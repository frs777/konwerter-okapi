"""Resolve an input document to a filter descriptor."""
from __future__ import annotations

import re
from pathlib import Path

from .registry import FilterDescriptor, FilterRegistry


_XML_NAMESPACE_TO_FORMAT = {
    "urn:oasis:names:tc:xliff:document:1.2": "xliff",
    "urn:oasis:names:tc:xliff:document:2.0": "xliff2",
}


class FilterResolver:
    def __init__(self, registry: FilterRegistry) -> None:
        self.registry = registry

    def resolve(
        self, source_path: Path, *, format: str | None = None, filter_id: str | None = None
    ) -> FilterDescriptor:
        extension = source_path.suffix.lower()
        candidates = self.registry.find_by_extension(extension)
        if filter_id is not None:
            candidates = tuple(item for item in candidates if item.id == filter_id)
        elif format is not None:
            candidates = tuple(item for item in candidates if item.format == format)
        if not candidates:
            if filter_id is not None:
                raise ValueError(f"unsupported filter for {extension or '<none>'}: {filter_id}")
            if format is not None:
                raise ValueError(f"unsupported format for {extension or '<none>'}: {format}")
            raise ValueError(f"unsupported document extension: {extension or '<none>'}")
        if len(candidates) == 1 or filter_id is not None or format is not None:
            return candidates[0]

        content_format = self._detect_content_format(source_path)
        if content_format is not None:
            matching = tuple(
                item for item in candidates if item.format == content_format
            )
            if len(matching) == 1:
                return matching[0]
        return candidates[0]

    @staticmethod
    def _detect_content_format(source_path: Path) -> str | None:
        """Detect formats whose extension is intentionally ambiguous."""
        try:
            head = source_path.read_text(encoding="utf-8")[:65536]
        except (OSError, UnicodeDecodeError):
            return None
        match = re.search(
            r'xmlns(?:\:[A-Za-z_][\w.-]*)?\s*=\s*["\']([^"\']+)["\']',
            head,
        )
        if match is None:
            return None
        return _XML_NAMESPACE_TO_FORMAT.get(match.group(1))
