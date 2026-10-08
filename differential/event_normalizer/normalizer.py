from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum


def _value(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _value(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_value(item) for item in value]
    if isinstance(value, list):
        return [_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _value(item) for key, item in sorted(value.items())}
    return value


class EventNormalizer:
    def normalize(self, events) -> tuple[dict, ...]:
        return tuple({"type": event.type.value, "resource": _value(event.resource)} for event in events)
