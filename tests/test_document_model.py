from core.document.model import Code, Skeleton, TextFragment, TextUnit
from core.events.model import DocumentPart, Ending, Event, EventType, StartDocument


def test_text_fragment_preserves_structural_inline_code():
    fragment = TextFragment(parts=("A", Code("x", "TAG"), "B"))

    assert fragment.parts[0] == "A"
    assert fragment.parts[1] == Code("x", "TAG")
    assert fragment.parts[2] == "B"


def test_text_unit_contains_fragments_without_flattening_codes():
    unit = TextUnit(id="u1", fragments=(TextFragment(("hello ", Code("<b>", "TAG"), "world")),))

    assert unit.id == "u1"
    assert isinstance(unit.fragments[0].parts[1], Code)


def test_text_unit_can_preserve_distinct_target_fragments():
    source = (TextFragment(("Hello",)),)
    target = (TextFragment(("Cześć",)),)

    unit = TextUnit(id="u1", fragments=source, target_fragments=target)

    assert unit.fragments == source
    assert unit.target_fragments == target


def test_skeleton_is_structural():
    skeleton = Skeleton(parts=("<p>", "</p>"))

    assert skeleton.parts == ("<p>", "</p>")


def test_event_stream_uses_explicit_event_types():
    events = (
        Event(EventType.START_DOCUMENT, StartDocument("test.md")),
        Event(EventType.TEXT_UNIT, TextUnit("u1", (TextFragment(("tekst",)),))),
        Event(EventType.DOCUMENT_PART, DocumentPart("newline")),
        Event(EventType.END_DOCUMENT, Ending()),
    )

    assert [event.type for event in events] == [
        EventType.START_DOCUMENT,
        EventType.TEXT_UNIT,
        EventType.DOCUMENT_PART,
        EventType.END_DOCUMENT,
    ]


def test_text_fragment_can_record_style_provenance():
    fragment = TextFragment(("Styled",), {"bold": "true"}, {"run_style": "Emphasis", "source": "combined"})
    assert fragment.metadata == {"bold": "true"}
    assert fragment.style == {"run_style": "Emphasis", "source": "combined"}

def test_markup_components_preserve_nested_open_close_structure():
    from core.document.model import Markup
    start = Markup.start("w:hyperlink", (("r:id", "rId5"),))
    end = Markup.end("w:hyperlink")
    assert start.kind == "start"
    assert start.name == "w:hyperlink"
    assert start.attributes == (("r:id", "rId5"),)
    assert end.kind == "end"
    assert end.name == "w:hyperlink"


def test_markup_is_a_distinct_text_fragment_part():
    from core.document.model import Markup, TextFragment
    fragment = TextFragment(("hello", Markup.start("w:ins"), "world", Markup.end("w:ins")))
    assert fragment.parts[1].kind == "start"
    assert fragment.parts[3].kind == "end"


def test_skeleton_can_preserve_ordered_markup_components():
    from core.document.model import Markup, Skeleton
    skeleton = Skeleton((Markup.start("w:tbl"), Markup.start("w:tr"), Markup.end("w:tr"), Markup.end("w:tbl")))
    assert [part.name for part in skeleton.parts] == ["w:tbl", "w:tr", "w:tr", "w:tbl"]
