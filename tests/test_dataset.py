import asyncio
import json
from pathlib import Path

from arlab.config import load_agent, load_dataset, load_profile, load_yaml, project_root
from arlab.datasets import export_deepeval_jsonl, scenario_cases
from arlab.runner import BenchmarkRunner


def test_exports_deepeval_compatible_goldens(tmp_path: Path) -> None:
    root = project_root(Path(__file__))
    manifest = load_dataset(root / "datasets/synthetic/weather-reliability-v1.yaml")
    output = export_deepeval_jsonl(manifest, root, tmp_path / "goldens.jsonl")

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 3
    assert all(record["input"] for record in records)
    assert all(record["expected_output"] for record in records)
    assert all(isinstance(record["context"], list) for record in records)
    assert {record["additional_metadata"]["split"] for record in records} == {
        "validation",
        "test",
    }


def test_reference_agent_passes_every_synthetic_case(tmp_path: Path) -> None:
    root = project_root(Path(__file__))
    manifest = load_dataset(root / "datasets/synthetic/weather-reliability-v1.yaml")
    agent_path = root / "agents/reference-weather-recovery.yaml"
    agent = load_agent(agent_path)
    profile = load_profile(root / "evaluation-profiles/deterministic-only.yaml")
    runner = BenchmarkRunner(root)

    async def run_cases() -> list[dict[str, object]]:
        summaries = []
        for scenario, _ in scenario_cases(manifest, root):
            summaries.append(
                await runner.run(
                    scenario,
                    agent,
                    load_yaml(agent_path),
                    profile,
                    repetitions=1,
                    output_directory=tmp_path / str(scenario["id"]),
                )
            )
        return summaries

    summaries = asyncio.run(run_cases())
    assert all(summary["pass_rate"] == 1.0 for summary in summaries)
    assert sum(summary["tool_call_count"] for summary in summaries) == 4
    assert all(summary["average_latency_ms"] >= 0 for summary in summaries)
