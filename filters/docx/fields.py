from __future__ import annotations
from dataclasses import dataclass, field
from core.document.model import Code, Part

@dataclass
class FieldState:
    depth: int = 0
    instruction: list[str] = field(default_factory=list)
    result: list[Part] = field(default_factory=list)
    phase: str = "instruction"

@dataclass(frozen=True)
class ComplexField:
    instruction: str
    result: tuple[Part, ...]
    nested: tuple["ComplexField", ...] = ()

    @property
    def depth(self) -> int:
        return 1 + max((field.depth for field in self.nested), default=0)

    @property
    def nested_count(self) -> int:
        return sum(1 + field.nested_count for field in self.nested)


class ComplexFieldStream:
    def __init__(self) -> None:
        self._completed: list[ComplexField] = []
        self._stack: list[dict] = []

    @property
    def fields(self) -> tuple[ComplexField, ...]:
        return tuple(self._completed)

    def feed(self, parts: tuple[Part, ...] | list[Part]) -> None:
        for part in parts:
            if not isinstance(part, Code) or part.kind != "field_char":
                if not self._stack:
                    continue
                current = self._stack[-1]
                if current["phase"] == "instruction" and isinstance(part, Code) and part.kind == "field_instruction":
                    current["instruction"].append(part.data)
                elif current["phase"] != "instruction":
                    current["result"].append(part)
                continue
            marker = part.data
            if marker == "begin":
                node = {"instruction": [], "result": [], "nested": [], "phase": "instruction"}
                if self._stack:
                    self._stack[-1]["nested"].append(node)
                self._stack.append(node)
            elif marker == "separate":
                if not self._stack:
                    raise ValueError("field separate without begin")
                self._stack[-1]["phase"] = "result"
            elif marker == "end":
                if not self._stack:
                    raise ValueError("field end without begin")
                node = self._stack.pop()
                if not self._stack:
                    self._completed.append(self._freeze(node))

    def finish(self) -> tuple[ComplexField, ...]:
        if self._stack:
            raise ValueError("unclosed complex field")
        return self.fields

    def _freeze(self, node: dict) -> ComplexField:
        return ComplexField(
            "".join(node["instruction"]),
            tuple(node["result"]),
            tuple(self._freeze(child) for child in node["nested"]),
        )


def parse_complex_fields(parts: tuple[Part, ...] | list[Part]) -> tuple[ComplexField, ...]:
    stream = ComplexFieldStream()
    stream.feed(parts)
    return stream.finish()


def parse_text_unit_fields(unit) -> tuple[ComplexField, ...]:
    parts = tuple(part for fragment in unit.fragments for part in fragment.parts)
    return parse_complex_fields(parts)


def parse_text_units_fields(units) -> tuple[ComplexField, ...]:
    stream = ComplexFieldStream()
    for unit in units:
        stream.feed(tuple(part for fragment in unit.fragments for part in fragment.parts))
    return stream.finish()


def parse_event_stream_fields(events) -> tuple[ComplexField, ...]:
    """Parse complex fields while preserving state across consecutive TextUnit events."""
    stream = ComplexFieldStream()
    for event in events:
        resource = getattr(event, "resource", None)
        if resource is None or not hasattr(resource, "fragments"):
            continue
        parts = tuple(part for fragment in resource.fragments for part in fragment.parts)
        stream.feed(parts)
    return stream.finish()
