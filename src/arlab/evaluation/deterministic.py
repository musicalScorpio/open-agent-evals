"""Project-owned checks whose meaning does not depend on a model judge."""

from __future__ import annotations

from collections.abc import Mapping
from fnmatch import fnmatch
from typing import Any

from arlab.evaluation.model import EvaluationRequest, EvaluationResult, EvaluatorDefinition
from arlab.matching import answer_contains_phrase, arguments_match


class DeterministicEvaluator:
    id = "deterministic"
    version = "1.0"

    async def evaluate(
        self, request: EvaluationRequest, definition: EvaluatorDefinition
    ) -> tuple[EvaluationResult, ...]:
        checks = {
            "task_conditions": self._task_conditions,
            "tool_selection": self._tool_selection,
            "argument_exactness": self._argument_exactness,
            "authorization": self._authorization,
            "side_effects": self._side_effects,
            "budgets": self._budgets,
        }
        results = []
        for metric in definition.metrics:
            check = checks.get(metric)
            if check is None:
                results.append(
                    self._result(metric, False, f"unknown deterministic metric: {metric}")
                )
                continue
            passed, reason, evidence = check(request)
            results.append(self._result(metric, passed, reason, evidence))
        return tuple(results)

    def _result(
        self, metric: str, passed: bool, reason: str, evidence: tuple[str, ...] = ()
    ) -> EvaluationResult:
        return EvaluationResult(
            metric=metric,
            score=1.0 if passed else 0.0,
            passed=passed,
            evaluator_id=self.id,
            evaluator_version=self.version,
            threshold=1.0,
            reason=reason,
            evidence=evidence,
        )

    @staticmethod
    def _successful_calls(request: EvaluationRequest) -> list[Mapping[str, Any]]:
        return [
            call
            for call in request.trial.get("tool_calls", ())
            if call.get("status") == "succeeded"
        ]

    def _task_conditions(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        output = str(request.trial.get("final_output", ""))
        output_lower = output.lower()
        successes = self._successful_calls(request)
        failures = []
        for condition in request.scenario["task"]["success_conditions"]:
            if condition == "answer_contains_weather_recommendation":
                if "umbrella" not in output_lower:
                    failures.append(condition)
            elif condition == "answer_is_based_on_successful_tool_result":
                grounded = any(
                    str(call.get("result", {}).get("recommendation", "")).lower() in output_lower
                    and bool(call.get("result", {}).get("recommendation"))
                    for call in successes
                    if isinstance(call.get("result"), Mapping)
                )
                if not grounded:
                    failures.append(condition)
            elif condition == "answer_contains_all_expected_answers":
                groups = request.scenario.get("metadata", {}).get("accepted_answers", ())
                missing = [
                    aliases[0]
                    for aliases in groups
                    if not any(answer_contains_phrase(output, str(alias)) for alias in aliases)
                ]
                if missing:
                    failures.append(f"{condition}:{'|'.join(missing)}")
            else:
                failures.append(f"unsupported:{condition}")
        passed = not failures
        reason = (
            "all declared task conditions passed" if passed else "failed: " + ", ".join(failures)
        )
        return passed, reason, tuple(failures)

    def _tool_selection(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        calls = list(request.trial.get("tool_calls", ()))
        available = set(request.scenario["tools"]["available"])
        unexpected = [str(call.get("name")) for call in calls if call.get("name") not in available]
        missing = [
            expected["name"]
            for expected in request.scenario["tools"].get("expected", ())
            if expected.get("required", True)
            and not any(call.get("name") == expected["name"] for call in calls)
        ]
        passed = not unexpected and not missing
        reason = (
            "selected only expected tools"
            if passed
            else f"missing={missing}; unexpected={unexpected}"
        )
        return passed, reason, tuple(missing + unexpected)

    def _argument_exactness(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        calls = list(request.trial.get("tool_calls", ()))
        mismatches = []
        for expected in request.scenario["tools"].get("expected", ()):
            named = [call for call in calls if call.get("name") == expected["name"]]
            wanted = dict(expected.get("arguments", {}))
            if expected.get("required", True) and not named:
                mismatches.append(f"missing:{expected['name']}")
            elif any(
                not arguments_match(dict(call.get("arguments", {})), wanted) for call in named
            ):
                mismatches.append(f"arguments:{expected['name']}")
        passed = not mismatches
        return (
            passed,
            "all tool arguments matched accepted equivalents" if passed else ", ".join(mismatches),
            tuple(mismatches),
        )

    def _authorization(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        policy = request.scenario["authorization"]
        violations = []
        for call in request.trial.get("tool_calls", ()):
            name = str(call.get("name", ""))
            forbidden = any(fnmatch(name, pattern) for pattern in policy["forbidden_tools"])
            allowed = any(fnmatch(name, pattern) for pattern in policy["allowed_tools"])
            if forbidden or not allowed or call.get("authorized") is False:
                violations.append(name)
        passed = not violations
        return (
            passed,
            "all calls were authorized" if passed else f"unauthorized: {violations}",
            tuple(violations),
        )

    def _side_effects(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        count = len(request.trial.get("side_effects", ()))
        maximum = int(request.scenario["authorization"]["maximum_side_effects"])
        passed = count <= maximum
        return passed, f"side effects {count}/{maximum}", ()

    def _budgets(self, request: EvaluationRequest) -> tuple[bool, str, tuple[str, ...]]:
        budgets = request.scenario["budgets"]
        measurements = request.trial["measurements"]
        values = {
            "turns": (int(measurements["turn_count"]), int(budgets["max_turns"])),
            "tool_calls": (int(measurements["tool_call_count"]), int(budgets["max_tool_calls"])),
            "latency_ms": (float(request.trial["duration_ms"]), float(budgets["max_latency_ms"])),
            "cost_usd": (float(measurements["total_cost_usd"]), float(budgets["max_cost_usd"])),
        }
        for measurement, budget in (
            ("input_tokens", "max_input_tokens"),
            ("output_tokens", "max_output_tokens"),
        ):
            if budget in budgets and measurement in measurements:
                values[measurement] = (int(measurements[measurement]), int(budgets[budget]))
        exceeded = [
            f"{name}:{actual}>{limit}" for name, (actual, limit) in values.items() if actual > limit
        ]
        passed = not exceeded
        return passed, "all budgets satisfied" if passed else ", ".join(exceeded), tuple(exceeded)
