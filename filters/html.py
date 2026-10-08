from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from core.document.model import Markup, TextFragment, TextUnit
from core.events.model import Event, EventType, StartDocument

_BLOCKS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td", "th", "title", "dt", "dd", "caption"}
_IGNORED = {"script", "style", "noscript", "template"}


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.units = []
        self.parts = []
        self.stack = []
        self.ranges = []
        self.unit_id = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _IGNORED:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in _BLOCKS and self.parts:
            self._flush()
        if tag in _BLOCKS:
            self.stack.append((tag, self._offset(), None))
            return
        if tag in {"b", "strong", "i", "em", "u", "code"}:
            self.parts.append(Markup.start(tag, tuple(attrs)))
        self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if self.skip:
            return
        self.parts.append(Markup.empty(tag.lower(), tuple(attrs)))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _IGNORED:
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag in {"b", "strong", "i", "em", "u", "code"}:
            self.parts.append(Markup.end(tag))
        if tag in _BLOCKS:
            for i in range(len(self.stack) - 1, -1, -1):
                item = self.stack[i]
                if isinstance(item, tuple) and item[0] == tag:
                    self.ranges.append((len(self.units) + 1, item[1], self._offset_before_end()))
                    del self.stack[i]
                    break
        elif self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in _BLOCKS:
            self._flush()

    def _offset(self):
        line, col = self.getpos()
        lines = self.raw_source.splitlines(keepends=True)
        return sum(len(x) for x in lines[:line - 1]) + col

    def _offset_before_end(self):
        line, col = self.getpos()
        return sum(len(x) for x in self.raw_source.splitlines(keepends=True)[:line - 1]) + col

    def handle_data(self, data):
        if not self.skip and data:
            self.parts.append(data)

    def handle_entityref(self, name):
        if not self.skip:
            self.parts.append(f"&{name};")

    def handle_charref(self, name):
        if not self.skip:
            self.parts.append(f"&#{name};")

    def _flush(self):
        if not any(isinstance(p, str) and p.strip() for p in self.parts):
            self.parts.clear()
            return
        self.unit_id += 1
        self.units.append(TextUnit(str(self.unit_id), (TextFragment(tuple(self.parts)),), {"html_element": self.stack[-1] if self.stack else ""}))
        self.parts.clear()


class HtmlFilter:
    name = "html"
    version = "1.0"
    mime_types = ("text/html", "application/xhtml+xml")
    extensions = (".html", ".htm", ".xhtml")
    features = ("text", "inline_code")
    framework_contract = "net.sf.okapi.common.filters.IFilter"

    def __init__(self):
        self._source = None

    def read(self, source):
        if isinstance(source, Path) or (isinstance(source, str) and "<" not in source[:100]):
            path = Path(source); self._source = path.read_text(encoding="utf-8"); name = path.name
        else:
            self._source = str(source); name = "memory.html"
        parser = _Parser(); parser.raw_source = self._source; parser.feed(self._source); parser.close()
        yield Event(EventType.START_DOCUMENT, StartDocument(name, name))
        yield from (Event(EventType.TEXT_UNIT, u) for u in parser.units)
        yield Event(EventType.END_DOCUMENT, None)

    def write(self, events, target=None):
        if self._source is None:
            raise RuntimeError("read() must be called before write()")
        output = self._source
        parser = _Parser(); parser.raw_source = self._source; parser.feed(self._source); parser.close()
        changed = []
        units = [event.resource for event in events if event.type is EventType.TEXT_UNIT]
        for unit in units:
            text = self._serialize(tuple(part for fragment in unit.fragments for part in fragment.parts))
            changed.append((unit.id, text))
        for unit_id, text in reversed(changed):
            match = next((r for r in parser.ranges if str(r[0]) == str(unit_id)), None)
            if match is None:
                continue
            _, start, end = match
            open_end = self._find_open_end(output, start)
            output = output[:open_end] + text + output[end:]
        if target is not None:
            Path(target).write_text(output, encoding="utf-8")
        return output

    @staticmethod
    def _find_open_end(source, start):
        end = source.find(">", start)
        return end + 1 if end >= 0 else start

    @staticmethod
    def _serialize(parts):
        out = []
        for part in parts:
            if isinstance(part, str): out.append(part)
            elif isinstance(part, Markup):
                attrs = "".join(f' {k}="{v}"' for k, v in part.attributes)
                out.append(f"<{part.name}{attrs}>" if part.kind == "start" else f"</{part.name}>" if part.kind == "end" else f"<{part.name}{attrs}/>")
            else: out.append(getattr(part, "data", ""))
        return "".join(out)

    def round_trip(self, source):
        return self.write(tuple(self.read(source)))
