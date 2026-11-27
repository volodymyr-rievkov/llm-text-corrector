"""Framework-free value objects of the correction use case."""

from dataclasses import dataclass
from typing import Literal, TypedDict


@dataclass(frozen=True, slots=True)
class CorrectionRequest:
    text: str


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    corrected_text: str


ReasoningEffort = Literal["low", "medium", "high"]


class Message(TypedDict):
    """One chat message in the wire shape LLM providers accept."""

    role: Literal["system", "user", "assistant"]
    content: str
