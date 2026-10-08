from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from analyzer.jar_inspector.inspector import JarInspector
from analyzer.metadata.extractor import FilterMetadata, FilterMetadataExtractor
from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor

@dataclass(frozen=True, slots=True)
class ExtractedFilter:
    metadata: FilterMetadata
    classes: tuple[str, ...]
    behavior: object | None = None
    source_path: Path | None = None

def extract_filter(jar: str | Path, metadata_path: str | Path) -> ExtractedFilter:
    inspection = JarInspector().inspect(jar)
    metadata = FilterMetadataExtractor().extract(metadata_path)
    behavior = None
    source = _discover_entry_source(metadata.entry_class)
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

def _discover_entry_source(entry_class: str) -> Path | None:
    class_name = entry_class.rsplit('.', 1)[-1] + '.java'
    root = Path('/home/frs/Projekty/Okapi-main/okapi/filters')
    if not root.exists():
        return None
    matches = sorted(root.rglob(class_name))
    return matches[0] if matches else None
