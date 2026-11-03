"""The minimal contract every evaluation integration implements."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from arlab.evaluation.model import EvaluationRequest, EvaluationResult, EvaluatorDefinition


@runtime_checkable
class Evaluator(Protocol):
    @property
    def id(self) -> str:
        """Stable adapter identifier, such as deterministic, deepeval, or promptfoo."""

    @property
    def version(self) -> str:
        """Adapter and rubric version recorded with every score."""

    async def evaluate(
        self,
        request: EvaluationRequest,
        definition: EvaluatorDefinition,
    ) -> Sequence[EvaluationResult]:
        """Evaluate one normalized trial without mutating it."""
