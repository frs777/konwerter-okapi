from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True, slots=True)
class Code:
    data: str
    kind: str
    target: str | None = None


@dataclass(frozen=True, slots=True)
class MarkupComponent:
    markup: "Markup"
    component_id: str
    parent_id: str | None = None
    matches: str | None = None
    properties: dict[str, str] | None = None
    role: str = "generic"
    styled: bool = False

    @property
    def kind(self) -> str:
        return self.markup.kind

    @property
    def name(self) -> str:
        return self.markup.name

    @property
    def attributes(self) -> tuple[tuple[str, str], ...]:
        return self.markup.attributes

    @property
    def data(self) -> str:
        return self.markup.data

    @classmethod
    def from_markup(cls, markup: "Markup", component_id: str, parent_id: str | None = None, matches: str | None = None, properties: dict[str, str] | None = None, role: str = "generic", styled: bool = False) -> "MarkupComponent":
        return cls(markup, component_id, parent_id, matches, properties, role, styled)

    @staticmethod
    def validate_sequence(components: tuple["MarkupComponent", ...] | list["MarkupComponent"]) -> None:
        stack: list[MarkupComponent] = []
        for component in components:
            if component.kind == "start":
                stack.append(component)
            elif component.kind == "end":
                if not stack or component.matches != stack[-1].component_id or component.name != stack[-1].name:
                    raise ValueError(f"mismatched markup component: {component.name}")
                stack.pop()
        if stack:
            raise ValueError("unclosed markup component")


@dataclass(frozen=True, slots=True)
class Markup:
    """Structured markup component preserved separately from translatable text."""

    kind: str
    name: str
    data: str = ""
    attributes: tuple[tuple[str, str], ...] = ()
    target: str | None = None

    @classmethod
    def start(
        cls,
        name: str,
        attributes: tuple[tuple[str, str], ...] = (),
        data: str = "",
        target: str | None = None,
    ) -> "Markup":
        return cls("start", name, data, attributes, target)

    @classmethod
    def end(cls, name: str, data: str = "") -> "Markup":
        return cls("end", name, data)

    @classmethod
    def empty(
        cls,
        name: str,
        attributes: tuple[tuple[str, str], ...] = (),
        data: str = "",
        target: str | None = None,
    ) -> "Markup":
        return cls("empty", name, data, attributes, target)


Part = Union[str, Code, Markup]


@dataclass(frozen=True, slots=True)
class TextFragment:
    parts: tuple[Part, ...]
    metadata: dict[str, str] | None = None
    style: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class TextUnit:
    id: str
    fragments: tuple[TextFragment, ...]
    metadata: dict[str, str] | None = None


SkeletonPart = Union[str, Markup]


@dataclass(frozen=True, slots=True)
class Skeleton:
    parts: tuple[SkeletonPart, ...]
    document_part: str | None = None
    parent_id: str | None = None
