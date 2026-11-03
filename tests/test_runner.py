import asyncio
import json
from pathlib import Path

from arlab.config import load_agent, load_profile, load_scenario, load_yaml, project_root
from arlab.runner import BenchmarkRunner


def test_reference_weather_recovery_passes_and_writes_valid_evidence(tmp_path: Path) -> None:
    root = project_root(Path(__file__))
    agent_path = root / "agents/reference-weather-recovery.yaml"
    summary = asyncio.run(
        BenchmarkRunner(root).run(
            load_scenario(root / "suites/smoke/recovery-weather-timeout.yaml"),
            load_agent(agent_path),
            load_yaml(agent_path),
            load_profile(root / "evaluation-profiles/deterministic-only.yaml"),
            repetitions=1,
            output_directory=tmp_path,
        )
    )

    assert summary["pass_rate"] == 1.0
    result_path = Path(summary["result_directory"]) / "trial-001.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["status"] == "passed"
    assert [call["status"] for call in result["tool_calls"]] == ["timed_out", "succeeded"]
    assert all(evaluation["passed"] for evaluation in result["evaluations"])
