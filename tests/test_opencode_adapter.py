import json
from pathlib import Path

from arlab.agents import AgentDefinition, AgentRunContext
from arlab.integrations.opencode import OpenCodeCliSession


def _session(tmp_path: Path) -> OpenCodeCliSession:
    definition = AgentDefinition.from_mapping(
        {
            "id": "opencode.test",
            "version": "1.0",
            "runtime": {"adapter": "opencode", "mode": "cli"},
            "model": {
                "provider": "ollama",
                "name": "gpt-oss:20b",
                "endpoint": "http://127.0.0.1:11434",
                "options": {"num_ctx": 32768},
            },
            "permissions": {"default": "deny", "rules": {}},
        }
    )
    context = AgentRunContext(
        run_id="run",
        trial_id="trial",
        scenario_id="scenario",
        workspace=tmp_path,
    )
    return OpenCodeCliSession(definition, context)


def test_parses_tool_calls_usage_and_final_text(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session._tool_names["weather_lookup"] = "weather.lookup"
    events = [
        {
            "type": "tool_use",
            "part": {
                "tool": "weather_lookup",
                "callID": "first",
                "state": {
                    "status": "error",
                    "input": {"city": "Orlando", "date": "tomorrow"},
                    "error": "timeout; retryable=true",
                },
            },
        },
        {
            "type": "tool_use",
            "part": {
                "tool": "weather_lookup",
                "callID": "second",
                "state": {
                    "status": "completed",
                    "input": {"city": "Orlando", "date": "tomorrow"},
                    "output": json.dumps({"recommendation": "Bring an umbrella"}),
                },
            },
        },
        {
            "type": "step_finish",
            "part": {
                "tokens": {
                    "input": 100,
                    "output": 20,
                    "reasoning": 3,
                    "cache": {"read": 40},
                },
                "cost": 0,
            },
        },
        {"type": "text", "part": {"text": "Bring an umbrella."}},
    ]
    payload = "\n".join(json.dumps(event) for event in events).encode()

    _, _, text, calls, usage, model_calls = session._parse_events(payload)

    assert text[-1] == "Bring an umbrella."
    assert [call.name for call in calls] == ["weather.lookup", "weather.lookup"]
    assert calls[0].error == "timeout"
    assert calls[1].result == {"recommendation": "Bring an umbrella"}
    assert usage.input_tokens == 100
    assert usage.cached_input_tokens == 40
    assert model_calls == 1


def test_writes_ollama_provider_configuration(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session._tool_names["weather_lookup"] = "weather.lookup"
    session._tool_arguments["weather_lookup"] = ("city", "date")

    path = session._write_local_config()
    config = json.loads(path.read_text(encoding="utf-8"))

    assert config["model"] == "ollama/gpt-oss:20b"
    assert config["provider"]["ollama"]["options"]["baseURL"].endswith("/v1")
    assert config["permission"]["weather_lookup"] == "allow"
    assert config["default_agent"] == "arlab"
    assert config["agent"]["arlab"]["mode"] == "primary"
    assert config["agent"]["arlab"]["prompt"] == "{file:./ARLAB_INSTRUCTIONS.md}"
    assert (tmp_path / "ARLAB_INSTRUCTIONS.md").exists()


def test_parses_structured_retryable_fault_as_failed_call(tmp_path: Path) -> None:
    session = _session(tmp_path)
    session._tool_names["weather_lookup"] = "weather.lookup"
    events = [
        {
            "type": "tool_use",
            "part": {
                "tool": "weather_lookup",
                "callID": "first",
                "state": {
                    "status": "completed",
                    "input": {"city": "Miami", "date": "2026-11-02"},
                    "output": json.dumps(
                        {
                            "__arlab_fault__": True,
                            "ok": False,
                            "error": "rate_limited",
                            "retryable": True,
                        }
                    ),
                },
            },
        }
    ]

    _, _, _, calls, _, _ = session._parse_events(json.dumps(events[0]).encode())

    assert calls[0].error == "rate_limited"
    assert calls[0].result is None
