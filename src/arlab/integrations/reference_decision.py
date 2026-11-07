"""Known-good decision agent used to validate voice-evaluation mechanics."""

from __future__ import annotations

import json
from collections.abc import Mapping

from arlab.agents import AgentDefinition, AgentRunContext, AgentTurn, Usage


class ReferenceDecisionSession:
    def __init__(self, session_id: str, scenario: Mapping[str, object]) -> None:
        self._id = session_id
        self._scenario = scenario

    @property
    def id(self) -> str:
        return self._id

    async def send(self, message: str) -> AgentTurn:
        del message
        voice = self._scenario["voice"]
        decision = voice["decision"]
        content = json.dumps(
            {
                "decision": {
                    "action": decision["expected_action"],
                    "reason_codes": decision.get("required_reason_codes", []),
                },
                "customer_message": decision["reference_customer_message"],
            }
        )
        return AgentTurn(
            content=content,
            usage=Usage(input_tokens=0, output_tokens=0, cost_usd=0.0),
            model_call_count=0,
            finished=True,
        )

    async def close(self) -> None:
        return None


class ReferenceDecisionAdapter:
    id = "scripted-decision"

    def __init__(self, config: Mapping[str, object] | None = None) -> None:
        self.config = dict(config or {})

    async def open_session(
        self, definition: AgentDefinition, context: AgentRunContext
    ) -> ReferenceDecisionSession:
        del definition
        scenario = context.metadata.get("scenario")
        if not isinstance(scenario, Mapping) or "voice" not in scenario:
            raise RuntimeError("the reference decision agent requires a voice scenario")
        return ReferenceDecisionSession(f"reference-decision-{context.trial_id}", scenario)
