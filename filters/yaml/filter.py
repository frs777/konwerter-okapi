from __future__ import annotations

from dataclasses import dataclass
import json

import yaml

from core.document.model import TextFragment, TextUnit
from core.events.model import Event, EventType


@dataclass(frozen=True, slots=True)
class _ScalarSpan:
    start: int
    end: int
    style: str | None
    path: str


class YamlFilter:
    """Java-free YAML filter using a structural parser plus lossless source spans.

    YAML parsing determines which scalar nodes are translatable. The original
    document remains the skeleton; writing replaces only changed scalar spans.
    """

    def read(self, source: str):
        events = [Event(EventType.START_DOCUMENT, source)]
        spans: list[_ScalarSpan] = []

        for document_index, root in enumerate(yaml.compose_all(source)):
            self._collect_value_scalars(root, "", spans)

        for index, span in enumerate(spans, start=1):
            original = source[span.start:span.end]
            value = self._decode_scalar(original, span.style)
            unit = TextUnit(
                id=f"yaml-{index}",
                fragments=(TextFragment((value,)),),
                metadata={
                    "yaml_path": span.path,
                    "source_start": str(span.start),
                    "source_end": str(span.end),
                    "scalar_style": span.style or "plain",
                    "original": original,
                },
            )
            events.append(Event(EventType.TEXT_UNIT, unit))

        events.append(Event(EventType.END_DOCUMENT, None))
        return tuple(events)

    def write(self, events) -> str:
        source = next(
            (event.resource for event in events if event.type is EventType.START_DOCUMENT),
            None,
        )
        if not isinstance(source, str):
            raise ValueError("YAML write requires START_DOCUMENT with source text")

        replacements: list[tuple[int, int, str]] = []
        for event in events:
            if event.type is not EventType.TEXT_UNIT:
                continue
            unit = event.resource
            metadata = unit.metadata or {}
            if "source_start" not in metadata or "source_end" not in metadata:
                continue
            value = "".join(
                part if isinstance(part, str) else getattr(part, "data", str(part))
                for fragment in unit.fragments
                for part in fragment.parts
            )
            original = metadata.get("original", "")
            if value == self._decode_scalar(original, metadata.get("scalar_style")):
                continue
            start = int(metadata["source_start"])
            end = int(metadata["source_end"])
            replacements.append(
                (start, end, self._encode_scalar(value, metadata.get("scalar_style"), original))
            )

        result = source
        for start, end, replacement in sorted(replacements, reverse=True):
            result = result[:start] + replacement + result[end:]
        return result

    def round_trip(self, source: str) -> str:
        return self.write(self.read(source))

    def _collect_value_scalars(self, node, path: str, spans: list[_ScalarSpan]) -> None:
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                key_name = str(key.value)
                child_path = f"{path}/{key_name}" if path else key_name
                self._collect_value_scalars(value, child_path, spans)
            return

        if isinstance(node, yaml.SequenceNode):
            for index, value in enumerate(node.value):
                child_path = f"{path}/{index}" if path else str(index)
                self._collect_value_scalars(value, child_path, spans)
            return

        if isinstance(node, yaml.ScalarNode):
            if node.tag == "tag:yaml.org,2002:null":
                return
            spans.append(
                _ScalarSpan(
                    node.start_mark.index,
                    node.end_mark.index,
                    node.style,
                    path,
                )
            )

    @staticmethod
    def _decode_scalar(raw: str, style: str | None) -> str:
        if style == "'":
            return raw[1:-1].replace("''", "'")
        if style == '"':
            return json.loads(raw)
        if style in {"|", ">"}:
            lines = raw.splitlines()
            if not lines:
                return ""
            content = lines[1:]
            if style == "|":
                value = "\n".join(line.lstrip() for line in content)
            else:
                value = " ".join(line.strip() for line in content)
            return value + ("\n" if raw.endswith("\n") else "")
        return raw

    @staticmethod
    def _encode_scalar(value: str, style: str | None, original: str) -> str:
        if style == "'":
            return "'" + value.replace("'", "''") + "'"
        if style == '"':
            return json.dumps(value, ensure_ascii=False)
        if style in {"|", ">"}:
            header, _, content = original.partition("\n")
            indent = "  "
            for line in content.splitlines():
                if line.strip():
                    indent = line[: len(line) - len(line.lstrip())] or indent
                    break
            encoded = header + "\n" + "\n".join(indent + line for line in value.rstrip("\n").splitlines())
            return encoded + ("\n" if value.endswith("\n") else "")
        return value
