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
