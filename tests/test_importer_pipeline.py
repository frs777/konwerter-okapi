from pathlib import Path

from filter_ir.model.filter import FilterIR


def test_importer_generates_python_filter_from_ir(tmp_path: Path):
    from importer.python_generation.generator import PythonFilterGenerator
    ir = FilterIR("markdown", "1.0", ("text/markdown",), (".md",), ("text", "inline_code"))
    output = PythonFilterGenerator().generate(ir, tmp_path)
    assert (output / "filter.py").exists()
    assert "class MarkdownFilter" in (output / "filter.py").read_text()


def test_importer_reports_features_requiring_adapter(tmp_path: Path):
    from importer.validation.report import AdapterReport
    report = AdapterReport.from_ir(FilterIR("x", "1", ("x/test",), (".x",), ("tables", "protected")))
    assert report.required_features == ("protected", "tables")


def test_ir_generation_uses_declared_metadata(tmp_path: Path):
    from analyzer.metadata.extractor import FilterMetadata
    from importer.extraction.metadata import ExtractedFilter
    from importer.ir_generation.generator import filter_ir_from_extracted
    extracted = ExtractedFilter(FilterMetadata("markdown", "net.sf.okapi.filters.markdown.MarkdownFilter", ()), ("A.class",))
    ir = filter_ir_from_extracted(extracted)
    assert ir.name == "markdown"
    assert ir.version == "1.0"
    assert ir.features == ("text",)


def test_generated_filter_is_executable(tmp_path: Path):
    from importer.python_generation.generator import PythonFilterGenerator
    ir = FilterIR("sample", "1.0", ("text/plain",), (".sample",), ("text",))
    output = PythonFilterGenerator().generate(ir, tmp_path)
    import sys
    sys.path.insert(0, str(output.parent))
    try:
        from sample.filter import SampleFilter
        assert SampleFilter().round_trip('Zażółć 😀') == 'Zażółć 😀'
    finally:
        sys.path.pop(0)


def test_extraction_uses_real_okapi_jar_and_metadata(tmp_path: Path):
    from importer.extraction.metadata import extract_filter
    metadata_path = tmp_path / 'filter.json'
    metadata_path.write_text('{"name":"markdown","entry_class":"net.sf.okapi.filters.markdown.MarkdownFilter","dependencies":[]}', encoding='utf-8')
    extracted = extract_filter('testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar', metadata_path)
    assert extracted.metadata.entry_class.endswith('MarkdownFilter')
    assert 'net.sf.okapi.filters.markdown.MarkdownFilter' in extracted.classes



def test_ir_generation_preserves_extracted_behavior_rules():
    from analyzer.metadata.extractor import FilterMetadata
    from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor
    from importer.extraction.metadata import ExtractedFilter
    from importer.ir_generation.generator import filter_ir_from_extracted

    source = Path('/home/frs/Projekty/Okapi-main/okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/MarkdownFilter.java')
    behavior = JavaSourceBehaviorExtractor().extract_markdown_filter(source)
    extracted = ExtractedFilter(FilterMetadata("markdown", "net.sf.okapi.filters.markdown.MarkdownFilter", ()), (), behavior)
    ir = filter_ir_from_extracted(extracted)
    assert any(rule.name == "translateUrls" for rule in ir.parameter_rules)
    assert any(rule.token_type == "FENCED_CODE_BLOCK" for rule in ir.token_rules)


def test_importer_preserves_filter_framework_contract():
    from analyzer.metadata.source_extractor import JavaSourceBehaviorExtractor
    from importer.extraction.metadata import ExtractedFilter
    from analyzer.metadata.extractor import FilterMetadata
    from importer.ir_generation.generator import filter_ir_from_extracted

    source = '/home/frs/Projekty/Okapi-main/okapi/filters/markdown/src/main/java/net/sf/okapi/filters/markdown/MarkdownFilter.java'
    behavior = JavaSourceBehaviorExtractor().extract_markdown_filter(source)
    extracted = ExtractedFilter(
        FilterMetadata('okf_markdown', behavior.class_name, ()),
        (),
        behavior,
    )
    ir = filter_ir_from_extracted(extracted)
    assert ir.superclass == 'AbstractFilter'
    assert ir.framework_contract == 'net.sf.okapi.common.filters.AbstractFilter'
    assert 'open' in ir.lifecycle_methods
    assert 'next' in ir.lifecycle_methods


def test_extraction_discovers_entry_source_only_from_explicit_source_root(tmp_path):
    from importer.extraction.metadata import _discover_entry_source

    source_root = tmp_path / "okapi" / "filters"
    source_dir = source_root / "sample" / "src" / "main" / "java"
    source_dir.mkdir(parents=True)
    source = source_dir / "SampleFilter.java"
    source.write_text("public class SampleFilter {}", encoding="utf-8")

    assert _discover_entry_source(
        "net.sf.okapi.filters.sample.SampleFilter", source_root
    ) == source


def test_conversion_pipeline_accepts_explicit_okapi_source_root(tmp_path):
    from importer.pipeline import OkapiConversionPipeline

    metadata_path = tmp_path / "filter.json"
    metadata_path.write_text(
        '{"name":"sample","entry_class":"net.sf.okapi.filters.sample.SampleFilter","dependencies":[]}',
        encoding="utf-8",
    )
    source_root = tmp_path / "okapi" / "filters"
    source_dir = source_root / "sample" / "src" / "main" / "java"
    source_dir.mkdir(parents=True)
    (source_dir / "SampleFilter.java").write_text(
        "public class SampleFilter implements IFilter { public void open() {} public boolean hasNext() { return false; } public void close() {} }",
        encoding="utf-8",
    )
    jar = tmp_path / "sample.jar"
    import zipfile
    with zipfile.ZipFile(jar, "w") as zf:
        zf.writestr("net/sf/okapi/filters/sample/SampleFilter.class", b"\xca\xfe\xba\xbe\x00\x00\x00\x34\x00\x01")

    result = OkapiConversionPipeline().convert(
        jar, metadata_path, tmp_path / "out", source_root=source_root
    )
    assert result.ir.entry_class == "SampleFilter"
