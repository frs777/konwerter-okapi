from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os
from analyzer.jar_inspector.inspector import JarInspector
from analyzer.metadata.extractor import FilterMetadata, FilterMetadataExtractor
from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor
from analyzer.java_probe.probe import JavaFilterProbe, JavaEvidence

@dataclass(frozen=True, slots=True)
class ExtractedFilter:
    metadata: FilterMetadata
    classes: tuple[str, ...]
    behavior: object | None = None
    source_path: Path | None = None
    java_evidence: JavaEvidence | None = None

def extract_filter(
    jar: str | Path,
    metadata_path: str | Path,
    source_root: str | Path | None = None,
) -> ExtractedFilter:
    inspection = JarInspector().inspect(jar)
    metadata = FilterMetadataExtractor().extract(metadata_path)
    behavior = None
    source = _discover_entry_source(metadata.entry_class, source_root)
    java_evidence = None
    try:
        classpath = _discover_runtime_classpath(source_root)
        java_evidence = JavaFilterProbe().probe(
            jar,
            metadata.entry_class,
            classpath=classpath,
        )
    except (FileNotFoundError, RuntimeError, OSError):
        # Static/source extraction remains authoritative fallback when the
        # optional JVM evidence cannot be collected for a particular filter.
        java_evidence = None
    if source is not None:
        extractor = JavaSourceBehaviorExtractor()
        class_name = metadata.entry_class.rsplit('.', 1)[-1]
        if class_name == 'MarkdownFilter':
            behavior = extractor.extract_markdown_filter(source)
        elif class_name == 'OpenXMLFilter':
            behavior = extractor.extract_openxml_filter(source)
        else:
            behavior = extractor.extract_generic_filter(source)
    if behavior is not None and java_evidence is not None:
        behavior = _merge_java_evidence(behavior, java_evidence)
    return ExtractedFilter(metadata, inspection.classes, behavior, source, java_evidence)

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


def _discover_runtime_classpath(source_root: str | Path | None) -> tuple[Path, ...]:
    if source_root is None:
        return ()
    root = Path(source_root)
    if not root.is_dir():
        return ()
    return tuple(sorted(root.rglob("*.jar")))


def _merge_java_evidence(behavior: object, evidence: JavaEvidence) -> object:
    # Keep source-derived semantics, but replace structural facts with facts
    # observed from the loaded class where they are available.
    from dataclasses import replace

    lifecycle = tuple(
        name for name in ("open", "next", "close", "hasNext")
        if name in evidence.public_methods
    )
    framework_contract = behavior.framework_contract
    if "net.sf.okapi.common.filters.IFilter" in evidence.interfaces:
        framework_contract = "net.sf.okapi.common.filters.IFilter"
    return replace(
        behavior,
        class_name=evidence.class_name,
        superclass=evidence.superclass,
        lifecycle_methods=lifecycle or behavior.lifecycle_methods,
        framework_contract=framework_contract,
        java_evidence=evidence,
    )
