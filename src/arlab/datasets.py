"""Framework-neutral dataset manifests and evaluator-specific exports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arlab.config import load_scenario


def scenario_cases(manifest: Mapping[str, Any], root: Path) -> list[tuple[Mapping[str, Any], str]]:
    return [
        (load_scenario(root / str(case["scenario"])), str(case["split"]))
        for case in manifest["cases"]
    ]


def export_deepeval_jsonl(manifest: Mapping[str, Any], root: Path, output_path: Path) -> Path:
    """Export local goldens without importing or requiring DeepEval."""
    records = []
    for scenario, split in scenario_cases(manifest, root):
        fixture_binding = scenario["fixtures"][0]
        fixture = json.loads((root / str(fixture_binding["path"])).read_text(encoding="utf-8"))
        result = fixture["result"]
        expected_output = (
            f"{result['recommendation']}. The forecast for {result['city']} shows "
            f"{result['conditions']} with a {result['precipitation_probability']}% "
            "chance of precipitation."
        )
        records.append(
            {
                "input": scenario["task"]["user_prompt"],
                "expected_output": expected_output,
                "context": [json.dumps(result, sort_keys=True)],
                "additional_metadata": {
                    "dataset_id": manifest["id"],
                    "dataset_version": manifest["version"],
                    "scenario_id": scenario["id"],
                    "split": split,
                    "source": manifest["source"],
                    "expected_tools": scenario["tools"].get("expected", []),
                    "faults": scenario.get("faults", []),
                    "risk_tier": scenario["risk_tier"],
                    "autonomy_level": scenario["autonomy_level"],
                },
            }
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return output_path
