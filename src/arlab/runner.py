"""Execute isolated benchmark trials and persist normalized evidence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from arlab import __version__
from arlab.agents import AgentDefinition, AgentRunContext
from arlab.builtins import registries
from arlab.evaluation import EvaluationProfile, EvaluationRequest
from arlab.tools import FixtureToolProvider


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _tool_call(call: Any) -> dict[str, Any]:
    status = (
        "succeeded"
        if call.error is None
        else ("timed_out" if call.error == "timeout" else "failed")
    )
    value: dict[str, Any] = {
        "call_id": call.id,
        "name": call.name,
        "arguments": dict(call.arguments),
        "status": status,
        "duration_ms": 0.0,
    }
    if call.result is not None:
        value["result"] = call.result
    if call.error is not None:
        value["error_type"] = call.error
    if call.authorized is not None:
        value["authorized"] = call.authorized
    return value


class BenchmarkRunner:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.plugins = registries(self.root)

    async def run(
        self,
        scenario: Mapping[str, Any],
        agent: AgentDefinition,
        agent_raw: Mapping[str, Any],
        profile: EvaluationProfile,
        *,
        repetitions: int | None = None,
        output_directory: Path | None = None,
    ) -> dict[str, Any]:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        total = repetitions or int(scenario.get("execution", {}).get("repetitions", 1))
        if total < 1:
            raise ValueError("repetitions must be at least 1")

        store_config = dict(profile.result_store_config)
        if output_directory is not None:
            store_config["directory"] = str(output_directory)
        store = self.plugins["result_store"].create(profile.result_store, store_config)
        sinks = []
        skipped_plugins = []
        for name in profile.telemetry_sinks:
            try:
                sinks.append(self.plugins["telemetry_sink"].create(name, {}))
            except KeyError:
                skipped_plugins.append(f"telemetry:{name}")

        await self._emit(sinks, {"type": "run.started", "run_id": run_id, "timestamp": _now()})
        results = []
        for number in range(1, total + 1):
            result = await self._run_trial(
                run_id, number, scenario, agent, agent_raw, profile, skipped_plugins
            )
            await store.write_trial(result)
            results.append(result)
            await self._emit(
                sinks,
                {
                    "type": "trial.completed",
                    "run_id": run_id,
                    "trial_id": result["trial_id"],
                    "status": result["status"],
                    "timestamp": _now(),
                },
            )

        passed = sum(result["status"] == "passed" for result in results)
        measurement_totals = {
            name: sum(result["measurements"].get(name, 0) for result in results)
            for name in (
                "tool_call_count",
                "model_call_count",
                "total_cost_usd",
                "input_tokens",
                "output_tokens",
                "reasoning_tokens",
                "cached_input_tokens",
            )
        }
        summary = {
            "run_id": run_id,
            "scenario_id": scenario["id"],
            "agent_id": agent.id,
            "profile_id": profile.id,
            "trials": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "average_latency_ms": sum(result["duration_ms"] for result in results) / total,
            **measurement_totals,
            "result_directory": str(store.directory / run_id),
            "skipped_optional_plugins": sorted(set(skipped_plugins)),
        }
        summary_path = store.directory / run_id / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        await self._emit(sinks, {"type": "run.completed", **summary, "timestamp": _now()})
        for sink in sinks:
            await sink.flush()
        return summary

    async def _run_trial(
        self,
        run_id: str,
        number: int,
        scenario: Mapping[str, Any],
        agent: AgentDefinition,
        agent_raw: Mapping[str, Any],
        profile: EvaluationProfile,
        skipped_plugins: list[str],
    ) -> dict[str, Any]:
        trial_id = f"trial-{number:03d}"
        started_at = _now()
        started = time.perf_counter()
        tool_provider = FixtureToolProvider(scenario, self.root)
        with tempfile.TemporaryDirectory(prefix="arlab-") as directory:
            context = AgentRunContext(
                run_id=run_id,
                trial_id=trial_id,
                scenario_id=str(scenario["id"]),
                workspace=Path(directory),
                environment={"ARLAB_RUN_ID": run_id, "ARLAB_TRIAL_ID": trial_id},
                metadata={"scenario": scenario, "project_root": str(self.root)},
                services={"tool_provider": tool_provider},
            )
            adapter = self.plugins["agent_adapter"].create(agent.adapter, agent.runtime)
            session = await adapter.open_session(agent, context)
            try:
                turn = await session.send(str(scenario["task"]["user_prompt"]))
            finally:
                await session.close()

        duration_ms = (time.perf_counter() - started) * 1000
        calls = []
        previous_call_by_name: dict[str, str] = {}
        for call in turn.tool_calls:
            normalized_call = _tool_call(call)
            if call.name in previous_call_by_name:
                normalized_call["retry_of"] = previous_call_by_name[call.name]
            previous_call_by_name[call.name] = call.id
            calls.append(normalized_call)
        usage = turn.usage
        measurements = {
            "turn_count": 1,
            "tool_call_count": len(calls),
            "model_call_count": turn.model_call_count
            if turn.model_call_count is not None
            else (0 if agent.model.provider == "built-in" else 1),
            "total_cost_usd": float(usage.cost_usd or 0.0) if usage else 0.0,
        }
        if usage:
            for name in (
                "input_tokens",
                "output_tokens",
                "reasoning_tokens",
                "cached_input_tokens",
            ):
                value = getattr(usage, name)
                if value is not None:
                    measurements[name] = value

        trial = {
            "final_output": turn.content,
            "tool_calls": calls,
            "side_effects": [],
            "measurements": measurements,
            "duration_ms": duration_ms,
        }
        evaluation_request = EvaluationRequest(
            run_id=run_id,
            trial_id=trial_id,
            scenario=scenario,
            agent=agent_raw,
            trial=trial,
            expected=scenario.get("expectations", {}),
        )
        evaluations = []
        required_passed = True
        for definition in profile.evaluators:
            try:
                evaluator = self.plugins["evaluator"].create(definition.adapter, definition.config)
            except KeyError:
                if definition.required:
                    raise
                skipped_plugins.append(f"evaluator:{definition.adapter}")
                continue
            evaluated = await evaluator.evaluate(evaluation_request, definition)
            for result in evaluated:
                evaluations.append(
                    {
                        "metric": result.metric,
                        "evaluator": {
                            "id": result.evaluator_id,
                            "version": result.evaluator_version,
                        },
                        "score": result.score,
                        "threshold": result.threshold,
                        "passed": result.passed,
                        "reason": result.reason,
                        "evidence": list(result.evidence),
                    }
                )
                if definition.required and not result.passed:
                    required_passed = False

        result = {
            "schema_version": "1.0",
            "run_id": run_id,
            "trial_id": trial_id,
            "scenario": {
                "id": scenario["id"],
                "version": scenario["schema_version"],
                "content_hash": _hash(scenario),
            },
            "agent": {"id": agent.id, "version": agent.version, "content_hash": _hash(agent_raw)},
            "started_at": started_at,
            "duration_ms": duration_ms,
            "status": "passed" if required_passed else "failed",
            "outcome": {
                "task_success": required_passed,
                "partial_score": sum(item["score"] for item in evaluations) / len(evaluations)
                if evaluations
                else 0.0,
                "final_output": turn.content,
            },
            "tool_calls": calls,
            "side_effects": [],
            "faults_injected": list(scenario.get("faults", ())),
            "measurements": measurements,
            "evaluations": evaluations,
            "provenance": {
                "repository_commit": _commit(self.root),
                "runner_version": __version__,
                "environment_hash": _hash({"python": sys.version, "platform": platform.platform()}),
                "model_provider": agent.model.provider,
                "model_name": agent.model.name,
                "prompt_hash": _hash(scenario["task"]["user_prompt"]),
                "configuration": {"profile": profile.id, "pid": os.getpid()},
            },
        }
        schema = json.loads((self.root / "schemas/result.schema.json").read_text(encoding="utf-8"))
        errors = list(Draft202012Validator(schema).iter_errors(result))
        if errors:
            raise RuntimeError(
                "generated invalid result: " + "; ".join(error.message for error in errors)
            )
        return result

    @staticmethod
    async def _emit(sinks: list[Any], event: Mapping[str, Any]) -> None:
        for sink in sinks:
            await sink.emit(event)
