"""Registry of format/filter descriptors, independent of Okapi classes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .capabilities import FilterCapabilities


@dataclass(frozen=True)
class FilterDescriptor:
    id: str
    backend_id: str
    format: str
    extensions: tuple[str, ...]
    mime_types: tuple[str, ...] = ()
    capabilities: FilterCapabilities = FilterCapabilities()
    priority: int = 0

    def __post_init__(self) -> None:
        normalized = tuple(ext.lower() if ext.startswith(".") else "." + ext.lower() for ext in self.extensions)
        object.__setattr__(self, "extensions", normalized)


class FilterRegistry:
    def __init__(self, descriptors: Iterable[FilterDescriptor] = ()) -> None:
        self._descriptors: list[FilterDescriptor] = []
        for descriptor in descriptors:
            self.register(descriptor)

    def register(self, descriptor: FilterDescriptor) -> None:
        if any(item.id == descriptor.id for item in self._descriptors):
            raise ValueError(f"filter already registered: {descriptor.id}")
        self._descriptors.append(descriptor)

    def find_by_extension(self, extension: str) -> tuple[FilterDescriptor, ...]:
        ext = extension.lower()
        if not ext.startswith("."):
            ext = "." + ext
        return tuple(sorted((d for d in self._descriptors if ext in d.extensions), key=lambda d: d.priority, reverse=True))
