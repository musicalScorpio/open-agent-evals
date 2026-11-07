"""Voice-call evidence, prompts, deterministic metrics, and trace exports."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arlab.evaluation.model import EvaluationRequest, EvaluationResult, EvaluatorDefinition


def _voice(scenario: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = scenario.get("voice")
    return value if isinstance(value, Mapping) else None


def render_task_prompt(scenario: Mapping[str, Any]) -> str:
    """Render structured voice evidence into the prompt sent to the candidate agent."""
    prompt = str(scenario["task"]["user_prompt"])
    voice = _voice(scenario)
    if voice is None:
        return prompt

    lines = [prompt, "", "Customer-call transcript (one message per recorded clip):"]
    for index, message in enumerate(voice["conversation"], start=1):
        lines.append(f"{index}. {str(message['role']).upper()}: {message['content']}")

    decision = voice["decision"]
    lines.extend(
        [
            "",
            "Return only one JSON object with this shape:",
            '{"decision":{"action":"...","reason_codes":["..."]},'
            '"customer_message":"..."}',
            "Do not claim that an action was completed unless the policy and evidence allow it.",
            f"Permitted actions: {', '.join(decision['allowed_actions'])}.",
            "Use only these canonical reason codes: "
            + ", ".join(decision.get("required_reason_codes", ()))
            + ".",
        ]
    )
    return "\n".join(lines)


def result_turns(
    scenario: Mapping[str, Any], final_output: str, timestamp: str
) -> list[dict[str, Any]]:
    """Create replayable result turns without embedding audio bytes in run evidence."""
    voice = _voice(scenario)
    if voice is None:
        return []
    turns = []
    for message in voice["conversation"]:
        content: dict[str, Any] = {"text": message["content"]}
        if "audio" in message:
            content["audio"] = {
                "path": message["audio"]["path"],
                "mimeType": message["audio"]["mime_type"],
            }
        turns.append({"role": message["role"], "content": content, "timestamp": timestamp})
    turns.append({"role": "assistant", "content": final_output, "timestamp": timestamp})
    return turns


def _extract_json(value: str) -> Mapping[str, Any] | None:
    candidates = [value.strip()]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", value, flags=re.DOTALL | re.I)
    if fenced:
        candidates.insert(0, fenced.group(1))
    start, end = value.find("{"), value.rfind("}")
    if start >= 0 and end > start:
        candidates.append(value[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, Mapping):
            return parsed
    return None


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", value.casefold())


def word_error_rate(reference: str, observed: str) -> float:
    """Compute word error rate using Levenshtein distance."""
    expected, actual = _words(reference), _words(observed)
    if not expected:
        return 0.0 if not actual else 1.0
    previous = list(range(len(actual) + 1))
    for row, wanted in enumerate(expected, start=1):
        current = [row]
        for column, found in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (wanted != found),
                )
            )
        previous = current
    return previous[-1] / len(expected)


class VoiceDecisionEvaluator:
    """Deterministic voice-pipeline and post-call decision quality gates."""

    id = "voice-decision"
    version = "1.0"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def evaluate(
        self, request: EvaluationRequest, definition: EvaluatorDefinition
    ) -> tuple[EvaluationResult, ...]:
        checks = {
            "audio_traceability": self._audio_traceability,
            "transcript_accuracy": self._transcript_accuracy,
            "decision_correctness": self._decision_correctness,
            "policy_compliance": self._policy_compliance,
            "customer_response": self._customer_response,
        }
        voice = _voice(request.scenario)
        if voice is None:
            return tuple(
                self._result(metric, False, "scenario has no voice definition")
                for metric in definition.metrics
            )
        output = str(request.trial.get("final_output", ""))
        parsed = _extract_json(output)
        results = []
        for metric in definition.metrics:
            check = checks.get(metric)
            if check is None:
                results.append(self._result(metric, False, f"unknown voice metric: {metric}"))
                continue
            passed, reason, evidence, score = check(voice, parsed)
            threshold = (
                max(0.0, 1 - float(voice["transcription"]["max_word_error_rate"]))
                if metric == "transcript_accuracy"
                else 1.0
            )
            results.append(self._result(metric, passed, reason, evidence, score, threshold))
        return tuple(results)

    def _result(
        self,
        metric: str,
        passed: bool,
        reason: str,
        evidence: tuple[str, ...] = (),
        score: float | None = None,
        threshold: float = 1.0,
    ) -> EvaluationResult:
        return EvaluationResult(
            metric=metric,
            score=float(passed) if score is None else score,
            passed=passed,
            evaluator_id=self.id,
            evaluator_version=self.version,
            threshold=threshold,
            reason=reason,
            evidence=evidence,
        )

    def _audio_traceability(
        self, voice: Mapping[str, Any], parsed: Mapping[str, Any] | None
    ) -> tuple[bool, str, tuple[str, ...], float]:
        del parsed
        failures = []
        audio_count = 0
        for index, message in enumerate(voice["conversation"], start=1):
            audio = message.get("audio")
            if not isinstance(audio, Mapping):
                continue
            audio_count += 1
            path = (self.root / str(audio["path"])).resolve()
            if self.root not in path.parents or not path.is_file():
                failures.append(f"turn-{index}:missing-or-unsafe-path")
                continue
            expected_hash = audio.get("sha256")
            if expected_hash and hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
                failures.append(f"turn-{index}:sha256-mismatch")
        if audio_count == 0:
            failures.append("no-audio-clips")
        passed = not failures
        return (
            passed,
            f"{audio_count} per-turn audio clips are locally traceable"
            if passed
            else ", ".join(failures),
            tuple(failures),
            1.0 if passed else 0.0,
        )

    @staticmethod
    def _transcript_accuracy(
        voice: Mapping[str, Any], parsed: Mapping[str, Any] | None
    ) -> tuple[bool, str, tuple[str, ...], float]:
        del parsed
        transcription = voice.get("transcription", {})
        rate = word_error_rate(
            str(transcription.get("reference", "")),
            str(transcription.get("observed", "")),
        )
        maximum = float(transcription.get("max_word_error_rate", 0.0))
        passed = rate <= maximum
        return passed, f"word error rate {rate:.3f} (maximum {maximum:.3f})", (), max(0.0, 1 - rate)

    @staticmethod
    def _decision_values(
        parsed: Mapping[str, Any] | None,
    ) -> tuple[str, set[str]]:
        if parsed is None or not isinstance(parsed.get("decision"), Mapping):
            return "", set()
        decision = parsed["decision"]
        action = str(decision.get("action", ""))
        reasons = decision.get("reason_codes", ())
        return action, {str(reason) for reason in reasons} if isinstance(reasons, list) else set()

    def _decision_correctness(
        self, voice: Mapping[str, Any], parsed: Mapping[str, Any] | None
    ) -> tuple[bool, str, tuple[str, ...], float]:
        action, _ = self._decision_values(parsed)
        expected = str(voice["decision"]["expected_action"])
        passed = action == expected
        reason = (
            f"decision action matched {expected}"
            if passed
            else f"expected {expected}; got {action or '<missing>'}"
        )
        evidence = () if passed else (f"action:{action or '<missing>'}",)
        return passed, reason, evidence, float(passed)

    def _policy_compliance(
        self, voice: Mapping[str, Any], parsed: Mapping[str, Any] | None
    ) -> tuple[bool, str, tuple[str, ...], float]:
        action, reasons = self._decision_values(parsed)
        policy = voice["decision"]
        missing = sorted(set(policy.get("required_reason_codes", ())) - reasons)
        forbidden_reasons = sorted(set(policy.get("forbidden_reason_codes", ())) & reasons)
        failures = []
        if action not in policy["allowed_actions"]:
            failures.append(f"disallowed-action:{action or '<missing>'}")
        if action in policy.get("forbidden_actions", ()):
            failures.append(f"forbidden-action:{action}")
        failures.extend(f"missing-reason:{item}" for item in missing)
        failures.extend(f"forbidden-reason:{item}" for item in forbidden_reasons)
        passed = not failures
        reason = "decision obeyed policy" if passed else ", ".join(failures)
        return passed, reason, tuple(failures), float(passed)

    @staticmethod
    def _customer_response(
        voice: Mapping[str, Any], parsed: Mapping[str, Any] | None
    ) -> tuple[bool, str, tuple[str, ...], float]:
        message = str(parsed.get("customer_message", "")) if parsed else ""
        folded = message.casefold()
        policy = voice["decision"]
        missing = [
            item
            for item in policy.get("customer_message_must_include", ())
            if str(item).casefold() not in folded
        ]
        forbidden = [
            item
            for item in policy.get("customer_message_must_not_include", ())
            if str(item).casefold() in folded
        ]
        failures = [
            *(f"missing:{item}" for item in missing),
            *(f"forbidden:{item}" for item in forbidden),
        ]
        passed = bool(message) and not failures
        if not message:
            failures.insert(0, "missing:customer_message")
        reason = (
            "customer response met deterministic requirements"
            if passed
            else ", ".join(failures)
        )
        return passed, reason, tuple(failures), float(passed)


def export_confident_audio_trace(
    scenario: Mapping[str, Any], root: Path, output_path: Path
) -> Path:
    """Export the documented Confident message/media shape without uploading it."""
    voice = _voice(scenario)
    if voice is None:
        raise ValueError("scenario has no voice definition")
    messages = []
    for message in voice["conversation"]:
        exported: dict[str, Any] = {"role": message["role"], "content": message["content"]}
        audio = message.get("audio")
        if isinstance(audio, Mapping):
            path = (root / str(audio["path"])).resolve()
            if root.resolve() not in path.parents or not path.is_file():
                raise ValueError(
                    f"audio fixture is missing or escapes project root: {audio['path']}"
                )
            exported["audio"] = {
                "mimeType": audio["mime_type"],
                "dataBase64": base64.b64encode(path.read_bytes()).decode("ascii"),
            }
        messages.append(exported)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(messages, indent=2) + "\n", encoding="utf-8")
    return output_path
