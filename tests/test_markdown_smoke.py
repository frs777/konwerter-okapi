from pathlib import Path


def test_markdown_smoke_round_trip_preserves_text():
    from filters.markdown.filter import MarkdownFilter
    result = MarkdownFilter().round_trip('# Nagłówek\n\nZażółć gęślą jaźń — 😀')
    assert result == '# Nagłówek\n\nZażółć gęślą jaźń — 😀'

def test_markdown_filter_emits_inline_link_code_and_document_structure():
    from core.document.model import Code
    from core.events.model import EventType
    from filters.markdown.filter import MarkdownFilter

    source = "# Tytuł\n\nTekst **ważny** i [link](https://example.com) oraz " + "`kod`.\n"
    events = tuple(MarkdownFilter().read(source))
    text_units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]
    codes = [part for unit in text_units for fragment in unit.fragments for part in fragment.parts if isinstance(part, Code)]
    kinds = {code.kind for code in codes}
    assert "bold" in kinds
    assert "link" in kinds
    assert "inline_code" in kinds
    assert any(code.target == "https://example.com" for code in codes)
    assert any(event.type is EventType.DOCUMENT_PART for event in events)


def test_markdown_filter_protects_fenced_code_and_yaml_front_matter():
    from core.document.model import Code
    from core.events.model import EventType
    from filters.markdown.filter import MarkdownFilter

    source = "---\ntitle: Test\n---\n\nTekst\n\n```python\nprint('x')\n```\n"
    events = tuple(MarkdownFilter().read(source))
    protected = [
        part
        for event in events
        if event.type is EventType.TEXT_UNIT
        for fragment in event.resource.fragments
        for part in fragment.parts
        if isinstance(part, Code) and part.kind == "protected"
    ]
    assert any("print('x')" in code.data for code in protected)
    assert any(event.type is EventType.DOCUMENT_PART and "title: Test" in event.resource.content for event in events)



def test_markdown_filter_round_trips_official_okapi_corpus():
    from filters.markdown.filter import MarkdownFilter

    root = Path('/home/frs/Projekty/Okapi-main/okapi/filters/markdown/src/test/resources/net/sf/okapi/filters/markdown')
    filter_ = MarkdownFilter()
    documents = sorted(root.rglob('*.md'))
    assert len(documents) >= 20
    for document in documents:
        source = document.read_text(encoding='utf-8')
        assert filter_.round_trip(source) == source, document
