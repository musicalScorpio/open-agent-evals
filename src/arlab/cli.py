"""Command-line interface for local benchmark execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

from arlab.builtins import registries
from arlab.config import (
    ConfigurationError,
    load_agent,
    load_profile,
    load_scenario,
    load_yaml,
    project_root,
)
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
        return asyncio.run(_run(args, root))
    except (ConfigurationError, KeyError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
