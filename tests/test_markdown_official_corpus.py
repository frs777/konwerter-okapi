from pathlib import Path
from filters.markdown.filter import MarkdownFilter
ROOT=Path("/home/frs/Projekty/Okapi-main/okapi/filters/markdown/src/test/resources/net/sf/okapi/filters/markdown")

def test_official_markdown_corpus_round_trips():
    files=list(ROOT.glob("*.md")); assert len(files)>=50
    f=MarkdownFilter()
    assert all(f.round_trip(p.read_text(encoding="utf-8"))==p.read_text(encoding="utf-8") for p in files)
