from pathlib import Path
from filters.docx.reader import DocxReader
from filters.docx.writer import DocxWriter
from core.events.model import EventType

CORPUS = sorted(Path("fixtures/docx").rglob("*.docx"))


def _text(events):
    out = []
    for event in events:
        if event.type != EventType.TEXT_UNIT:
            continue
        for fragment in event.resource.fragments:
            for part in fragment.parts:
                if isinstance(part, str):
                    out.append(part)
                elif getattr(part, "kind", None) in {"protected", "hyperlink", "field_instruction"}:
                    out.append(getattr(part, "data", ""))
    return "".join(out)


def test_docx_writer_can_translate_in_place_without_truncating_source_package(tmp_path):
    from dataclasses import replace
    from zipfile import ZipFile

    from core.document.model import TextFragment
    from core.events.model import Event, EventType
    from filters.docx.reader import DocxReader
    from filters.docx.writer import DocxWriter

    source = tmp_path / "in-place.docx"
    source.write_bytes(Path("fixtures/docx/reference.docx").read_bytes())
    events = tuple(DocxReader().read(source))
    changed_events = []
    changed = False
    expected_text = None
    for event in events:
        if event.type == EventType.TEXT_UNIT and not changed and (event.resource.metadata or {}).get("part", "body") == "body":
            unit = event.resource
            fragments = list(unit.fragments)
            for fragment_index, fragment in enumerate(fragments):
                parts = list(fragment.parts)
                for part_index, part in enumerate(parts):
                    if isinstance(part, str) and part:
                        parts[part_index] = part + " — translated"
                        expected_text = parts[part_index]
                        fragments[fragment_index] = replace(fragment, parts=tuple(parts))
                        translated = replace(unit, fragments=tuple(fragments))
                        changed_events.append(Event(event.type, translated, event.skeleton))
                        changed = True
                        break
                if changed:
                    break
            if changed:
                continue
        changed_events.append(event)

    assert changed and expected_text
    DocxWriter().write(tuple(changed_events), source)

    with ZipFile(source) as package:
        assert "word/document.xml" in package.namelist()
    after = tuple(DocxReader().read(source))
    assert expected_text in _text(after)


def test_all_docx_fixtures_preserve_text_and_field_structure(tmp_path):
    assert len(CORPUS) >= 7
    for source in CORPUS:
        reader = DocxReader()
        before = list(reader.read(source))
        target = tmp_path / source.name
        DocxWriter().write(before, target)
        after_reader = DocxReader()
        after = list(after_reader.read(target))
        assert _text(after) == _text(before), source.name
        assert [f.instruction.strip() for f in after_reader.complex_fields] == [
            f.instruction.strip() for f in reader.complex_fields
        ], source.name
