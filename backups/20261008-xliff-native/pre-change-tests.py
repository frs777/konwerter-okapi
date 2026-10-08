from pathlib import Path


def test_conversion_pipeline_generates_python_package_and_ir(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/markdown/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    assert result.output_dir == tmp_path / "markdown"
    assert (result.output_dir / "filter.py").exists()
    assert (result.output_dir / "filter_ir.json").exists()
    assert (result.output_dir / "conversion_report.json").exists()

    ir = (result.output_dir / "filter_ir.json").read_text(encoding="utf-8")
    assert '"name": "markdown"' in ir
    assert '"text/markdown"' in ir


def test_conversion_pipeline_reports_adapter_features(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/markdown/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    assert "inline_code" in result.adapter_report.required_features


def test_conversion_pipeline_rejects_missing_metadata(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    missing = tmp_path / "missing.json"

    try:
        OkapiConversionPipeline().convert(jar, missing, tmp_path)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Brak metadanych powinien zostać zgłoszony")


def test_conversion_cli_converts_real_markdown_jar(tmp_path: Path):
    import json
    import subprocess
    import sys

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/markdown/filter.json")
    command = [
        sys.executable, "tools/okapi_convert.py",
        str(jar), "--metadata", str(metadata), "--output", str(tmp_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(completed.stdout)
    assert payload["filter"] == "markdown"
    assert Path(payload["output_dir"]).joinpath("filter.py").exists()


def test_generated_filter_contains_parameters_from_ir(tmp_path: Path):
    from importer.python_generation.generator import PythonFilterGenerator
    from filter_ir.model.filter import FilterIR, ParameterRule

    ir = FilterIR(
        "sample", "1.0", ("text/plain",), (".sample",), ("text",),
        parameters=("translateUrls", "urlPattern"),
        parameter_rules=(
            ParameterRule("translateUrls", "boolean", False),
            ParameterRule("urlPattern", "string", ".+"),
        ),
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    parameters = (output / "parameters.py").read_text(encoding="utf-8")
    assert "class SampleParameters" in parameters
    assert "translate_urls: bool = False" in parameters
    assert "url_pattern: str = '.+'" in parameters


def test_conversion_pipeline_uses_openxml_source_behavior(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    jar = Path("testdata/okapi-filters-java/openxml/runtime-openxml-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/openxml/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    assert "application/xml" in result.ir.mime_types
    assert ".docx" in result.ir.extensions
    assert "zip_package" in result.ir.features
    assert "translateWordHeadersFooters" in result.ir.parameters
    assert any(rule.name == "maxAttributeSize" for rule in result.ir.parameter_rules)


def test_generated_filter_exposes_contract_metadata_and_lifecycle(tmp_path: Path):
    from importer.python_generation.generator import PythonFilterGenerator
    from filter_ir.model.filter import FilterIR

    ir = FilterIR(
        "contract_sample", "1.0", ("application/xml",), (".xml",), ("zip_package", "skeleton"),
        superclass="net.sf.okapi.common.filters.IFilter",
        lifecycle_methods=("open", "hasNext", "next", "close"),
        framework_contract="net.sf.okapi.common.filters.IFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    source = (output / "filter.py").read_text(encoding="utf-8")
    assert "class ContractSampleFilter" in source
    assert "def open(" in source
    assert "def has_next(" in source
    assert "def next(" in source
    assert "def close(" in source
    assert "mime_types" in source
    assert "application/xml" in source


def test_extractor_discovers_source_by_entry_class_without_filter_name_dispatch():
    from importer.extraction.metadata import extract_filter

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/markdown/filter.json")
    extracted = extract_filter(jar, metadata)
    assert extracted.source_path is not None
    assert extracted.source_path.name == "MarkdownFilter.java"
    assert extracted.behavior is not None


def test_generated_filter_uses_java_entry_class_name(tmp_path: Path):
    from importer.python_generation.generator import PythonFilterGenerator
    from filter_ir.model.filter import FilterIR

    ir = FilterIR("openxml", "1.0", ("application/xml",), (".docx",), ("zip_package",), entry_class="OpenXMLFilter")
    output = PythonFilterGenerator().generate(ir, tmp_path)
    source = (output / "filter.py").read_text(encoding="utf-8")
    assert "class OpenXMLFilter" in source


def test_conversion_report_records_entry_class_and_behavior_source(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    jar = Path("testdata/okapi-filters-java/openxml/runtime-openxml-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/openxml/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["entry_class"] == "OpenXMLFilter"
    assert report["behavior_source"] == "contract-adapter"


def test_html_pipeline_uses_generic_source_behavior(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline
    jar = Path("testdata/okapi-filters-java/html/runtime-html-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/html/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)
    assert result.ir.entry_class == "HtmlFilter"
    assert result.ir.lifecycle_methods


def test_generated_markdown_filter_uses_native_python_behavior(tmp_path: Path):
    import importlib.util

    from importer.pipeline import OkapiConversionPipeline
    from core.document.model import Code

    jar = Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar")
    metadata = Path("testdata/okapi-filters-java/markdown/filter.json")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    spec = importlib.util.spec_from_file_location("generated_markdown_filter", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    events = module.MarkdownFilter().read("**bold**")
    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    assert any(isinstance(part, Code) and part.kind == "bold" for unit in text_units for fragment in unit.fragments for part in fragment.parts)


def test_markdown_conversion_report_declares_native_python_behavior(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/markdown/runtime-markdown-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/markdown/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["entry_class"] == "MarkdownFilter"
    assert report["behavior_source"] == "native-python"


def test_generator_uses_rule_generated_strategy_for_token_rules(tmp_path: Path):
    import importlib.util

    from core.document.model import Code
    from filter_ir.model.filter import FilterIR, TokenRule
    from importer.python_generation.generator import PythonFilterGenerator

    ir = FilterIR(
        "rule_sample", "1.0", ("text/plain",), (".sample",), ("text", "inline_code"),
        token_rules=(TokenRule("STRONG_EMPHASIS", "bold", "paired", False),),
        entry_class="RuleSampleFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    spec = importlib.util.spec_from_file_location("generated_rule_filter", output / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    events = module.RuleSampleFilter().read("**bold**")
    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    assert any(isinstance(part, Code) and part.kind == "bold" for unit in text_units for fragment in unit.fragments for part in fragment.parts)


def test_rule_generated_conversion_report_is_explicit(tmp_path: Path):
    import json

    from filter_ir.model.filter import FilterIR, TokenRule
    from importer.python_generation.generator import PythonFilterGenerator

    ir = FilterIR(
        "rule_report", "1.0", ("text/plain",), (".rule",), ("text",),
        token_rules=(TokenRule("EMPHASIS", "italic", "paired", False),),
        entry_class="RuleReportFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    report = json.loads((output / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "rule-generated"


def test_generator_does_not_claim_rule_generated_for_unsupported_token_strategy(tmp_path: Path):
    from filter_ir.model.filter import FilterIR, TokenRule
    from importer.python_generation.generator import PythonFilterGenerator
    import json

    ir = FilterIR(
        "unsupported_rule", "1.0", ("text/plain",), (".rule",), ("text",),
        token_rules=(TokenRule("CODE", "inline_code", "isolated", False),),
        entry_class="UnsupportedRuleFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    report = json.loads((output / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "contract-adapter"
    assert report["unsupported_token_rules"] == ["CODE:isolated"]


def test_conversion_pipeline_batch_converts_filter_catalog(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    root = Path("testdata/okapi-filters-java")
    results = OkapiConversionPipeline().convert_catalog(root, tmp_path)

    assert [result.ir.name for result in results] == [
        "epub", "html", "json", "markdown", "openoffice", "openxml", "xliff", "xliff2", "yaml",
    ]
    assert all((result.output_dir / "filter.py").exists() for result in results)
    assert all((result.output_dir / "filter_ir.json").exists() for result in results)
    assert all((result.output_dir / "conversion_report.json").exists() for result in results)


def test_conversion_cli_converts_catalog(tmp_path: Path):
    import json
    import subprocess
    import sys

    completed = subprocess.run(
        [
            sys.executable, "tools/okapi_convert.py",
            "--catalog", "testdata/okapi-filters-java", "--output", str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    assert [item["filter"] for item in payload] == [
        "epub", "html", "json", "markdown", "openoffice", "openxml", "xliff", "xliff2", "yaml",
    ]


def test_conversion_report_quantifies_token_rule_coverage(tmp_path: Path):
    import json

    from filter_ir.model.filter import FilterIR, TokenRule
    from importer.python_generation.generator import PythonFilterGenerator

    ir = FilterIR(
        "coverage_sample", "1.0", ("text/plain",), (".sample",), ("text",),
        token_rules=(
            TokenRule("STRONG_EMPHASIS", "bold", "paired", False),
            TokenRule("CODE", "inline_code", "isolated", False),
        ),
        entry_class="CoverageSampleFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    report = json.loads((output / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["token_rule_coverage"] == {"supported": 1, "total": 2, "ratio": 0.5}
    assert report["unsupported_token_rules"] == ["CODE:isolated"]


def test_conversion_report_lists_unsupported_features_explicitly(tmp_path: Path):
    import json

    from filter_ir.model.filter import FilterIR
    from importer.python_generation.generator import PythonFilterGenerator

    ir = FilterIR(
        "feature_sample", "1.0", ("text/plain",), (".sample",),
        ("text", "subfilter", "tables"), entry_class="FeatureSampleFilter",
    )
    output = PythonFilterGenerator().generate(ir, tmp_path)
    report = json.loads((output / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["unsupported_features"] == ["subfilter"]

def test_conversion_ir_preserves_parameters_used_by_source_behavior(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/json/runtime-json-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/json/filter.json"),
        tmp_path,
    )
    assert "extractStandalone" in result.ir.used_parameters
    assert "useKeyAsName" in result.ir.used_parameters
    assert "useFullKeyPath" in result.ir.used_parameters

def test_conversion_report_lists_source_parameters_used_by_filter(tmp_path: Path):
    import json

    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/json/runtime-json-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/json/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert "extractStandalone" in report["used_parameters"]
    assert "useKeyAsName" in report["used_parameters"]


def test_json_uses_native_python_implementation(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    metadata = Path("testdata/okapi-filters-java/json/filter.json")
    jar = Path("testdata/okapi-filters-java/json/runtime-json-1.49.0-SNAPSHOT.jar")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    import json
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "native-python"


def test_generated_json_filter_executes_native_round_trip(tmp_path: Path):
    from importer.pipeline import OkapiConversionPipeline

    metadata = Path("testdata/okapi-filters-java/json/filter.json")
    jar = Path("testdata/okapi-filters-java/json/runtime-json-1.49.0-SNAPSHOT.jar")
    result = OkapiConversionPipeline().convert(jar, metadata, tmp_path)

    import importlib.util
    spec = importlib.util.spec_from_file_location("generated_json_filter", result.output_dir / "filter.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    events = module.JSONFilter(parameters={"extractStandalone": True}).read('{"root": {"title": "Hello"}, "items": ["One", "Two"]}')
    units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    assert [unit.metadata["json_path"] for unit in units] == ["/root/title", "/items/0", "/items/1"]
    assert module.JSONFilter().round_trip('{"root": {"title": "Hello"}}') == '{"root": {"title": "Hello"}}'


def test_json_native_report_does_not_mark_implemented_subfilter_as_unsupported(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/json/runtime-json-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/json/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert "subfilter" not in report["unsupported_features"]

def test_yaml_conversion_uses_native_python_implementation(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/yaml/runtime-yaml-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/yaml/filter.json"),
        tmp_path,
    )
    report = json.loads(
        (result.output_dir / "conversion_report.json").read_text(encoding="utf-8")
    )
    assert report["behavior_source"] == "native-python"
    assert report["unsupported_features"] == ["skeleton", "subfilter"]


def test_generated_yaml_filter_executes_native_round_trip(tmp_path: Path):
    import importlib.util
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/yaml/runtime-yaml-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/yaml/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location(
        "generated_yaml_filter", result.output_dir / "filter.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = 'title: "Hello world"\nitems:\n  - One\n'
    filter_instance = module.YamlFilter()
    assert filter_instance.round_trip(source) == source
