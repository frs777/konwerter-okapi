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


def test_xliff_conversion_uses_native_python_implementation(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/xliff/runtime-xliff-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/xliff/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "native-python"


def test_generated_xliff_filter_reads_and_round_trips_source_text(tmp_path: Path):
    import importlib.util
    from importer.pipeline import OkapiConversionPipeline
    from core.events.model import EventType

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/xliff/runtime-xliff-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/xliff/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location("generated_xliff_filter", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = '<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file source-language="en" target-language="pl"><body><trans-unit id="1"><source>Hello <g id="1">world</g>.</source></trans-unit></body></file></xliff>'
    events = list(module.XLIFFFilter().read(source))
    units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]
    assert len(units) == 1
    assert units[0].metadata["trans_unit_id"] == "1"
    assert any(part == "Hello " for fragment in units[0].fragments for part in fragment.parts)
    assert module.XLIFFFilter().round_trip(source) == source


def test_native_xliff12_writer_supports_prefixed_namespace_tags():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff.filter import XLIFFFilter

    source = '<x:xliff xmlns:x="urn:oasis:names:tc:xliff:document:1.2"><x:file><x:body><x:trans-unit id="u"><x:source>Hello</x:source><x:target>Witaj</x:target></x:trans-unit></x:body></x:file></x:xliff>'
    filter_instance = XLIFFFilter()
    events = tuple(filter_instance.read(source))
    original = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = original.__class__(original.id, original.fragments, original.metadata, (TextFragment(("Cześć",)),))
    output = filter_instance.write(tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event for event in events))

    assert "<x:source>Hello</x:source>" in output
    assert "<x:target>Cześć</x:target>" in output


def test_native_xliff_preserves_and_writes_distinct_target_content():
    from core.events.model import EventType
    from filters.xliff.filter import XLIFFFilter

    source = '<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file source-language="en" target-language="pl"><body><trans-unit id="1"><source>Hello</source><target>Witaj</target></trans-unit></body></file></xliff>'
    filter_instance = XLIFFFilter()
    events = list(filter_instance.read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)

    assert unit.target_fragments is not None
    assert unit.target_fragments[0].parts == ("Witaj",)

    translated = unit.__class__(
        unit.id,
        unit.fragments,
        unit.metadata,
        target_fragments=(unit.target_fragments[0].__class__(("Cześć",)),),
    )
    from core.events.model import Event
    output = filter_instance.write((events[0], Event(EventType.TEXT_UNIT, translated), events[-1]))
    assert "<source>Hello</source>" in output
    assert "<target>Cześć</target>" in output


def test_native_xliff2_writer_supports_prefixed_namespace_tags():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<x:xliff xmlns:x="urn:oasis:names:tc:xliff:document:2.0"><x:file id="f"><x:unit id="u"><x:segment id="s"><x:source>Hello</x:source><x:target>Witaj</x:target></x:segment></x:unit></x:file></x:xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    original = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = original.__class__(original.id, original.fragments, original.metadata, (TextFragment(("Cześć",)),))
    output = filter_instance.write(tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event for event in events))

    assert "<x:source>Hello</x:source>" in output
    assert "<x:target>Cześć</x:target>" in output


def test_native_xliff2_inserts_target_when_translation_is_added_to_source_only_segment():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="u"><segment id="s1"><source>Hello</source></segment></unit></file></xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    original = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = original.__class__(original.id, original.fragments, original.metadata, (TextFragment(("Witaj",)),))
    output = filter_instance.write(tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event for event in events))

    assert "<source>Hello</source>" in output
    assert "<target>Witaj</target>" in output


def test_native_xliff2_reads_and_updates_each_segment_in_a_unit():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="u"><segment id="s1"><source>First</source><target>Uno</target></segment><segment id="s2"><source>Second</source><target>Dos</target></segment></unit></file></xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]

    assert len(units) == 2
    assert [unit.fragments[0].parts for unit in units] == [("First",), ("Second",)]
    second = units[1]
    translated = second.__class__(second.id, second.fragments, second.metadata, (TextFragment(("Deuxième",)),))
    changed_events = tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT and event.resource.id == second.id else event for event in events)
    output = filter_instance.write(changed_events)

    assert "<target>Uno</target>" in output
    assert "<target>Deuxième</target>" in output
    assert "<target>Dos</target>" not in output


def test_native_xliff12_represents_empty_inline_codes_as_empty_markup():
    from core.document.model import Markup
    from core.events.model import EventType
    from filters.xliff.filter import XLIFFFilter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file><body><trans-unit id="u"><source>Call <ph id="1"/> now</source></trans-unit></body></file></xliff>'
    events = tuple(XLIFFFilter().read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    parts = unit.fragments[0].parts

    assert "Call " in parts
    assert " now" in parts
    assert any(isinstance(part, Markup) and part.kind == "empty" and part.name == "ph" for part in parts)
    assert not any(isinstance(part, Markup) and part.kind == "start" and part.name == "ph" for part in parts)


def test_native_xliff2_preserves_nested_inline_markup_and_text():
    from core.document.model import Markup
    from core.events.model import EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="1"><segment><source>Say <pc id="1">very <ph id="2"/> well</pc>!</source></segment></unit></file></xliff>'
    events = tuple(XLIFF2Filter().read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    parts = unit.fragments[0].parts

    assert "very " in parts
    assert " well" in parts
    assert any(isinstance(part, Markup) and part.kind == "start" and part.name == "pc" for part in parts)
    assert any(isinstance(part, Markup) and part.kind == "end" and part.name == "pc" for part in parts)
    assert any(isinstance(part, Markup) and part.kind == "empty" and part.name == "ph" for part in parts)


def test_native_xliff2_preserves_and_writes_distinct_target_content():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="1"><segment><source>Hello</source><target>Witaj</target></segment></unit></file></xliff>'
    filter_instance = XLIFF2Filter()
    events = list(filter_instance.read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)

    assert unit.target_fragments is not None
    assert unit.target_fragments[0].parts == ("Witaj",)
    translated = unit.__class__(unit.id, unit.fragments, unit.metadata, (TextFragment(("Cześć",)),))
    output = filter_instance.write((events[0], Event(EventType.TEXT_UNIT, translated), events[-1]))
    assert "<source>Hello</source>" in output
    assert "<target>Cześć</target>" in output


def test_native_xliff2_round_trip_preserves_source_comments_and_cdata():
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="u"><segment><source><![CDATA[A & B]]><!--editor note--> remains</source><target>Old</target></segment></unit></file></xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    output = filter_instance.write(events)

    assert '<![CDATA[A & B]]>' in output
    assert '<!--editor note-->' in output
    assert '<target>Old</target>' in output


def test_native_xliff12_writer_updates_target_after_long_source_replacement():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff.filter import XLIFFFilter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:1.2"><file><body><trans-unit id="u"><source>Hi</source><target>Old</target></trans-unit></body></file></xliff>'
    filter_instance = XLIFFFilter()
    events = tuple(filter_instance.read(source))
    original = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = original.__class__(
        original.id,
        (TextFragment(("A much longer replacement source string",)),),
        original.metadata,
        (TextFragment(("A much longer target string",)),),
    )
    output = filter_instance.write(
        tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event for event in events)
    )

    assert "<source>A much longer replacement source string</source>" in output
    assert "<target>A much longer target string</target>" in output
    assert "<target>Old</target>" not in output


def test_native_xliff2_writer_updates_target_after_long_source_replacement():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0"><file id="f"><unit id="u"><segment id="s"><source>Hi</source><target>Old</target></segment></unit></file></xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    original = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = original.__class__(
        original.id,
        (TextFragment(("A much longer replacement source string",)),),
        original.metadata,
        (TextFragment(("A much longer target string",)),),
    )
    output = filter_instance.write(
        tuple(Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event for event in events)
    )

    assert "<source>A much longer replacement source string</source>" in output
    assert "<target>A much longer target string</target>" in output
    assert "<target>Old</target>" not in output


def test_xliff2_conversion_uses_native_python_implementation(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/xliff2/runtime-xliff2-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/xliff2/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "native-python"


def test_generated_xliff2_filter_reads_and_round_trips_segment_source(tmp_path: Path):
    import importlib.util
    from importer.pipeline import OkapiConversionPipeline
    from core.events.model import EventType

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/xliff2/runtime-xliff2-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/xliff2/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location("generated_xliff2_filter", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = '<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" srcLang="en" trgLang="pl"><file id="f1"><unit id="u1"><segment><source>Hello <ph id="1"/> world</source></segment></unit></file></xliff>'
    events = list(module.XLIFF2Filter().read(source))
    units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]
    assert len(units) == 1
    assert units[0].metadata["unit_id"] == "u1"
    assert any(part == "Hello " for fragment in units[0].fragments for part in fragment.parts)
    assert module.XLIFF2Filter().round_trip(source) == source


def test_epub_conversion_uses_native_python_implementation(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/epub/runtime-epub-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/epub/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "native-python"


def test_html_conversion_uses_native_python_implementation(tmp_path: Path):
    import json
    from importer.pipeline import OkapiConversionPipeline

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/html/runtime-html-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/html/filter.json"),
        tmp_path,
    )
    report = json.loads((result.output_dir / "conversion_report.json").read_text(encoding="utf-8"))
    assert report["behavior_source"] == "native-python"


def test_generated_html_filter_extracts_block_text_and_round_trips(tmp_path: Path):
    import importlib.util
    from importer.pipeline import OkapiConversionPipeline
    from core.events.model import EventType

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/html/runtime-html-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/html/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location("generated_html_filter", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = '<html><body><h1>Title</h1><p>Hello <b>world</b>.</p><script>ignore()</script></body></html>'
    filt = module.HtmlFilter()
    events = list(filt.read(source))
    units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]
    assert ["".join(part for fragment in u.fragments for part in fragment.parts if isinstance(part, str)) for u in units] == ["Title", "Hello world."]
    assert filt.round_trip(source) == source


def test_generated_html_filter_writes_changed_block_text(tmp_path: Path):
    import importlib.util
    from importer.pipeline import OkapiConversionPipeline
    from core.document.model import TextFragment, TextUnit
    from core.events.model import Event, EventType

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/html/runtime-html-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/html/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location("generated_html_filter_write", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    source = '<html><body><p>Hello world.</p><p>Second.</p></body></html>'
    filt = module.HtmlFilter(); events = tuple(filt.read(source))
    units = [e.resource for e in events if e.type is EventType.TEXT_UNIT]
    changed = [Event(EventType.TEXT_UNIT, TextUnit(u.id, (TextFragment(("Changed!",)),), u.metadata)) if u.id == "1" else Event(EventType.TEXT_UNIT, u) for u in units]
    assert "Changed!" in filt.write(changed)
    assert "Hello world." not in filt.write(changed)


def test_generated_epub_filter_reads_xhtml_members(tmp_path: Path):
    import importlib.util
    import io
    import zipfile
    from importer.pipeline import OkapiConversionPipeline
    from core.events.model import EventType

    result = OkapiConversionPipeline().convert(
        Path("testdata/okapi-filters-java/epub/runtime-epub-1.49.0-SNAPSHOT.jar"),
        Path("testdata/okapi-filters-java/epub/filter.json"),
        tmp_path,
    )
    spec = importlib.util.spec_from_file_location("generated_epub_filter", result.output_dir / "filter.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("OEBPS/chapter.xhtml", "<html><body><p>Hello EPUB.</p></body></html>")
        archive.writestr("OEBPS/image.png", b"not text")
    filt = module.EpubFilter(); events = list(filt.read(buffer.getvalue()))
    units = [e.resource for e in events if e.type is EventType.TEXT_UNIT]
    assert len(units) == 1
    assert units[0].metadata["epub_path"] == "OEBPS/chapter.xhtml"
    assert "Hello EPUB." in "".join(p for f in units[0].fragments for p in f.parts if isinstance(p, str))


def test_native_xliff12_translation_does_not_reserialize_source_inline_markup():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff.filter import XLIFFFilter

    source = '<x:xliff xmlns:x="urn:oasis:names:tc:xliff:document:1.2"><x:file><x:body><x:trans-unit id="u"><x:source>Hello <x:g id="1">world</x:g>.</x:source><x:target>Witaj <x:g id="1">świecie</x:g>.</x:target></x:trans-unit></x:body></x:file></x:xliff>'
    filter_instance = XLIFFFilter()
    events = tuple(filter_instance.read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = unit.__class__(unit.id, unit.fragments, unit.metadata, (TextFragment(("Cześć",)),))

    output = filter_instance.write(tuple(
        Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event
        for event in events
    ))

    assert '<x:source>Hello <x:g id="1">world</x:g>.</x:source>' in output
    assert '<x:target>Cześć</x:target>' in output


def test_native_xliff2_translation_does_not_reserialize_source_inline_markup():
    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.xliff2.filter import XLIFF2Filter

    source = '<x:xliff xmlns:x="urn:oasis:names:tc:xliff:document:2.0"><x:file id="f"><x:unit id="u"><x:segment id="s"><x:source>Hello <x:ph id="1"/> world</x:source><x:target>Witaj <x:ph id="1"/> świecie</x:target></x:segment></x:unit></x:file></x:xliff>'
    filter_instance = XLIFF2Filter()
    events = tuple(filter_instance.read(source))
    unit = next(event.resource for event in events if event.type is EventType.TEXT_UNIT)
    translated = unit.__class__(unit.id, unit.fragments, unit.metadata, (TextFragment(("Cześć",)),))

    output = filter_instance.write(tuple(
        Event(EventType.TEXT_UNIT, translated) if event.type is EventType.TEXT_UNIT else event
        for event in events
    ))

    assert '<x:source>Hello <x:ph id="1"/> world</x:source>' in output
    assert '<x:target>Cześć</x:target>' in output
