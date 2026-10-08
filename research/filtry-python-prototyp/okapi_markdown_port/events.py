"""Minimalny model zdarzeń inspirowany kontraktem Okapi Framework."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    """Typy zdarzeń potrzebne w pierwszym etapie portu."""

    START_DOCUMENT = "START_DOCUMENT"
    TEXT_UNIT = "TEXT_UNIT"
    DOCUMENT_PART = "DOCUMENT_PART"
    END_DOCUMENT = "END_DOCUMENT"


@dataclass(frozen=True, slots=True)
class StartDocument:
    """Metadane początku dokumentu."""

    name: str


@dataclass(frozen=True, slots=True)
class TextUnit:
    """Minimalna jednostka tekstu tłumaczalnego."""

    id: str
    source: str


@dataclass(frozen=True, slots=True)
class DocumentPart:
    """Fragment dokumentu przechowywany poza tekstem tłumaczalnym."""

    content: str


@dataclass(frozen=True, slots=True)
class Ending:
    """Znacznik końca dokumentu."""


@dataclass(frozen=True, slots=True)
class Event:
    """Zdarzenie łączące typ z zasobem."""

    type: EventType
    resource: object


__all__ = [
    "DocumentPart",
    "Ending",
    "Event",
    "EventType",
    "StartDocument",
    "TextUnit",
]
