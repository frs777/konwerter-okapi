from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import importlib


def _inspector_class():
    spec = importlib.util.find_spec("analyzer.jar_inspector.inspector")
    assert spec is not None
    return importlib.import_module("analyzer.jar_inspector.inspector").JarInspector


def test_jar_inspector_reads_manifest_and_classes(tmp_path):
    jar = tmp_path / "sample.jar"
    with ZipFile(jar, "w", ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\nImplementation-Version: 1.2.3\n")
        archive.writestr("com/example/Filter.class", b"\xca\xfe\xba\xbe")
        archive.writestr("com/example/Helper.class", b"\xca\xfe\xba\xbe")
        archive.writestr("README.txt", "x")
    result = _inspector_class()().inspect(jar)
    assert result.path == Path(jar)
    assert result.manifest["Implementation-Version"] == "1.2.3"
    assert result.classes == ("com.example.Filter", "com.example.Helper")


def test_jar_inspector_rejects_non_jar(tmp_path):
    bad = tmp_path / "not.jar"
    bad.write_text("not a zip")
    try:
        _inspector_class()().inspect(bad)
    except ValueError as exc:
        assert "JAR" in str(exc)
    else:
        raise AssertionError("Inspektor powinien odrzucić niepoprawny JAR")


def test_filter_metadata_extractor_reads_filter_json(tmp_path):
    module = importlib.import_module("analyzer.metadata.extractor")
    path = tmp_path / "filter.json"
    path.write_text('{"name":"markdown","entry_class":"com.example.Filter","dependencies":[{"name":"Dep","artifact":"g:a:1"}]}')
    metadata = module.FilterMetadataExtractor().extract(path)
    assert metadata.name == "markdown"
    assert metadata.entry_class == "com.example.Filter"
    assert metadata.dependencies == ("g:a:1",)


def test_dependency_analyzer_collects_declared_and_jar_dependencies(tmp_path):
    module = importlib.import_module("analyzer.dependencies.analyzer")
    root = tmp_path / "deps"
    root.mkdir()
    (root / "filter.json").write_text('{"name":"x","entry_class":"X","dependencies":[{"artifact":"g:a:1"},{"artifact":"g:b:2"}]}')
    (root / "a.jar").write_bytes(b"not-a-jar")
    result = module.DependencyAnalyzer().analyze(root / "filter.json", [root / "a.jar"])
    assert result.declared == ("g:a:1", "g:b:2")
    assert result.jar_files == (root / "a.jar",)


def test_class_inspector_rejects_unknown_class(tmp_path):
    from analyzer.class_inspector.inspector import ClassInspector
    import pytest
    with pytest.raises(KeyError):
        ClassInspector().inspect_jar_class('testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar', 'missing.NoSuchClass')
