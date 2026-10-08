from __future__ import annotations

from dataclasses import dataclass, replace
import json

from core.document.model import Skeleton, TextFragment, TextUnit
from core.events.model import EndSubfilter, Event, EventType, StartSubfilter


@dataclass(frozen=True, slots=True)
class _ObjectContext:
    path: str
    parent: int | None
    key: str | None
    id_value: str | None = None
    notes: tuple[dict[str, str], ...] = ()
    generic_meta: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class _StringSpan:
    start: int
    end: int
    path: str
    name: str
    has_key: bool
    object_index: int | None


class JsonFilter:
    """Java-free JSON filter with source-preserving spans and core extraction semantics."""

    def __init__(self, parameters: dict | None = None):
        parameters = parameters or {}
        self.extract_all_pairs = parameters.get("extractAllPairs", True)
        self.extract_standalone = parameters.get("extractStandalone", False)
        self.use_key_as_name = parameters.get("useKeyAsName", True)
        self.use_full_key_path = parameters.get("useFullKeyPath", False)
        self.use_leading_slash_on_key_path = parameters.get("useLeadingSlashOnKeyPath", True)
        self.use_id_stack = parameters.get("useIdStack", False)
        self.id_rules = self._compile_rule(parameters.get("idRules"))
        self.note_rules = self._compile_rule(parameters.get("noteRules"))
        self.generic_meta_rules = self._compile_rule(parameters.get("genericMetaRules"))
        self.extraction_rules = self._compile_rule(parameters.get("extractionRules"))
        self.subfilter = parameters.get("subfilter")
        self.subfilter_rules = self._compile_rule(parameters.get("subfilterRules"))
        self._subfilter_index = 0

    def read(self, source: str):
        decoder = json.JSONDecoder()
        spans: list[_StringSpan] = []
        objects: list[_ObjectContext] = []
        position = self._parse_value(source, 0, "", spans, decoder, False, objects, None)
        position = self._skip_whitespace(source, position)
        if position != len(source):
            raise ValueError(f"unexpected JSON data at position {position}")

        events = [Event(EventType.START_DOCUMENT, source)]
        for index, span in enumerate(spans, start=1):
            obj = objects[span.object_index] if span.object_index is not None else None
            rule_key = span.path if self.use_full_key_path else span.name
            if self._is_rule_match(self.id_rules, rule_key) or self._is_rule_match(self.note_rules, rule_key) or self._is_rule_match(self.generic_meta_rules, rule_key):
                continue
            if span.has_key and self.extraction_rules is not None and not self._is_rule_match(self.extraction_rules, rule_key):
                continue
            if not self._should_extract(span):
                continue
            raw = source[span.start:span.end]
            value = json.loads(raw)
            owner = self._metadata_owner(objects, span.object_index)
            name = span.path if self.use_full_key_path else span.name
            if owner is not None and owner.id_value is not None:
                if self.use_id_stack:
                    ids = [item.id_value for item in self._object_chain(objects, owner) if item.id_value is not None]
                    name = "/".join(ids)
                else:
                    name = owner.id_value
            elif not self.use_key_as_name:
                name = None
            if name is not None and not self.use_leading_slash_on_key_path:
                name = name.lstrip("/")
            metadata = {
                "json_path": span.path,
                "name": name,
                "source_start": str(span.start),
                "source_end": str(span.end),
                "original": raw,
            }
            if owner is not None and owner.notes:
                metadata["notes"] = json.dumps(list(owner.notes), ensure_ascii=False)
            if owner is not None and owner.generic_meta:
                metadata["generic_meta"] = json.dumps(dict(owner.generic_meta), ensure_ascii=False)
            if self.subfilter is not None and (
                self.subfilter_rules is None or self._is_rule_match(self.subfilter_rules, rule_key)
            ):
                events.extend(self._read_subfilter(value, metadata))
                continue

            unit = TextUnit(
                id=f"json-{index}",
                fragments=(TextFragment((value,)),),
                metadata=metadata,
            )
            events.append(Event(EventType.TEXT_UNIT, unit))
        events.append(Event(EventType.END_DOCUMENT, None))
        return tuple(events)

    def _should_extract(self, span: _StringSpan) -> bool:
        return self.extract_all_pairs if span.has_key else self.extract_standalone

    def _read_subfilter(self, value: str, metadata: dict[str, str]) -> tuple[Event, ...]:
        subfilter = self.subfilter
        if hasattr(subfilter, "read"):
            instance = subfilter
        elif callable(subfilter):
            instance = subfilter()
        else:
            raise TypeError("subfilter must provide read(source) or be a callable factory")

        raw_events = tuple(instance.read(value))
        filter_name = getattr(instance, "name", instance.__class__.__name__)
        nested = tuple(
            event
            for event in raw_events
            if event.type not in {EventType.START_DOCUMENT, EventType.END_DOCUMENT}
        )
        self._subfilter_index += 1
        start_resource = StartSubfilter(f"subfilter-{self._subfilter_index}", filter_name, None, Skeleton(()))
        start = Event(EventType.START_SUBFILTER, start_resource)
        end = Event(EventType.END_SUBFILTER, EndSubfilter(f"{start_resource.id}-end"))
        return (start, *nested, end)

    def write(self, events) -> str:
        source = next(
            (event.resource for event in events if event.type is EventType.START_DOCUMENT),
            None,
        )
        if not isinstance(source, str):
            raise ValueError("JSON write requires START_DOCUMENT with source text")

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
            if value == json.loads(original):
                continue
            replacements.append(
                (int(metadata["source_start"]), int(metadata["source_end"]), json.dumps(value, ensure_ascii=False))
            )

        result = source
        for start, end, replacement in sorted(replacements, reverse=True):
            result = result[:start] + replacement + result[end:]
        return result

    def round_trip(self, source: str) -> str:
        return self.write(self.read(source))

    def _parse_value(self, source: str, position: int, path: str, spans: list[_StringSpan], decoder: json.JSONDecoder, has_key: bool, objects: list[_ObjectContext], object_index: int | None) -> int:
        position = self._skip_whitespace(source, position)
        if position >= len(source):
            raise ValueError("unexpected end of JSON")
        char = source[position]
        if char == '{':
            return self._parse_object(source, position, path, spans, decoder, objects, object_index)
        if char == '[':
            return self._parse_array(source, position, path, spans, decoder, objects, object_index)
        if char == '"':
            _, end = decoder.raw_decode(source, position)
            spans.append(_StringSpan(position, end, path, path.rsplit('/', 1)[-1] if path else "", has_key, object_index))
            return end
        _, end = decoder.raw_decode(source, position)
        return end

    def _parse_object(self, source: str, position: int, path: str, spans: list[_StringSpan], decoder: json.JSONDecoder, objects: list[_ObjectContext], parent_index: int | None) -> int:
        object_index = len(objects)
        objects.append(_ObjectContext(path, parent_index, path.rsplit("/", 1)[-1] if path else None))
        position = self._skip_whitespace(source, position + 1)
        if position < len(source) and source[position] == '}':
            return position + 1
        while True:
            if position >= len(source) or source[position] != '"':
                raise ValueError(f"expected JSON object key at position {position}")
            key, position = decoder.raw_decode(source, position)
            position = self._skip_whitespace(source, position)
            if position >= len(source) or source[position] != ':':
                raise ValueError(f"expected ':' after JSON key at position {position}")
            child_path = f"{path}/{key}" if path else f"/{key}"
            before = len(spans)
            position = self._parse_value(source, position + 1, child_path, spans, decoder, True, objects, object_index)
            self._record_object_rule(objects, object_index, child_path, key, source, before, spans, decoder)
            position = self._skip_whitespace(source, position)
            if position < len(source) and source[position] == '}':
                return position + 1
            if position >= len(source) or source[position] != ',':
                raise ValueError(f"expected ',' or '}}' at position {position}")
            position = self._skip_whitespace(source, position + 1)

    def _parse_array(self, source: str, position: int, path: str, spans: list[_StringSpan], decoder: json.JSONDecoder, objects: list[_ObjectContext], parent_index: int | None) -> int:
        position = self._skip_whitespace(source, position + 1)
        if position < len(source) and source[position] == ']':
            return position + 1
        index = 0
        while True:
            child_path = f"{path}/{index}" if path else f"/{index}"
            position = self._parse_value(source, position, child_path, spans, decoder, False, objects, parent_index)
            position = self._skip_whitespace(source, position)
            if position < len(source) and source[position] == ']':
                return position + 1
            if position >= len(source) or source[position] != ',':
                raise ValueError(f"expected ',' or ']' at position {position}")
            index += 1
            position = self._skip_whitespace(source, position + 1)



    @staticmethod
    def _compile_rule(value):
        if value is None or str(value).strip() == "":
            return None
        import re
        return re.compile(str(value).strip())

    @staticmethod
    def _is_rule_match(rule, path: str) -> bool:
        return rule is not None and rule.fullmatch(path) is not None

    @staticmethod
    def _object_chain(objects, owner):
        chain = []
        while owner is not None:
            chain.append(owner)
            owner = objects[owner.parent] if owner.parent is not None else None
        return tuple(reversed(chain))

    def _metadata_owner(self, objects, object_index):
        current = object_index
        while current is not None:
            obj = objects[current]
            if obj.id_value is not None or obj.notes or obj.generic_meta:
                return obj
            current = obj.parent
        return None

    def _record_object_rule(self, objects, object_index, path, key, source, before, spans, decoder):
        obj = objects[object_index]
        raw_value = None
        if before < len(spans):
            raw_value = json.loads(source[spans[before].start:spans[before].end])
        if raw_value is None:
            return
        rule_key = path if self.use_full_key_path else key
        if self._is_rule_match(self.id_rules, rule_key):
            objects[object_index] = _ObjectContext(obj.path, obj.parent, obj.key, str(raw_value), obj.notes, obj.generic_meta)
        elif self._is_rule_match(self.note_rules, rule_key):
            notes = obj.notes + ({"from": key, "text": str(raw_value)},)
            objects[object_index] = _ObjectContext(obj.path, obj.parent, obj.key, obj.id_value, notes, obj.generic_meta)
        elif self._is_rule_match(self.generic_meta_rules, rule_key):
            meta_key = path if self.use_full_key_path else key
            meta = obj.generic_meta + ((meta_key if not self.use_id_stack else key, str(raw_value)),)
            objects[object_index] = _ObjectContext(obj.path, obj.parent, obj.key, obj.id_value, obj.notes, meta)
    @staticmethod
    def _skip_whitespace(source: str, position: int) -> int:
        while position < len(source) and source[position] in " \t\r\n":
            position += 1
        return position
