"""Secondary ports that keep infrastructure out of the benchmark core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolProvider(Protocol):
    @property
    def id(self) -> str: ...

    async def invoke(self, name: str, arguments: Mapping[str, Any]) -> Any: ...


@runtime_checkable
class TelemetrySink(Protocol):
    @property
    def id(self) -> str: ...

    async def emit(self, event: Mapping[str, Any]) -> None: ...

    async def flush(self) -> None: ...


@runtime_checkable
class ResultStore(Protocol):
    @property
    def id(self) -> str: ...

    async def write_trial(self, trial: Mapping[str, Any]) -> None: ...

    async def read_run(self, run_id: str) -> Sequence[Mapping[str, Any]]: ...
