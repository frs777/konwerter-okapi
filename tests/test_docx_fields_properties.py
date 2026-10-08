from core.document.model import Code
from filters.docx.fields import ComplexField, FieldState, parse_complex_fields
from filters.docx.properties import RunPropertySet

def test_complex_field_tracks_instruction_result_and_nested_depth():
    parts = (
        Code("begin", "field_char"),
        Code(" HYPERLINK \"x\" ", "field_instruction"),
        Code("separate", "field_char"),
        "Label",
        Code("begin", "field_char"),
        Code(" PAGE ", "field_instruction"),
        Code("separate", "field_char"),
        "2",
        Code("end", "field_char"),
        Code("end", "field_char"),
    )
    fields = parse_complex_fields(parts)
    assert len(fields) == 1
    field = fields[0]
    assert field.instruction.strip().startswith("HYPERLINK")
    assert field.result == ("Label",)
    assert field.nested[0].instruction.strip() == "PAGE"
    assert field.nested[0].result == ("2",)

def test_field_state_rejects_unbalanced_end():
    try:
        parse_complex_fields((Code("end", "field_char"),))
    except ValueError as exc:
        assert "without begin" in str(exc)
    else:
        raise AssertionError("expected ValueError")

def test_run_property_set_merge_and_minify():
    base = RunPropertySet({"bold": "true", "color": "000000", "font": "Arial"})
    override = RunPropertySet({"color": "FF0000", "italic": "true"})
    merged = base.merge(override)
    assert merged.values == {"bold": "true", "color": "FF0000", "font": "Arial", "italic": "true"}
    assert merged.minify(base).values == {"color": "FF0000", "italic": "true"}

def test_run_property_set_font_mapping():
    props = RunPropertySet({"font": "Arial", "font_cs": "Arial"})
    mapped = props.map_fonts({"Arial": "Noto Sans"})
    assert mapped.values["font"] == "Noto Sans"
    assert mapped.values["font_cs"] == "Noto Sans"

def test_text_unit_field_parser_spans_fragment_boundaries():
    from core.document.model import TextFragment, TextUnit
    from filters.docx.fields import parse_text_unit_fields
    unit = TextUnit("1", (
        TextFragment((Code("begin", "field_char"),)),
        TextFragment((Code(" PAGE ", "field_instruction"), Code("separate", "field_char"))),
        TextFragment(("42",)),
        TextFragment((Code("end", "field_char"),)),
    ))
    fields = parse_text_unit_fields(unit)
    assert fields[0].instruction.strip() == "PAGE"
    assert fields[0].result == ("42",)

def test_writer_preserves_explicit_false_toggle_properties(tmp_path):
    from core.events.model import Event, EventType
    from core.document.model import TextFragment, TextUnit
    from filters.docx.writer import DocxWriter
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    target = tmp_path / "false-toggle.docx"
    unit = TextUnit("1", (TextFragment(("x",), {"bold": "false", "hidden": "false"}),))
    DocxWriter().write([Event(EventType.TEXT_UNIT, unit)], target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    rpr = root.find(".//w:rPr", ns)
    assert rpr.find("w:b", ns).get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == "false"
    assert rpr.find("w:vanish", ns).get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") == "false"



def test_complex_field_exposes_nested_depth_and_count():
    parts = (
        Code("begin", "field_char"), Code(" IF ", "field_instruction"), Code("separate", "field_char"), "outer",
        Code("begin", "field_char"), Code(" IF ", "field_instruction"), Code("separate", "field_char"), "middle",
        Code("begin", "field_char"), Code(" PAGE ", "field_instruction"), Code("separate", "field_char"), "3", Code("end", "field_char"),
        Code("end", "field_char"), Code("end", "field_char"),
    )
    field = parse_complex_fields(parts)[0]
    assert field.depth == 3
    assert field.nested_count == 2

def test_complex_fields_can_span_multiple_text_units():
    from filters.docx.reader import DocxReader
    from filters.docx.fields import parse_event_stream_fields
    from core.events.model import EventType

    units = [
        event.resource
        for event in DocxReader().read("fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx")
        if event.type == EventType.TEXT_UNIT
    ]
    fields = parse_event_stream_fields(
        event for event in DocxReader().read("fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx")
    )
    assert fields
    assert any(field.instruction.strip().startswith("HYPERLINK") for field in fields)


def test_complex_field_stream_spans_text_units_and_preserves_nested_fields():
    from filters.docx.fields import ComplexFieldStream

    stream = ComplexFieldStream()
    stream.feed((
        Code("begin", "field_char"),
        Code(" HYPERLINK \\\"x\\\" ", "field_instruction"),
        Code("separate", "field_char"),
        "visible ",
    ))
    assert stream.fields == ()
    stream.feed((
        Code("begin", "field_char"),
        Code(" PAGE ", "field_instruction"),
        Code("separate", "field_char"),
        "1",
        Code("end", "field_char"),
        Code("end", "field_char"),
    ))
    fields = stream.finish()
    assert len(fields) == 1
    assert fields[0].instruction == ' HYPERLINK \\\"x\\\" '
    assert fields[0].result == ("visible ",)
    assert len(fields[0].nested) == 1
    assert fields[0].nested[0].instruction == " PAGE "
    assert fields[0].nested[0].result == ("1",)


def test_reader_preserves_all_openxml_font_categories():
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    run = ET.fromstring(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Calibri" w:cs="Amiri" '
        'w:eastAsia="Noto Sans CJK" w:asciiTheme="majorHAnsi" w:hAnsiTheme="minorHAnsi" '
        'w:cstheme="majorBidi" w:eastAsiaTheme="majorEastAsia" w:hint="eastAsia"/></w:rPr><w:t>x</w:t></w:r>'
    )
    props = DocxReader()._run_properties(run)
    assert props == {
        "font_ascii": "Arial", "font_hAnsi": "Calibri", "font_cs": "Amiri", "font_eastAsia": "Noto Sans CJK",
        "font_asciiTheme": "majorHAnsi", "font_hAnsiTheme": "minorHAnsi",
        "font_cstheme": "majorBidi", "font_eastAsiaTheme": "majorEastAsia", "font_hint": "eastAsia",
        "font": "Arial",
    }


def test_writer_emits_all_openxml_font_categories(tmp_path):
    from core.events.model import Event, EventType
    from core.document.model import TextFragment, TextUnit
    from filters.docx.writer import DocxWriter
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    target = tmp_path / "fonts.docx"
    metadata = {
        "font_ascii": "Arial", "font_hAnsi": "Calibri", "font_cs": "Amiri", "font_eastAsia": "Noto Sans CJK",
        "font_asciiTheme": "majorHAnsi", "font_hAnsiTheme": "minorHAnsi",
        "font_cstheme": "majorBidi", "font_eastAsiaTheme": "majorEastAsia", "font_hint": "eastAsia",
    }
    DocxWriter().write([Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(("x",), metadata),)))], target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    fonts = root.find(".//w:rFonts", ns)
    assert fonts is not None
    assert fonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ascii") == "Arial"
    assert fonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hAnsi") == "Calibri"
    assert fonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}cs") == "Amiri"
    assert fonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia") == "Noto Sans CJK"
    assert fonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}hint") == "eastAsia"


def test_writer_round_trips_two_level_nested_complex_field(tmp_path):
    from core.events.model import Event, EventType
    from core.document.model import TextFragment, TextUnit
    from filters.docx.writer import DocxWriter
    from filters.docx.reader import DocxReader
    from filters.docx.fields import parse_text_unit_fields

    target = tmp_path / "nested-fields.docx"
    unit = TextUnit("1", (TextFragment((
        Code("begin", "field_char"),
        Code(" IF ", "field_instruction"),
        Code("separate", "field_char"),
        "outer ",
        Code("begin", "field_char"),
        Code(" PAGE ", "field_instruction"),
        Code("separate", "field_char"),
        "7",
        Code("end", "field_char"),
        Code("end", "field_char"),
    ),),))

    DocxWriter().write([Event(EventType.TEXT_UNIT, unit)], target)
    reread = [event.resource for event in DocxReader().read(target) if event.type == EventType.TEXT_UNIT]
    fields = parse_text_unit_fields(reread[0])
    assert len(fields) == 1
    assert fields[0].instruction.strip() == "IF"
    assert fields[0].result == ("outer ",)
    assert len(fields[0].nested) == 1
    assert fields[0].nested[0].instruction.strip() == "PAGE"
    assert fields[0].nested[0].result == ("7",)


def test_writer_round_trip_preserves_resolved_vs_direct_run_properties(tmp_path):
    from core.events.model import Event, EventType
    from core.document.model import TextFragment, TextUnit
    from filters.docx.writer import DocxWriter
    from filters.docx.reader import DocxReader
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET

    target = tmp_path / "minify.docx"
    fragment = TextFragment(("x",), {"bold": "true"}, {"resolved_bold": "true", "resolved_color": "000000"})
    DocxWriter().write([Event(EventType.TEXT_UNIT, TextUnit("1", (fragment,)))], target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    rpr = root.find(".//w:rPr", ns)
    assert rpr.find("w:b", ns) is not None
    assert rpr.find("w:color", ns) is None
    events = list(DocxReader().read(target))
    unit = next(e.resource for e in events if e.type == EventType.TEXT_UNIT)
    assert unit.fragments[0].metadata == {"bold": "true"}


def test_writer_round_trip_preserves_textbox_structure_and_field_across_paragraphs(tmp_path):
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter
    from filters.docx.fields import parse_event_stream_fields
    from core.events.model import EventType
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    target = tmp_path / "textbox-roundtrip.docx"
    events = list(DocxReader().read(source))
    DocxWriter().write(events, target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    assert root.find(".//w:drawing", ns) is not None
    assert root.find(".//w:txbxContent", ns) is not None
    roundtrip_events = list(DocxReader().read(target))
    fields = parse_event_stream_fields(roundtrip_events)
    assert any(f.instruction.strip().startswith("HYPERLINK") for f in fields)
    assert any((u.metadata or {}).get("text_box") == "true" for e in roundtrip_events if e.type == EventType.TEXT_UNIT for u in [e.resource])


def test_writer_round_trip_preserves_nested_complex_fields_in_real_stream(tmp_path):
    from core.document.model import Code, TextFragment, TextUnit
    from core.events.model import Event, EventType
    from filters.docx.writer import DocxWriter
    from filters.docx.reader import DocxReader
    from filters.docx.fields import parse_event_stream_fields

    target = tmp_path / "nested-fields.docx"
    parts = (
        Code("begin", "field_char"), Code(" IF ", "field_instruction"), Code("separate", "field_char"), "outer",
        Code("begin", "field_char"), Code(" PAGE ", "field_instruction"), Code("separate", "field_char"), "7", Code("end", "field_char"),
        Code("end", "field_char"),
    )
    events = [Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment(parts[:4]),))), Event(EventType.TEXT_UNIT, TextUnit("2", (TextFragment(parts[4:]),)))]
    DocxWriter().write(events, target)
    fields = parse_event_stream_fields(DocxReader().read(target))
    assert len(fields) == 1
    assert fields[0].instruction.strip() == "IF"
    assert fields[0].result == ("outer",)
    assert fields[0].nested[0].instruction.strip() == "PAGE"
    assert fields[0].nested[0].result == ("7",)


def test_reader_integrates_complex_field_stream_across_text_units():
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter
    from core.document.model import Code, TextFragment, TextUnit
    from core.events.model import Event, EventType

    source = "fixtures/docx/okapi/1083-date-and-hyperlink-instructions.docx"
    reader = DocxReader()
    list(reader.read(source))
    assert reader.complex_fields
    assert any(field.instruction.strip() for field in reader.complex_fields)

    events = [
        Event(EventType.TEXT_UNIT, TextUnit("1", (TextFragment((Code("begin", "field_char"), Code(" PAGE ", "field_instruction"), Code("separate", "field_char"), "1")),))),
        Event(EventType.TEXT_UNIT, TextUnit("2", (TextFragment((Code("end", "field_char"),)),))),
    ]
    target = __import__("pathlib").Path("/tmp/complex-field-reader-integration.docx")
    DocxWriter().write(events, target)
    roundtrip_reader = DocxReader()
    list(roundtrip_reader.read(target))
    assert roundtrip_reader.complex_fields[0].instruction.strip() == "PAGE"


def test_textbox_preserves_drawingml_and_vml_templates(tmp_path):
    import json
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    target = tmp_path / "textbox-templates.docx"
    events = list(DocxReader().read(source))
    textbox = next(e.resource for e in events if e.type == EventType.TEXT_UNIT and (e.resource.metadata or {}).get("text_box") == "true")
    meta = textbox.metadata or {}
    assert "textbox_drawingml" in meta
    assert "textbox_vml" in meta
    drawing = json.loads(meta["textbox_drawingml"])
    vml = json.loads(meta["textbox_vml"])
    assert drawing["tag"].endswith("anchor")
    assert drawing["attrib"]["{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId"] == "7F96FC78"
    assert vml["tag"].endswith("shape")
    assert "margin-left:313.4pt" in vml["attrib"]["style"]

    DocxWriter().write(events, target)
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    anchor = root.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor")
    shape = root.find(".//{urn:schemas-microsoft-com:vml}shape")
    assert anchor is not None
    assert shape is not None
    assert anchor.attrib["{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId"] == "7F96FC78"
    assert shape.attrib["style"] == vml["attrib"]["style"]


def test_textbox_visual_container_structure_survives_round_trip(tmp_path):
    from pathlib import Path
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter

    source = Path("fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx")
    target = tmp_path / "textbox-structure.docx"
    DocxWriter().write(list(DocxReader().read(source)), target)

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
    V = "urn:schemas-microsoft-com:vml"

    def canonical(node):
        node = ET.fromstring(ET.tostring(node, encoding="unicode"))
        for content in node.iter(f"{{{W}}}txbxContent"):
            for child in list(content):
                content.remove(child)
        def canon(elem):
            elem.attrib.clear() if False else None
            attrs = tuple(sorted(elem.attrib.items()))
            children = tuple(canon(child) for child in list(elem))
            return (elem.tag, attrs, children)
        return canon(node)

    with ZipFile(source) as zin, ZipFile(target) as zout:
        source_root = ET.fromstring(zin.read("word/document.xml"))
        target_root = ET.fromstring(zout.read("word/document.xml"))

    source_anchors = [canonical(n) for n in source_root.iter(f"{{{WP}}}anchor")]
    target_anchors = [canonical(n) for n in target_root.iter(f"{{{WP}}}anchor")]
    source_shapes = [canonical(n) for n in source_root.iter(f"{{{V}}}shape")]
    target_shapes = [canonical(n) for n in target_root.iter(f"{{{V}}}shape")]

    assert source_anchors == target_anchors
    assert source_shapes == target_shapes


def test_textbox_geometry_and_visual_properties_round_trip(tmp_path):
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    target = tmp_path / "textbox-visual.docx"
    events = list(DocxReader().read(source))
    DocxWriter().write(events, target)
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    }
    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    anchor = root.find(".//wp:anchor", ns)
    assert anchor is not None
    assert anchor.attrib["distL"] == "114300"
    assert anchor.find("wp:positionH/wp:posOffset", ns).text == "3980443"
    assert anchor.find("wp:positionV/wp:posOffset", ns).text == "303375"
    assert anchor.find("wp:wrapNone", ns) is not None
    xfrm = anchor.find(".//a:xfrm", ns)
    assert xfrm is not None
    assert xfrm.find("a:ext", ns).attrib["cx"] == "2219960"
    body_pr = anchor.find(".//wps:bodyPr", ns)
    assert body_pr is not None
    assert body_pr.attrib["{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}rot"] == "0" if "{http://schemas.microsoft.com/office/word/2010/wordprocessingShape}rot" in body_pr.attrib else body_pr.attrib.get("rot") == "0"



def test_textbox_fallback_emits_complete_geometry_and_visual_containers(tmp_path):
    from core.document.model import TextFragment, TextUnit
    from core.events.model import Event, EventType
    from filters.docx.writer import DocxWriter
    from zipfile import ZipFile
    from xml.etree import ElementTree as ET

    target = tmp_path / "textbox-fallback.docx"
    metadata = {"text_box": "true", "text_box_index": "0"}
    unit = TextUnit("1", (TextFragment(("fallback",), metadata),), metadata)
    DocxWriter().write([Event(EventType.TEXT_UNIT, unit)], target)

    with ZipFile(target) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    ns = {
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
        "v": "urn:schemas-microsoft-com:vml",
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    }
    anchor = root.find(".//wp:anchor", ns)
    assert anchor is not None
    assert anchor.find("wp:positionH/wp:posOffset", ns) is not None
    assert anchor.find("wp:positionV/wp:posOffset", ns) is not None
    assert anchor.find("wp:extent", ns) is not None
    assert anchor.find("wp:effectExtent", ns) is not None
    assert anchor.find("wp:wrapNone", ns) is not None
    assert anchor.find(".//a:xfrm/a:ext", ns) is not None
    assert anchor.find(".//wps:bodyPr", ns) is not None
    assert anchor.find(".//wps:spPr", ns) is not None
    assert root.find(".//v:shape", ns) is not None



def test_docx_reader_keeps_distinct_identical_textboxes(tmp_path):
    from zipfile import ZipFile, ZIP_DEFLATED
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    target = tmp_path / "duplicate-textboxes.docx"
    ns = {
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    with ZipFile(source) as zin:
        document = ET.fromstring(zin.read("word/document.xml"))
        anchor = document.find(".//wp:anchor", ns)
        assert anchor is not None
        duplicate = ET.fromstring(ET.tostring(anchor, encoding="unicode"))
        anchor_id = "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId"
        duplicate.set(anchor_id, "DUPL0001")
        pos_offset = duplicate.find("wp:positionH/wp:posOffset", ns)
        assert pos_offset is not None
        pos_offset.text = str(int(pos_offset.text or "0") + 100000)
        anchor_parent = next(parent for parent in document.iter() if anchor in list(parent))
        anchor_parent.append(duplicate)
        with ZipFile(target, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = ET.tostring(document, encoding="utf-8", xml_declaration=True) if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)

    units = [
        event.resource
        for event in DocxReader().read(target)
        if event.type == EventType.TEXT_UNIT
        and (event.resource.metadata or {}).get("text_box") == "true"
    ]
    assert len(units) == 4
    assert [u.metadata["text_box_index"] for u in units] == ["0", "1", "2", "3"]
    assert [u.metadata["text_box_id"] for u in units] == [
        "anchor-id:7F96FC78",
        "anchor-id:7F96FC78",
        "anchor-id:DUPL0001",
        "anchor-id:DUPL0001",
    ]



def test_docx_reader_deduplicates_each_textbox_representation_per_paragraph(tmp_path):
    from zipfile import ZipFile, ZIP_DEFLATED
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    target = tmp_path / "duplicate-representation.docx"
    with ZipFile(source) as zin:
        document = ET.fromstring(zin.read("word/document.xml"))
        anchor = document.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor")
        shape = document.find(".//{urn:schemas-microsoft-com:vml}shape")
        assert anchor is not None and shape is not None
        # Keep the existing anchor/VML pair as one logical TextBox and add
        # another complete pair with a distinct identity.
        anchor_copy = ET.fromstring(ET.tostring(anchor, encoding="unicode"))
        shape_copy = ET.fromstring(ET.tostring(shape, encoding="unicode"))
        aid = "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId"
        anchor_copy.set(aid, "DUPL0002")
        shape_copy.set("{http://schemas.microsoft.com/office/word/2010/wordml}anchorId", "DUPL0002")
        pos = anchor_copy.find("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}positionH/{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}posOffset")
        assert pos is not None
        pos.text = str(int(pos.text or "0") + 200000)
        parent = next(parent for parent in document.iter() if anchor in list(parent))
        parent.append(anchor_copy)
        vml_parent = next(parent for parent in document.iter() if shape in list(parent))
        vml_parent.append(shape_copy)
        with ZipFile(target, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = ET.tostring(document, encoding="utf-8", xml_declaration=True) if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)

    units = [e.resource for e in DocxReader().read(target) if e.type == EventType.TEXT_UNIT and (e.resource.metadata or {}).get("text_box") == "true"]
    assert len(units) == 4
    assert [u.metadata["text_box_index"] for u in units] == ["0", "1", "2", "3"]



def test_docx_writer_round_trips_distinct_identical_textboxes(tmp_path):
    from zipfile import ZipFile, ZIP_DEFLATED
    from xml.etree import ElementTree as ET
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1341-textbox-with-a-hyperlink.docx"
    modified = tmp_path / "two-textboxes.docx"
    target = tmp_path / "roundtrip.docx"
    with ZipFile(source) as zin:
        document = ET.fromstring(zin.read("word/document.xml"))
        anchor = document.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor")
        shape = document.find(".//{urn:schemas-microsoft-com:vml}shape")
        assert anchor is not None and shape is not None
        anchor_copy = ET.fromstring(ET.tostring(anchor, encoding="unicode"))
        shape_copy = ET.fromstring(ET.tostring(shape, encoding="unicode"))
        anchor_copy.set("{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId", "DUPL0003")
        shape_copy.set("{http://schemas.microsoft.com/office/word/2010/wordml}anchorId", "DUPL0003")
        parent = next(parent for parent in document.iter() if anchor in list(parent))
        parent.append(anchor_copy)
        vml_parent = next(parent for parent in document.iter() if shape in list(parent))
        vml_parent.append(shape_copy)
        with ZipFile(modified, "w", ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = ET.tostring(document, encoding="utf-8", xml_declaration=True) if item.filename == "word/document.xml" else zin.read(item.filename)
                zout.writestr(item, data)

    events = list(DocxReader().read(modified))
    DocxWriter().write(events, target)
    roundtrip = list(DocxReader().read(target))
    units = [e.resource for e in roundtrip if e.type == EventType.TEXT_UNIT and (e.resource.metadata or {}).get("text_box") == "true"]
    assert len(units) == 4
    with ZipFile(target) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    assert len(root.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}anchor")) == 2
    assert len(root.findall(".//{urn:schemas-microsoft-com:vml}shape")) == 2



def test_docx_reader_pairs_vml_without_anchor_id_with_drawingml_textbox():
    from filters.docx.reader import DocxReader
    from core.events.model import EventType

    source = "fixtures/docx/okapi/1370-same-nested-revisions.docx"
    units = [
        e.resource
        for e in DocxReader().read(source)
        if e.type == EventType.TEXT_UNIT
        and (e.resource.metadata or {}).get("text_box") == "true"
    ]
    assert len(units) == 1
    assert units[0].metadata["text_box_id"] == "anchor-id:5D42324C"
