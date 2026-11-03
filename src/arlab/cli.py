"""Command-line interface for local benchmark execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from arlab.builtins import registries
from arlab.config import (
    ConfigurationError,
    load_agent,
    load_dataset,
    load_profile,
    load_scenario,
    load_yaml,
    project_root,
)
from arlab.datasets import export_deepeval_jsonl, scenario_cases
from arlab.runner import BenchmarkRunner


def _path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _doctor() -> int:
    print(f"Python:   OK ({sys.version.split()[0]})")
    uv = shutil.which("uv")
    opencode = shutil.which("opencode")
    print(f"uv:       {'OK (' + uv + ')' if uv else 'MISSING'}")
    print(f"OpenCode: {'OK (' + opencode + ')' if opencode else 'MISSING (optional)'}")
    ollama = shutil.which("ollama")
    if not ollama:
        print("Ollama:   MISSING (optional for the reference smoke test)")
        return 0
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as response:
            models = json.load(response).get("models", [])
        names = ", ".join(model["name"] for model in models) or "no models pulled"
        print(f"Ollama:   OK ({ollama}; {names})")
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        print(f"Ollama:   INSTALLED but server is not reachable ({ollama})")
    return 0


def _validate(root: Path) -> int:
    groups = [
        ("agents", root / "agents", load_agent),
        ("profiles", root / "evaluation-profiles", load_profile),
        ("scenarios", root / "suites", load_scenario),
        ("datasets", root / "datasets", load_dataset),
    ]
    total = 0
    for label, directory, loader in groups:
        paths = sorted(directory.rglob("*.yaml"))
        for path in paths:
            loader(path)
        total += len(paths)
        print(f"{label.capitalize()}: {len(paths)} valid")
    print(f"Validated {total} definitions.")
    return 0


def _plugins(root: Path) -> int:
    for kind, registry in registries(root).items():
        print(f"{kind}: {', '.join(registry.names()) or 'none'}")
    return 0


async def _run(args: argparse.Namespace, root: Path) -> int:
    scenario_path = _path(root, args.scenario)
    agent_path = _path(root, args.agent)
    profile_path = _path(root, args.profile)
    scenario = load_scenario(scenario_path)
    agent = load_agent(agent_path)
    profile = load_profile(profile_path)
    output = _path(root, args.output) if args.output else None
    summary = await BenchmarkRunner(root).run(
        scenario,
        agent,
        load_yaml(agent_path),
        profile,
        repetitions=args.runs,
        output_directory=output,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


def _dataset_validate(args: argparse.Namespace, root: Path) -> int:
    path = _path(root, args.dataset)
    manifest = load_dataset(path)
    splits: dict[str, int] = {}
    for case in manifest["cases"]:
        split = str(case["split"])
        splits[split] = splits.get(split, 0) + 1
    print(
        json.dumps(
            {
                "dataset_id": manifest["id"],
                "version": manifest["version"],
                "source": manifest["source"],
                "cases": len(manifest["cases"]),
                "splits": splits,
                "review_status": manifest["generator"]["review_status"],
            },
            indent=2,
        )
    )
    return 0


def _dataset_export(args: argparse.Namespace, root: Path) -> int:
    manifest = load_dataset(_path(root, args.dataset))
    output = (
        _path(root, args.output)
        if args.output
        else root
        / "results"
        / "exports"
        / f"{manifest['id']}-v{manifest['version']}.deepeval.jsonl"
    )
    path = export_deepeval_jsonl(manifest, root, output)
    print(f"Exported {len(manifest['cases'])} DeepEval goldens to {path}")
    return 0


async def _dataset_run(args: argparse.Namespace, root: Path) -> int:
    manifest = load_dataset(_path(root, args.dataset))
    profile = load_profile(_path(root, args.profile))
    agent_paths = args.agent or ["agents/reference-weather-recovery.yaml"]
    agents = [(_path(root, path), load_agent(_path(root, path))) for path in agent_paths]
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_root = (
        _path(root, args.output)
        if args.output
        else root / "results" / "datasets" / f"{manifest['id']}-{timestamp}"
    )
    runner = BenchmarkRunner(root)
    agent_summaries = []
    total_failures = 0
    for agent_path, agent in agents:
        case_summaries = []
        for scenario, split in scenario_cases(manifest, root):
            summary = await runner.run(
                scenario,
                agent,
                load_yaml(agent_path),
                profile,
                repetitions=args.runs,
                output_directory=output_root / agent.id / str(scenario["id"]),
            )
            case_summaries.append({"split": split, **summary})
        passed = sum(item["passed"] for item in case_summaries)
        trials = sum(item["trials"] for item in case_summaries)
        failed = trials - passed
        total_failures += failed
        totals = {
            name: sum(item[name] for item in case_summaries)
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
        agent_summaries.append(
            {
                "agent_id": agent.id,
                "trials": trials,
                "passed": passed,
                "failed": failed,
                "pass_rate": passed / trials if trials else 0.0,
                "average_latency_ms": (
                    sum(item["average_latency_ms"] * item["trials"] for item in case_summaries)
                    / trials
                    if trials
                    else 0.0
                ),
                **totals,
                "cases": case_summaries,
            }
        )
    comparison = {
        "schema_version": "1.0",
        "dataset_id": manifest["id"],
        "dataset_version": manifest["version"],
        "profile_id": profile.id,
        "generated_at": datetime.now(UTC).isoformat(),
        "agents": agent_summaries,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    comparison_path = output_root / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({**comparison, "comparison_path": str(comparison_path)}, indent=2))
    return 0 if total_failures == 0 else 1


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="arlab", description="Local agent reliability benchmarks")
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("doctor", help="check local runtime dependencies")
    subcommands.add_parser("validate", help="validate all benchmark definitions")
    subcommands.add_parser("plugins", help="list available runtime plugins")
    run = subcommands.add_parser("run", help="execute a benchmark scenario")
    run.add_argument("--scenario", default="suites/smoke/recovery-weather-timeout.yaml")
    run.add_argument("--agent", default="agents/reference-weather-recovery.yaml")
    run.add_argument("--profile", default="evaluation-profiles/deterministic-only.yaml")
    run.add_argument("--runs", type=int, help="override scenario repetitions")
    run.add_argument("--output", help="override result directory")

    dataset = subcommands.add_parser("dataset", help="validate, export, or run a dataset")
    dataset_commands = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_default = "datasets/synthetic/weather-reliability-v1.yaml"

    validate_dataset = dataset_commands.add_parser("validate", help="validate a dataset manifest")
    validate_dataset.add_argument("--dataset", default=dataset_default)

    export_dataset = dataset_commands.add_parser(
        "export-deepeval", help="export framework-neutral cases as DeepEval JSONL goldens"
    )
    export_dataset.add_argument("--dataset", default=dataset_default)
    export_dataset.add_argument("--output")

    run_dataset = dataset_commands.add_parser("run", help="compare one or more agents")
    run_dataset.add_argument("--dataset", default=dataset_default)
    run_dataset.add_argument("--agent", action="append", help="agent YAML; repeat to compare")
    run_dataset.add_argument("--profile", default="evaluation-profiles/deterministic-only.yaml")
    run_dataset.add_argument("--runs", type=int, default=1, help="repetitions per case")
    run_dataset.add_argument("--output", help="override comparison result directory")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        root = project_root(Path.cwd())
        if args.command == "doctor":
            return _doctor()
        if args.command == "validate":
            return _validate(root)
        if args.command == "plugins":
            return _plugins(root)
        if args.command == "dataset":
            if args.dataset_command == "validate":
                return _dataset_validate(args, root)
            if args.dataset_command == "export-deepeval":
                return _dataset_export(args, root)
            return asyncio.run(_dataset_run(args, root))
        return asyncio.run(_run(args, root))
    except (ConfigurationError, KeyError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
