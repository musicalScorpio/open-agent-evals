import asyncio
import base64
import json
from pathlib import Path

from arlab.config import load_agent, load_profile, load_scenario, load_yaml, project_root
from arlab.runner import BenchmarkRunner
from arlab.voice import export_confident_audio_trace, render_task_prompt, word_error_rate


def test_word_error_rate_counts_substitution() -> None:
    assert word_error_rate("verify my identity", "verify your identity") == 1 / 3


def test_voice_prompt_includes_transcript_and_output_contract() -> None:
    root = project_root(Path(__file__))
    scenario = load_scenario(
        root / "suites/voice/customer-support/refund-without-verification.yaml"
    )
    prompt = render_task_prompt(scenario)

    assert "USER: I was charged $129 twice" in prompt
    assert '"decision":{"action":"..."' in prompt
    assert "Permitted actions: escalate_for_identity_verification" in prompt


def test_confident_audio_export_is_local_and_decodable(tmp_path: Path) -> None:
    root = project_root(Path(__file__))
    scenario = load_scenario(
        root / "suites/voice/customer-support/refund-without-verification.yaml"
    )
    path = export_confident_audio_trace(scenario, root, tmp_path / "trace.json")
    messages = json.loads(path.read_text(encoding="utf-8"))

    assert len(messages) == 3
    assert messages[0]["audio"]["mimeType"] == "audio/wav"
    assert base64.b64decode(messages[0]["audio"]["dataBase64"]).startswith(b"RIFF")


def test_reference_voice_decision_passes_all_required_gates(tmp_path: Path) -> None:
    root = project_root(Path(__file__))
    scenario = load_scenario(
        root / "suites/voice/customer-support/refund-without-verification.yaml"
    )
    agent_path = root / "agents/reference-voice-decision.yaml"
    summary = asyncio.run(
        BenchmarkRunner(root).run(
            scenario,
            load_agent(agent_path),
            load_yaml(agent_path),
            load_profile(root / "evaluation-profiles/voice-local.yaml"),
            repetitions=1,
            output_directory=tmp_path,
        )
    )

    assert summary["pass_rate"] == 1.0
    result = json.loads(
        (Path(summary["result_directory"]) / "trial-001.json").read_text(encoding="utf-8")
    )
    assert result["measurements"]["conversation_turn_count"] == 4
    assert len(result["turns"]) == 4
    assert {item["metric"] for item in result["evaluations"]} >= {
        "audio_traceability",
        "transcript_accuracy",
        "decision_correctness",
        "policy_compliance",
        "customer_response",
    }
    assert all(item["passed"] for item in result["evaluations"])

