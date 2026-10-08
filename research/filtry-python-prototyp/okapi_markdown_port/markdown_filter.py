"""Eksperymentalny, bez-Java port semantycznego wycinka Okapi Markdown Filter."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterator


INLINE_RE = re.compile(r"(`[^`\n]+`|!?\[[^\]\n]*\]\([^\)\n]+\)|<[^>\n]+>)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


@dataclass(frozen=True, slots=True)
class InlineCode:
    """Chroniony fragment Markdown, który nie jest jednostką tłumaczenia."""

    index: int
    text: str
    kind: str


@dataclass(frozen=True, slots=True)
class TextUnit:
    """Jednostka tekstowa wraz z informacją pozwalającą odtworzyć dokument."""

    id: str
    line: int
    source: str
    codes: tuple[InlineCode, ...]


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Wynik parsowania: oryginalny skeleton i jednostki tekstowe."""

    lines: tuple[str, ...]
    units: tuple[TextUnit, ...]

    def render(self, targets: dict[str, str]) -> str:
        """Odtwórz dokument po podstawieniu targetów jednostek."""
        expected = {unit.id for unit in self.units}
        if set(targets) != expected:
            raise ValueError("Niepełny albo nadmiarowy zestaw targetów.")
        lines = list(self.lines)
        for unit in self.units:
            lines[unit.line] = targets[unit.id] + ("\n" if lines[unit.line].endswith("\n") else "")
        return "".join(lines)


class MarkdownFilter:
    """Mały filtr badawczy inspirowany kontraktem Okapi.

    Domyślne parametry są zgodne z ustalonym eksperymentalnie kontraktem
    Okapi Markdown Filter. To nadal nie jest pełny parser CommonMark ani
    zgodny zamiennik Okapi 1.49.x.
    """

    def __init__(
        self,
        *,
        translate_fenced_code_blocks: bool = True,
        translate_indented_code_blocks: bool = True,
        translate_inline_code_blocks: bool = True,
        translate_image_alt_text: bool = True,
        translate_urls: bool = False,
        translate_header_metadata: bool = False,
        generate_header_anchors: bool = False,
        parse_mdx: bool = False,
        use_code_finder: bool = False,
    ) -> None:
        self.translate_fenced_code_blocks = translate_fenced_code_blocks
        self.translate_indented_code_blocks = translate_indented_code_blocks
        self.translate_inline_code_blocks = translate_inline_code_blocks
        self.translate_image_alt_text = translate_image_alt_text
        self.translate_urls = translate_urls
        self.translate_header_metadata = translate_header_metadata
        self.generate_header_anchors = generate_header_anchors
        self.parse_mdx = parse_mdx
        self.use_code_finder = use_code_finder

    def parse(self, text: str) -> ParsedDocument:
        """Rozbij dokument na skeleton i jednostki tłumaczeniowe."""
        lines = tuple(text.splitlines(keepends=True))
        units: list[TextUnit] = []
        fenced = False
        fence_char = ""

        for line_no, line in enumerate(lines):
            stripped = line.lstrip()
            fence = FENCE_RE.match(line)
            if fence:
                marker = fence.group(1)[0]
                if not fenced:
                    fenced, fence_char = True, marker
                else:
                    fenced = False
                if self.translate_fenced_code_blocks:
                    units.append(self._make_unit(line_no, line.rstrip("\r\n"), ()))
                continue

            if fenced:
                if self.translate_fenced_code_blocks:
                    units.append(self._make_unit(line_no, line.rstrip("\r\n"), ()))
                continue

            if not line.strip():
                continue

            if self._is_indented_code(line):
                if self.translate_indented_code_blocks:
                    units.append(self._make_unit(line_no, line.rstrip("\r\n"), ()))
                continue

            source = line.rstrip("\r\n")
            parts = list(INLINE_RE.finditer(source))
            codes = tuple(
                InlineCode(i, match.group(0), self._kind(match.group(0)))
                for i, match in enumerate(parts)
                if self.translate_inline_code_blocks or self._kind(match.group(0)) != "inline-code"
            )
            units.append(self._make_unit(line_no, source, codes))

        return ParsedDocument(lines, tuple(units))

    @staticmethod
    def _make_unit(line_no: int, source: str, codes: tuple[InlineCode, ...]) -> TextUnit:
        return TextUnit(f"md-{line_no + 1}", line_no, source, codes)

    @staticmethod
    def _is_indented_code(line: str) -> bool:
        return line.startswith("    ") or line.startswith("\t")

    @staticmethod
    def _kind(value: str) -> str:
        if value.startswith("`"):
            return "inline-code"
        if value.startswith("!["):
            return "image"
        if value.startswith("["):
            return "link"
        return "html"


__all__ = ["InlineCode", "MarkdownFilter", "ParsedDocument", "TextUnit"]
