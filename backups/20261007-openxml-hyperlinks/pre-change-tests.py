from core.events.model import EventType
from pathlib import Path
import importlib
import importlib.util

def _reader_class():
    spec = importlib.util.find_spec("filters.docx.reader")
    assert spec is not None, "Brakuje modułu filters.docx.reader"
    return importlib.import_module("filters.docx.reader").DocxReader

def _text_units():
    DocxReader = _reader_class()
    events = list(DocxReader().read(Path("fixtures/docx/reference.docx")))
    return [event.resource for event in events if event.type.value == "TEXT_UNIT"], events

def test_docx_reader_preserves_multiple_runs_as_inline_parts():
    units, _ = _text_units()
    assert any("Pogrubiony" in [part for fragment in unit.fragments for part in fragment.parts] and "i kursywa" in [part for fragment in unit.fragments for part in fragment.parts] for unit in units)

def test_docx_reader_preserves_unicode_text():
    units, _ = _text_units()
    assert any("Zażółć gęślą jaźń — 漢字 — 😀" in part for unit in units for fragment in unit.fragments for part in fragment.parts if isinstance(part, str))

def test_docx_reader_ignores_empty_text_runs_without_losing_paragraph():
    units, _ = _text_units()
    assert any(any("Pusty run" in part for fragment in unit.fragments for part in fragment.parts if isinstance(part, str)) for unit in units)

def test_docx_reader_marks_nested_non_translatable_elements_as_protected():
    units, _ = _text_units()
    assert any(getattr(part, "kind", None) == "protected" and "NIE TŁUMACZ" in getattr(part, "data", "") for unit in units for fragment in unit.fragments for part in fragment.parts if not isinstance(part, str))

def test_docx_reader_preserves_style_metadata_on_text_units():
    units, _ = _text_units()
    styled = [unit for unit in units if getattr(unit, "metadata", None)]
    assert styled
    assert any(unit.metadata.get("style") == "Heading1" for unit in styled)

def test_docx_reader_emits_end_document():
    _, events = _text_units()
    assert events[-1].type.value == "END_DOCUMENT"


def test_docx_reader_preserves_numbering_metadata(tmp_path):
    from zipfile import ZipFile
    from filters.docx.reader import DocxReader

    target = tmp_path / "numbered.docx"
    document = '''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="7"/></w:numPr></w:pPr><w:r><w:t>Punkt</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'''
    with ZipFile(target, "w") as archive:
        archive.writestr("word/document.xml", document)
    units = [e.resource for e in DocxReader().read(target) if e.type.value == "TEXT_UNIT"]
    assert units[0].metadata["num_id"] == "7"
    assert units[0].metadata["num_level"] == "1"


def test_docx_reader_extracts_footnotes_and_endnotes_as_document_parts():
    from filters.docx.reader import DocxReader
    p = Path("fixtures/docx/okapi/1413-notes.docx")
    units = [e.resource for e in DocxReader().read(p) if e.type == EventType.TEXT_UNIT]
    assert any((u.metadata or {}).get("part") == "footnote" and "Footnote for text" in "".join(str(x) for f in u.fragments for x in f.parts) for u in units)
    assert any((u.metadata or {}).get("part") == "endnote" and "Endnote for extra text" in "".join(str(x) for f in u.fragments for x in f.parts) for u in units)


def test_docx_reader_skips_deleted_revision_text():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/1370-same-nested-revisions.docx")
    units = [e.resource for e in DocxReader().read(p) if e.type == EventType.TEXT_UNIT]
    parts = [
        part
        for u in units
        for fragment in u.fragments
        for part in fragment.parts
        if hasattr(part, "data")
    ]
    assert not any(getattr(part, "data", None) == "A text box" for part in parts)


def test_docx_reader_smokes_official_okapi_docx_corpus():
    from filters.docx.reader import DocxReader
    corpus = sorted(Path("fixtures/docx/okapi").glob("*.docx"))
    assert len(corpus) >= 5
    for path in corpus:
        events = list(DocxReader().read(path))
        assert events[0].type == EventType.START_DOCUMENT
        assert events[-1].type == EventType.END_DOCUMENT


def test_docx_reader_extracts_comments_as_document_parts():
    from filters.docx.reader import DocxReader
    p = Path("fixtures/docx/okapi/Addcomments.docx")
    units = [e.resource for e in DocxReader().read(p) if e.type == EventType.TEXT_UNIT]
    assert any((u.metadata or {}).get("part") == "comment" and (u.metadata or {}).get("comment_id") == "2" for u in units)
    assert any("comment" in "".join(str(x) for x in u.fragments[0].parts).lower() for u in units if (u.metadata or {}).get("part") == "comment" and (u.metadata or {}).get("comment_id") == "2")


def test_docx_reader_skips_hidden_runs_by_default():
    from zipfile import ZipFile
    from filters.docx.reader import DocxReader

    target = Path("/tmp/docx-hidden-default.docx")
    document = '''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t>Ukryty</w:t></w:r><w:r><w:t>Widoczny</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'''
    with ZipFile(target, "w") as archive:
        archive.writestr("word/document.xml", document)

    units = [e.resource for e in DocxReader().read(target) if e.type == EventType.TEXT_UNIT]
    strings = [part for unit in units for fragment in unit.fragments for part in fragment.parts if isinstance(part, str)]
    assert "Ukryty" not in strings
    assert "Widoczny" in strings


def test_docx_reader_can_include_hidden_runs_when_enabled():
    from zipfile import ZipFile
    from filters.docx.reader import DocxReader

    target = Path("/tmp/docx-hidden-enabled.docx")
    document = '''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t>Ukryty</w:t></w:r><w:r><w:t>Widoczny</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'''
    with ZipFile(target, "w") as archive:
        archive.writestr("word/document.xml", document)

    units = [e.resource for e in DocxReader(translate_word_hidden=True).read(target) if e.type == EventType.TEXT_UNIT]
    strings = [part for unit in units for fragment in unit.fragments for part in fragment.parts if isinstance(part, str)]
    assert "Ukryty" in strings
    assert "Widoczny" in strings


def test_docx_reader_extracts_referenced_numbering_level_text_when_enabled():
    from filters.docx.reader import DocxReader

    source = Path("fixtures/docx/okapi/1313-numbering-1.docx")
    units = [e.resource for e in DocxReader(translate_word_numbering_level_text=True).read(source) if e.type == EventType.TEXT_UNIT]
    numbering = [u for u in units if (u.metadata or {}).get("part") == "numbering"]
    assert len(numbering) == 1
    assert numbering[0].metadata["num_id"] == "1"
    assert numbering[0].metadata["num_level"] == "0"
    assert "TestBefore" in "".join(part for f in numbering[0].fragments for part in f.parts if isinstance(part, str))


def test_docx_reader_preserves_direct_run_properties():
    from zipfile import ZipFile
    from filters.docx.reader import DocxReader

    target = Path("/tmp/docx-run-properties.docx")
    document = '''<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:rPr><w:b/><w:i/><w:u w:val="single"/><w:color w:val="FF0000"/><w:sz w:val="28"/><w:rFonts w:ascii="Arial"/></w:rPr><w:t>Styled</w:t></w:r><w:r><w:t>Plain</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'''
    with ZipFile(target, "w") as archive:
        archive.writestr("word/document.xml", document)
    units = [e.resource for e in DocxReader().read(target) if e.type == EventType.TEXT_UNIT]
    fragments = units[0].fragments
    assert fragments[0].parts == ("Styled",)
    assert fragments[0].metadata == {"bold": "true", "italic": "true", "underline": "single", "color": "FF0000", "size": "28", "font": "Arial"}
    assert fragments[1].parts == ("Plain",)
    assert fragments[1].metadata is None

def test_reader_preserves_bookmarks_and_complex_field_boundaries():
    from filters.docx.reader import DocxReader
    events = list(DocxReader().read("fixtures/docx/okapi/1083-date-and-hyperlink-instructions.docx"))
    codes = [
        part for event in events if getattr(event, "resource", None)
        for fragment in getattr(event.resource, "fragments", ())
        for part in fragment.parts if not isinstance(part, str)
    ]
    kinds = [code.kind for code in codes]
    assert "bookmark_start" in kinds
    assert "field_instruction" in kinds and "field_char" in kinds

def test_direct_run_properties_preserve_explicit_toggle_false():
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    run = ET.fromstring(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:rPr><w:b w:val="0"/><w:vanish w:val="false"/></w:rPr><w:t>x</w:t></w:r>'
    )
    props = DocxReader()._run_properties(run)
    assert props == {"bold": "false", "hidden": "false"}

def test_markup_component_parser_preserves_namespace_attributes_and_order():
    from xml.etree import ElementTree as ET
    from filters.docx.markup import MarkupComponentParser
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    element = ET.fromstring(
        '<w:proofErr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'w:type="spellStart" w:custom="x"/>'
    )
    parser = MarkupComponentParser()
    component = parser.start(element)
    assert component.kind == "start"
    assert component.name == "w:proofErr"
    assert component.attributes == (("w:custom", "x"), ("w:type", "spellStart"))


def test_markup_component_parser_builds_nested_skeleton():
    from xml.etree import ElementTree as ET
    from filters.docx.markup import MarkupComponentParser
    root = ET.fromstring(
        '<root><a x="1"><b>text</b></a></root>'
    )
    skeleton = MarkupComponentParser().skeleton(root)
    assert [(p.kind, p.name) for p in skeleton.parts] == [
        ("start", "root"), ("start", "a"), ("start", "b"), ("end", "b"), ("end", "a"), ("end", "root")
    ]

def test_reader_accepts_inserted_revision_as_translatable_text():
    from filters.docx.reader import DocxReader
    from xml.etree import ElementTree as ET

    paragraph = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:ins w:id="7"><w:r><w:t>added</w:t></w:r></w:ins>'
        '</w:p>'
    )
    fragments = DocxReader()._collect_paragraph_fragments(paragraph, {})
    parts = [p for f in fragments for p in f.parts]
    assert "added" in parts
    assert not any(getattr(p, "kind", None) == "revision" for p in parts)


def test_reader_skips_deleted_revision_content_by_default():
    from filters.docx.reader import DocxReader
    from xml.etree import ElementTree as ET

    paragraph = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:r><w:t>kept</w:t></w:r>'
        '<w:del w:id="8"><w:r><w:delText>removed</w:delText></w:r></w:del>'
        '</w:p>'
    )
    fragments = DocxReader()._collect_paragraph_fragments(paragraph, {})
    parts = [p for f in fragments for p in f.parts]
    assert "kept" in parts
    assert "removed" not in parts


def test_markup_component_parser_assigns_matching_component_ids_and_parentage():
    from xml.etree import ElementTree as ET
    from filters.docx.markup import MarkupComponentParser
    root = ET.fromstring('<w:ins xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:id="7"><w:hyperlink w:anchor="x"><w:r/></w:hyperlink></w:ins>')
    components = MarkupComponentParser().components(root)
    assert [c.kind for c in components] == ["start", "start", "start", "end", "end", "end"]
    assert components[0].component_id == "mc-1"
    assert components[1].component_id == "mc-2"
    assert components[2].parent_id == "mc-2"
    assert components[3].matches == "mc-3"
    assert components[5].matches == "mc-1"


def test_markup_component_sequence_rejects_mismatched_end_component():
    from core.document.model import Markup, MarkupComponent
    sequence = [MarkupComponent.from_markup(Markup.start("w:a"), "mc-1"), MarkupComponent.from_markup(Markup.end("w:b"), "mc-2")]
    try:
        MarkupComponent.validate_sequence(sequence)
    except ValueError as exc:
        assert "mismatched" in str(exc)
    else:
        raise AssertionError("expected mismatched component failure")


def test_markup_skeleton_preserves_document_part_identity_and_parent():
    from core.document.model import Markup, MarkupComponent, Skeleton
    skeleton = Skeleton((Markup.start("w:tbl"), Markup.end("w:tbl")), document_part="word/document.xml")
    assert skeleton.document_part == "word/document.xml"
    assert skeleton.parent_id is None
    assert isinstance(MarkupComponent.from_markup(Markup.start("w:tbl"), "mc-1"), MarkupComponent)


def test_markup_component_parser_classifies_openxml_specialized_components():
    from xml.etree import ElementTree as ET
    from filters.docx.markup import MarkupComponentParser

    root = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:pPr/><w:r><w:rPr/><w:t>x</w:t></w:r><w:tblPr/></w:p>'
    )
    parser = MarkupComponentParser()
    roles = [c.role for c in parser.components(root)]
    assert "block_properties" in roles
    assert "run_properties" in roles
    assert roles.count("block_properties") == 4


def test_markup_component_preserves_styled_context():
    from xml.etree import ElementTree as ET
    from filters.docx.markup import MarkupComponentParser

    root = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr></w:p>'
    )
    components = MarkupComponentParser().components(root)
    assert any(c.role == "block_properties" and c.styled for c in components)


def test_docx_writer_emits_real_complex_field_markers():
    from xml.etree import ElementTree as ET
    from core.document.model import Code, TextFragment, TextUnit
    from filters.docx.writer import DocxWriter, W
    from zipfile import ZipFile

    target = "tests/.tmp-complex-field.docx"
    unit = TextUnit("1", (TextFragment((
        Code("begin", "field_char"),
        Code(" PAGE ", "field_instruction"),
        Code("separate", "field_char"),
        "1",
        Code("end", "field_char"),
    )),))
    from core.events.model import Event, EventType
    DocxWriter().write([Event(EventType.TEXT_UNIT, unit)], target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": W}
    assert root.find('.//w:fldChar[@w:fldCharType="begin"]', ns) is not None
    assert root.find('.//w:instrText', ns).text == " PAGE "
    assert root.find('.//w:fldChar[@w:fldCharType="separate"]', ns) is not None
    assert root.find('.//w:fldChar[@w:fldCharType="end"]', ns) is not None


def test_docx_reader_preserves_hyperlink_runs_as_nested_markup():
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader

    paragraph = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<w:hyperlink r:id="rId7"><w:r><w:t>A</w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t>B</w:t></w:r></w:hyperlink>'
        '</w:p>'
    )
    fragments = DocxReader()._collect_paragraph_fragments(paragraph, {"rId7": "https://example.test"})
    parts = [part for f in fragments for part in f.parts]
    assert parts[0].kind == "start" and parts[0].name == "w:hyperlink"
    assert parts[-1].kind == "end" and parts[-1].name == "w:hyperlink"
    assert "A" in parts and "B" in parts


def test_docx_reader_extracts_textbox_paragraphs_from_drawing():
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    events = list(DocxReader().read("fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"))
    units = [e.resource for e in events if e.type == EventType.TEXT_UNIT]
    textbox_units = [u for u in units if (u.metadata or {}).get("text_box") == "true"]
    assert len(textbox_units) == 2
    assert any("okapiframework" in "".join(p.data for f in u.fragments for p in f.parts if hasattr(p, "data")) for u in textbox_units)

def test_reader_treats_inserted_revision_text_as_translatable():
    from filters.docx.reader import DocxReader
    from xml.etree import ElementTree as ET

    paragraph = ET.fromstring(
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:ins w:id="7"><w:r><w:t>added</w:t></w:r></w:ins>'
        '</w:p>'
    )
    fragments = DocxReader()._collect_paragraph_fragments(paragraph, {})
    parts = [part for fragment in fragments for part in fragment.parts]
    assert "added" in parts
    assert not any(
        getattr(part, "kind", None) == "revision"
        for part in parts
        if hasattr(part, "kind")
    )

def test_docx_reader_extracts_translatable_core_properties(tmp_path):
    from zipfile import ZipFile
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    target = tmp_path / "core-properties.docx"
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>Body</w:t></w:r></w:p><w:sectPr/></w:body></w:document>'
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:title>Document title</dc:title>'
        '<dc:creator>Author</dc:creator>'
        '<dc:description>Description</dc:description>'
        '<cp:category>Category</cp:category>'
        '<cp:keywords>one, two</cp:keywords>'
        '<cp:lastModifiedBy>Do not translate</cp:lastModifiedBy>'
        '</cp:coreProperties>'
    )
    with ZipFile(target, "w") as archive:
        archive.writestr("word/document.xml", document)
        archive.writestr("docProps/core.xml", core)

    units = [e.resource for e in DocxReader().read(target) if e.type == EventType.TEXT_UNIT]
    values = [
        part
        for unit in units
        for fragment in unit.fragments
        for part in fragment.parts
        if isinstance(part, str)
    ]
    assert "Document title" in values
    assert "Author" in values
    assert "Description" in values
    assert "Category" in values
    assert "one, two" in values
    assert "Do not translate" not in values

def test_docx_reader_extracts_word_graphic_names_as_translatable_text():
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    source = Path("/home/frs/Projekty/Okapi-main/okapi/filters/openxml/src/test/resources/1406-code-finding.docx")
    units = [e.resource for e in DocxReader().read(source) if e.type == EventType.TEXT_UNIT]
    values = [
        part
        for unit in units
        for fragment in unit.fragments
        for part in fragment.parts
        if isinstance(part, str)
    ]
    assert "1406, docPr, text box, issue #1406" in values
    assert "1406, docPr, issue #1406" in values


def test_docx_reader_supports_okapi_style_exclusion_mode():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/styles.docx")
    units = [e.resource for e in DocxReader(
        translate_word_in_exclude_style_mode=True,
        exclude_word_styles={"Title"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    strings = [
        part for unit in units for fragment in unit.fragments
        for part in fragment.parts if isinstance(part, str)
    ]
    assert "Title" not in strings
    assert "Heading 1" in strings
    assert "Subtitle" in strings


def test_docx_reader_supports_okapi_style_inclusion_mode():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/styles.docx")
    units = [e.resource for e in DocxReader(
        translate_word_in_exclude_style_mode=False,
        exclude_word_styles={"Title"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    body_units = [u for u in units if (u.metadata or {}).get("part", "body") == "body"]
    strings = [
        part for unit in body_units for fragment in unit.fragments
        for part in fragment.parts if isinstance(part, str)
    ]
    assert strings == ["Title"]


def test_docx_reader_style_inclusion_masks_unlisted_run_styles():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/1394-styles.docx")
    units = [e.resource for e in DocxReader(
        translate_word_in_exclude_style_mode=False,
        exclude_word_styles={"Emphasis"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    body = [u for u in units if (u.metadata or {}).get("part", "body") == "body"]
    assert len(body) == 1
    strings = [part for f in body[0].fragments for part in f.parts if isinstance(part, str)]
    assert strings == ["styled text"]
    codes = [part for f in body[0].fragments for part in f.parts if hasattr(part, "kind")]
    assert any(getattr(code, "kind", None) == "excluded_style" and getattr(code, "data", "") == "Regular text and " for code in codes)

def test_docx_reader_excludes_runs_by_font_color():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/colors.docx")
    units = [e.resource for e in DocxReader(
        translate_word_exclude_colors=True,
        exclude_word_colors={"FF0000"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    strings = [part for u in units for f in u.fragments for part in f.parts if isinstance(part, str)]
    codes = [part for u in units for f in u.fragments for part in f.parts if hasattr(part, "kind")]
    assert "I am red" not in strings
    assert any(getattr(code, "kind", None) == "excluded_style" and getattr(code, "data", "") == "I am red" for code in codes)
    assert "I am black" in strings and "I am green" in strings


def test_docx_reader_excludes_highlighted_runs_by_color():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/highlights.docx")
    units = [e.resource for e in DocxReader(
        translate_word_in_exclude_highlight_mode=True,
        word_highlight_colors={"FFFF00"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    strings = [part for u in units for f in u.fragments for part in f.parts if isinstance(part, str)]
    codes = [part for u in units for f in u.fragments for part in f.parts if hasattr(part, "kind")]
    assert all("highlighted" not in s for s in strings)
    assert any(getattr(code, "kind", None) == "excluded_style" and "highlighted" in getattr(code, "data", "") for code in codes)
    assert "Test 4" in strings and "5" in strings and "6" in strings


def test_docx_reader_includes_only_configured_highlight_color():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/highlights.docx")
    units = [e.resource for e in DocxReader(
        translate_word_in_exclude_highlight_mode=False,
        word_highlight_colors={"FFFF00"},
    ).read(p) if e.type == EventType.TEXT_UNIT]
    strings = [part for u in units for f in u.fragments for part in f.parts if isinstance(part, str)]
    codes = [part for u in units for f in u.fragments for part in f.parts if hasattr(part, "kind")]
    assert any("highlighted" in s for s in strings)
    assert "Test 4" not in strings and "5" not in strings and "6" not in strings

def test_docx_reader_preserves_display_text_for_style_color_and_highlight_exclusions():
    from filters.docx.reader import DocxReader

    p = Path("fixtures/docx/okapi/1433-text-for-masking.docx")
    units = [e.resource for e in DocxReader(
        translate_word_exclude_colors=True,
        exclude_word_colors={"Red"},
        translate_word_in_exclude_highlight_mode=True,
        word_highlight_colors={"Yellow"},
        translate_word_in_exclude_style_mode=True,
        exclude_word_styles={"Heading1Char"},
    ).read(p) if e.type == EventType.TEXT_UNIT and (e.resource.metadata or {}).get("part") != "core_properties"]
    assert len(units) == 1
    strings = [part for f in units[0].fragments for part in f.parts if isinstance(part, str)]
    codes = [part for f in units[0].fragments for part in f.parts if hasattr(part, "kind")]
    assert any("and normal text." in value for value in strings)
    assert len(codes) >= 3
    assert any("Excluded by highlight" in getattr(c, "data", "") for c in codes)
    assert any("excluded by color" in getattr(c, "data", "") for c in codes)
    assert any("excluded by style" in getattr(c, "data", "") for c in codes)
