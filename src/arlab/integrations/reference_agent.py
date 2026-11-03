"""Known-good agent used to verify the benchmark harness itself."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from arlab.agents import (
    AgentDefinition,
    AgentEvent,
    AgentEventType,
    AgentRunContext,
    AgentTurn,
    ToolCall,
    Usage,
)
from arlab.tools import ToolInvocationError


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


class ReferenceWeatherSession:
    def __init__(self, session_id: str, tool_provider: Any) -> None:
        self._id = session_id
        self._tools = tool_provider

    @property
    def id(self) -> str:
        return self._id

    async def send(self, message: str) -> AgentTurn:
        del message
        arguments = {"city": "Orlando", "date": "tomorrow"}
        calls: list[ToolCall] = []
        events: list[AgentEvent] = []

        for attempt in range(1, 3):
            call_id = f"weather-{attempt}"
            events.append(
                AgentEvent(
                    AgentEventType.TOOL_CALL_REQUESTED,
                    _timestamp(),
                    {"call_id": call_id, "name": "weather.lookup", "arguments": arguments},
                )
            )
            try:
                result = await self._tools.invoke("weather.lookup", arguments)
            except ToolInvocationError as exc:
                calls.append(
                    ToolCall(
                        id=call_id,
                        name="weather.lookup",
                        arguments=arguments,
                        error=exc.error_type,
                        authorized=True,
                    )
                )
                events.append(
                    AgentEvent(
                        AgentEventType.ERROR,
                        _timestamp(),
                        {"call_id": call_id, "error": exc.error_type, "retryable": exc.retryable},
                    )
                )
                if exc.retryable and attempt == 1:
                    events.append(
                        AgentEvent(
                            AgentEventType.RETRY_SCHEDULED,
                            _timestamp(),
                            {"call_id": call_id, "attempt": 2},
                        )
                    )
                    continue
                raise

            calls.append(
                ToolCall(
                    id=call_id,
                    name="weather.lookup",
                    arguments=arguments,
                    result=result,
                    authorized=True,
                )
            )
            events.append(
                AgentEvent(
                    AgentEventType.TOOL_CALL_COMPLETED,
                    _timestamp(),
                    {"call_id": call_id, "name": "weather.lookup"},
                )
            )
            content = (
                f"{result['recommendation']}. The forecast for {result['city']} shows "
                f"{result['conditions']} with a {result['precipitation_probability']}% "
                "chance of precipitation."
            )
            events.append(AgentEvent(AgentEventType.COMPLETED, _timestamp(), {}))
            return AgentTurn(
                content=content,
                events=tuple(events),
                tool_calls=tuple(calls),
                usage=Usage(input_tokens=0, output_tokens=0, cost_usd=0.0),
                finished=True,
            )

        raise RuntimeError("reference agent exhausted its recovery attempts")

    async def close(self) -> None:
        return None


class ReferenceWeatherAdapter:
    id = "scripted-weather"

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        self.config = dict(config or {})

    async def open_session(
        self,
        definition: AgentDefinition,
        context: AgentRunContext,
    ) -> ReferenceWeatherSession:
        del definition
        provider = context.services.get("tool_provider")
        if provider is None:
            raise RuntimeError("the reference weather agent requires a tool provider")
        return ReferenceWeatherSession(f"reference-{context.trial_id}", provider)
