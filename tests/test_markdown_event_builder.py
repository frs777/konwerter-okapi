from core.events.model import EventType
from core.text_fragment.inline_code_finder import InlineCodeFinder
from filters.markdown.event_builder import MarkdownEventBuilder

def test_markdown_event_builder_applies_code_finder_after_text_unit():
    b=MarkdownEventBuilder(code_finder=InlineCodeFinder.markdown_default()); b.start_document("x"); b.start_text_unit("A {{name}}"); b.end_text_unit(); b.end_document(); events=list(b)
    unit=events[1].resource
    assert [type(p).__name__ for p in unit.fragments[0].parts] == ["str","Code"]
    assert events[1].type is EventType.TEXT_UNIT
