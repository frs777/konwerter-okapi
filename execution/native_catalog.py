"""Catalog of native Python filters with evidence-backed execution modes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from execution.backends.native import NativeFilterBackend
from execution.job import JobCoordinator
from execution.registry import FilterDescriptor, FilterRegistry
from execution.resolver import FilterResolver
from execution.service import ExecutionService

from filters.docx.filter import DocxFilter
from filters.epub.filter import EpubFilter
from filters.txt.filter import TxtFilter
from filters.html import HtmlFilter
from filters.xliff.filter import XLIFFFilter
from filters.xliff2.filter import XLIFF2Filter
from filters.json.filter import JsonFilter
from filters.markdown.filter import MarkdownFilter
from filters.yaml.filter import YamlFilter


@dataclass(frozen=True)
class NativeFilterSpec:
    """One directly executable native filter contract."""

    descriptor: FilterDescriptor
    factory: Callable[[], object]
    source_mode: str


def _spec(
    name: str,
    format_name: str,
    extensions: tuple[str, ...],
    factory: Callable[[], object],
    source_mode: str,
    *,
    mime_types: tuple[str, ...] = (),
) -> NativeFilterSpec:
    return NativeFilterSpec(
        descriptor=FilterDescriptor(
            id=f"native.{name}",
            backend_id="native",
            format=format_name,
            extensions=extensions,
            mime_types=mime_types,
            priority=100,
        ),
        factory=factory,
        source_mode=source_mode,
    )


def native_filter_specs() -> tuple[NativeFilterSpec, ...]:
    """Return native filters whose read/write contract is directly supported."""
    return (
        _spec(
            "txt",
            "txt",
            (".txt",),
            TxtFilter,
            "path",
            mime_types=("text/plain",),
        ),
        _spec(
            "docx",
            "docx",
            (".docx",),
            DocxFilter,
            "path",
            mime_types=("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
        ),
        _spec(
            "markdown",
            "markdown",
            (".md", ".markdown"),
            MarkdownFilter,
            "text",
            mime_types=("text/markdown",),
        ),
        _spec(
            "html",
            "html",
            (".html", ".htm", ".xhtml"),
            HtmlFilter,
            "path",
            mime_types=("text/html", "application/xhtml+xml"),
        ),
        _spec(
            "json",
            "json",
            (".json",),
            JsonFilter,
            "text",
            mime_types=("application/json",),
        ),
        _spec(
            "yaml",
            "yaml",
            (".yaml", ".yml"),
            YamlFilter,
            "text",
            mime_types=("application/yaml", "text/yaml"),
        ),
        _spec(
            "epub",
            "epub",
            (".epub",),
            EpubFilter,
            "path",
            mime_types=("application/epub+zip",),
        ),
        _spec(
            "xliff",
            "xliff",
            (".xlf", ".xliff"),
            XLIFFFilter,
            "text",
            mime_types=("application/xliff+xml", "application/xml"),
        ),
        _spec(
            "xliff2",
            "xliff2",
            (".xlf", ".xliff"),
            XLIFF2Filter,
            "text",
            mime_types=("application/xliff+xml", "application/xml"),
        ),
    )


def build_native_execution() -> tuple[FilterRegistry, NativeFilterBackend]:
    """Build the registry and backend from the single native catalog."""
    specs = native_filter_specs()
    registry = FilterRegistry(spec.descriptor for spec in specs)
    backend = NativeFilterBackend(
        {spec.descriptor.id: spec.factory for spec in specs},
        source_modes={spec.descriptor.id: spec.source_mode for spec in specs},
    )
    return registry, backend


def build_native_execution_service() -> ExecutionService:
    """Build the ready-to-use application service backed only by native filters."""
    registry, backend = build_native_execution()
    return ExecutionService(
        resolver=FilterResolver(registry),
        backends={"native": backend},
        coordinator=JobCoordinator(),
    )
