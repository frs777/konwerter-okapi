from pathlib import Path
import importlib
import importlib.util


def _reader_class():
    spec = importlib.util.find_spec("filters.docx.reader")
    assert spec is not None, "Brakuje modułu filters.docx.reader"
    return importlib.import_module("filters.docx.reader").DocxReader


def test_docx_reader_extracts_text_units_and_inline_structure():
    DocxReader = _reader_class()
    fixture = Path("fixtures/docx/reference.docx")
    events = list(DocxReader().read(fixture))

    assert events
    assert events[0].type.value == "START_DOCUMENT"

    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    assert text_units
    assert any("Akapit" in part for unit in text_units for fragment in unit.fragments for part in fragment.parts if isinstance(part, str))

    assert any(
        getattr(part, "kind", None) == "hyperlink"
        for unit in text_units
        for fragment in unit.fragments
        for part in fragment.parts
        if not isinstance(part, str)
    )


def test_docx_reader_preserves_table_text_as_distinct_units():
    DocxReader = _reader_class()
    fixture = Path("fixtures/docx/reference.docx")
    events = list(DocxReader().read(fixture))

    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    texts = [
        part
        for unit in text_units
        for fragment in unit.fragments
        for part in fragment.parts
        if isinstance(part, str)
    ]

    assert "Komórka A" in texts
    assert "Komórka B" in texts


def test_docx_reader_marks_non_translatable_content_as_protected():
    DocxReader = _reader_class()
    fixture = Path("fixtures/docx/reference.docx")
    events = list(DocxReader().read(fixture))

    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    kinds = {
        getattr(part, "kind", None)
        for unit in text_units
        for fragment in unit.fragments
        for part in fragment.parts
        if not isinstance(part, str)
    }

    assert "protected" in kinds


def test_docx_reader_emits_skeleton_for_document_structure():
    DocxReader = _reader_class()
    fixture = Path("fixtures/docx/reference.docx")
    events = list(DocxReader().read(fixture))

    skeletons = [event.resource for event in events if event.type.value == "DOCUMENT_PART"]
    assert skeletons
    skeleton = skeletons[0]
    assert any("paragraph" in part for part in skeleton.parts)
    assert any("table" in part for part in skeleton.parts)


def test_docx_reader_includes_headers_and_footers():
    DocxReader = _reader_class()
    fixture = Path("fixtures/docx/reference.docx")
    events = list(DocxReader().read(fixture))
    text_units = [event.resource for event in events if event.type.value == "TEXT_UNIT"]
    texts = [part for unit in text_units for fragment in unit.fragments for part in fragment.parts if isinstance(part, str)]
    assert "Nagłówek testowy" in texts
    assert "Stopka testowa" in texts
