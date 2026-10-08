from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
from analyzer.jar_inspector.inspector import JarInspector
from analyzer.metadata.extractor import FilterMetadata, FilterMetadataExtractor
from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor

@dataclass(frozen=True, slots=True)
class ExtractedFilter:
    metadata: FilterMetadata
    classes: tuple[str, ...]
    behavior: object | None = None
    source_path: Path | None = None

def extract_filter(
    jar: str | Path,
    metadata_path: str | Path,
    source_root: str | Path | None = None,
) -> ExtractedFilter:
    inspection = JarInspector().inspect(jar)
    metadata = FilterMetadataExtractor().extract(metadata_path)
    behavior = None
    source = _discover_entry_source(metadata.entry_class, source_root)
    if source is not None:
        extractor = JavaSourceBehaviorExtractor()
        class_name = metadata.entry_class.rsplit('.', 1)[-1]
        if class_name == 'MarkdownFilter':
            behavior = extractor.extract_markdown_filter(source)
        elif class_name == 'OpenXMLFilter':
            behavior = extractor.extract_openxml_filter(source)
        else:
            behavior = extractor.extract_generic_filter(source)
    return ExtractedFilter(metadata, inspection.classes, behavior, source)

def _discover_entry_source(
    entry_class: str,
    source_root: str | Path | None = None,
) -> Path | None:
    root = Path(source_root) if source_root is not None else _default_source_root()
    if root is None:
        return None
    if not root.is_dir():
        return None
    class_name = entry_class.rsplit(".", 1)[-1] + ".java"
    matches = sorted(root.rglob(class_name))
    return matches[0] if matches else None


def _default_source_root() -> Path | None:
    configured = os.environ.get("OKAPI_SOURCE_ROOT")
    if configured:
        root = Path(configured).expanduser()
        return root if root.is_dir() else None

    cwd = Path.cwd().resolve()
    candidates = []
    for parent in (cwd, *cwd.parents):
        candidates.extend(
            (
                parent / "Okapi-main" / "okapi" / "filters",
                parent / "okapi" / "filters",
            )
        )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
