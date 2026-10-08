import pytest
from core.document.model import Code, TextFragment
from core.text_fragment.inline_code_finder import InlineCodeFinder

def test_finder_converts_matching_text_to_inline_code():
    fragment=TextFragment(("A {{name}} B",))
    finder=InlineCodeFinder([r"\{\{[^}]+\}\}"])
    result=finder.process(fragment)
    assert result.parts[0]=="A " and isinstance(result.parts[1], Code) and result.parts[1].data=="{{name}}"
    assert result.parts[1].kind=="regxph" and result.parts[2]==" B"

def test_finder_does_not_change_existing_codes():
    code=Code("<b>","bold")
    result=InlineCodeFinder([r"\{\{[^}]+\}\}"]).process(TextFragment(("A ",code," {{x}}")))
    assert result.parts[1] is code and isinstance(result.parts[3], Code)

def test_finder_can_use_default_markdown_rule():
    result=InlineCodeFinder.markdown_default().process(TextFragment(("{{x}}",)))
    assert [p.data for p in result.parts if isinstance(p,Code)] == ["{{x}}"]
