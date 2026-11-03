"""Protocols implemented by in-process, CLI, or HTTP agent runtimes."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from arlab.agents.model import AgentDefinition, AgentRunContext, AgentTurn


@runtime_checkable
class AgentSession(Protocol):
    @property
    def id(self) -> str:
        """Runtime-specific session identifier."""

    async def send(self, message: str) -> AgentTurn:
        """Send one user turn and return its normalized result."""

    async def close(self) -> None:
        """Release runtime resources without deleting benchmark evidence."""


@runtime_checkable
class AgentAdapter(Protocol):
    @property
    def id(self) -> str:
        """Stable adapter identifier used by agent definitions."""

    async def open_session(
        self,
        definition: AgentDefinition,
        context: AgentRunContext,
    ) -> AgentSession:
        """Create an isolated session for one benchmark trial."""
