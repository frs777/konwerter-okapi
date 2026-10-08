from okapi_markdown_port.markdown_filter import MarkdownFilter


def test_okapi_defaults_extract_code_blocks_as_translatable_units() -> None:
    doc = "Tekst.\n\n```python\nprint('x')\n```\n\n    kod()\n"
    parsed = MarkdownFilter().parse(doc)
    assert [u.source for u in parsed.units] == [
        "Tekst.",
        "```python",
        "print('x')",
        "```",
        "    kod()",
    ]


def test_non_translatable_code_configuration_moves_blocks_to_skeleton() -> None:
    doc = "Tekst.\n\n```python\nprint('x')\n```\n"
    parsed = MarkdownFilter(translate_fenced_code_blocks=False).parse(doc)
    assert [u.source for u in parsed.units] == ["Tekst."]


def test_indented_code_configuration_is_explicit() -> None:
    doc = "Tekst.\n\n    kod()\n"
    parsed = MarkdownFilter(translate_indented_code_blocks=False).parse(doc)
    assert [u.source for u in parsed.units] == ["Tekst."]


def test_inline_configuration_is_explicit() -> None:
    doc = "A `kod` i [link](https://example.org) ![alt](x.png) <b>x</b>\n"
    parsed = MarkdownFilter(translate_inline_code_blocks=False).parse(doc)
    assert [c.kind for c in parsed.units[0].codes] == ["link", "image", "html", "html"]


def test_round_trip_preserves_document_when_targets_are_unchanged() -> None:
    doc = "# T\n\nA `kod`.\n\n```python\nprint('kod')\n```\n"
    parsed = MarkdownFilter().parse(doc)
    targets = {u.id: u.source for u in parsed.units}
    assert parsed.render(targets) == doc
