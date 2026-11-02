"""Runtime-selectable evaluation contracts."""

from arlab.evaluation.model import (
    EvaluationProfile,
    EvaluationRequest,
    EvaluationResult,
    EvaluatorDefinition,
)
from arlab.evaluation.protocol import Evaluator

__all__ = [
    "EvaluationProfile",
    "EvaluationRequest",
    "EvaluationResult",
    "Evaluator",
    "EvaluatorDefinition",
]

