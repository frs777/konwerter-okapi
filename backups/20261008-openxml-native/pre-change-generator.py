from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from filter_ir.model.filter import FilterIR
from importer.validation.report import AdapterReport


_NATIVE_IMPLEMENTATIONS = {
    "MarkdownFilter": "filters.markdown.filter:MarkdownFilter",
    "JSONFilter": "filters.json.filter:JsonFilter",
    "YamlFilter": "filters.yaml.filter:YamlFilter",
    "XLIFFFilter": "filters.xliff.filter:XLIFFFilter",
    "XLIFF2Filter": "filters.xliff2.filter:XLIFF2Filter",
    "HtmlFilter": "filters.html:HtmlFilter",
    "EpubFilter": "filters.epub.filter:EpubFilter",
}

_NATIVE_SUPPORTED_FEATURES = {
    "MarkdownFilter": {"protected", "tables", "inline_code", "text"},
    "JSONFilter": {"subfilter", "text"},
    "YamlFilter": {"text"},
    "XLIFFFilter": {"text", "xml_stream"},
    "XLIFF2Filter": {"text"},
    "HtmlFilter": {"text", "inline_code"},
    "EpubFilter": {"text", "subfilter"},
}


class PythonFilterGenerator:
    def generate(
        self,
        ir: FilterIR,
        destination: str | Path,
        *,
        adapter_report: AdapterReport | None = None,
    ) -> Path:
        out = Path(destination) / ir.name
        out.mkdir(parents=True, exist_ok=True)
        class_name = ir.entry_class or (''.join(part.capitalize() for part in ir.name.replace('-', '_').split('_')) + 'Filter')
        (out / '__init__.py').write_text(
            f'from .filter import {class_name}\n'
            f'from .parameters import {class_name.removesuffix("Filter")}Parameters\n\n'
            f'__all__ = ["{class_name}", "{class_name.removesuffix("Filter")}Parameters"]\n',
            encoding='utf-8',
        )
        parameter_class = class_name.removesuffix("Filter") + "Parameters"
        parameter_lines = ["from __future__ import annotations", "", "from dataclasses import dataclass", "", "", "@dataclass(frozen=True, slots=True)", f"class {parameter_class}:"]
        if ir.parameter_rules:
            type_map = {"boolean": "bool", "string": "str", "integer": "int", "pattern": "str"}
            for rule in ir.parameter_rules:
                field_name = _camel_to_snake(rule.name)
                annotation = type_map[rule.value_type]
                default = repr(rule.default)
                parameter_lines.append(f"    {field_name}: {annotation} = {default}")
        else:
            parameter_lines.append("    pass")
        (out / 'parameters.py').write_text("\n".join(parameter_lines) + "\n", encoding='utf-8')

        native_implementation = _NATIVE_IMPLEMENTATIONS.get(ir.entry_class or "")
        supported_token_rules = {
            "STRONG_EMPHASIS": ("**", "bold"),
            "EMPHASIS": ("*", "italic"),
            "CODE": (chr(96), "inline_code"),
        }
        unsupported_token_rules = [
            f"{rule.token_type}:{rule.tag_strategy}"
            for rule in ir.token_rules
            if not (rule.tag_strategy == "paired" and rule.token_type in supported_token_rules)
        ]
        supported_token_rule_count = len(ir.token_rules) - len(unsupported_token_rules)
        token_rule_total = len(ir.token_rules)
        token_rule_ratio = (
            supported_token_rule_count / token_rule_total
            if token_rule_total
            else 0.0
        )
        supported_features = _NATIVE_SUPPORTED_FEATURES.get(
            ir.entry_class or "",
            {"protected", "tables", "inline_code", "text"},
        )
        unsupported_features = sorted(
            feature for feature in ir.features
            if feature not in supported_features
        )
        rule_generation_possible = bool(ir.token_rules) and not unsupported_token_rules
        if native_implementation:
            module_name, native_class = native_implementation.split(":", 1)
            filter_source = [
                'from __future__ import annotations',
                '',
                f'from {module_name} import {native_class} as _NativeFilter',
                '',
                f'class {class_name}(_NativeFilter):',
                f'    """Generated native-behavior adapter for {ir.name} {ir.version}."""',
                f'    name = {ir.name!r}',
                f'    version = {ir.version!r}',
                f'    mime_types = {tuple(ir.mime_types)!r}',
                f'    extensions = {tuple(ir.extensions)!r}',
                f'    features = {tuple(ir.features)!r}',
                f'    framework_contract = {ir.framework_contract!r}',
                '',
                '    def __init__(self, *args, **kwargs) -> None:',
                '        super().__init__(*args, **kwargs)',
                '        self._events = ()',
                '        self._event_index = 0',
                '',
                '    def open(self, source: str) -> None:',
                '        self._events = self.read(source)',
                '        self._event_index = 0',
                '',
                '    def has_next(self) -> bool:',
                '        return self._event_index < len(self._events)',
                '',
                '    def next(self):',
                '        if not self.has_next():',
                '            raise StopIteration',
                '        event = self._events[self._event_index]',
                '        self._event_index += 1',
                '        return event',
                '',
                '    def close(self) -> None:',
                '        self._events = ()',
                '        self._event_index = 0',
                '',
                '    def round_trip(self, source: str) -> str:',
                '        return self.write(tuple(self.read(source)))',
                '',
            ]
            behavior_source = 'native-python'
        elif rule_generation_possible:
            rule_literals = {
                'STRONG_EMPHASIS': ('**', 'bold'),
                'EMPHASIS': ('*', 'italic'),
                'CODE': (chr(96), 'inline_code'),
            }
            rules = [
                rule_literals[rule.token_type]
                for rule in ir.token_rules
                if rule.tag_strategy == 'paired' and rule.token_type in rule_literals
            ]
            filter_source = [
                'from __future__ import annotations',
                '',
                'import re',
                'from core.document.model import Code, TextFragment, TextUnit',
                'from core.events.model import Event, EventType',
                '',
                f'_TOKEN_RULES = {tuple(rules)!r}',
                '',
                f'class {class_name}:',
                f'    """Generated rule-based implementation for {ir.name} {ir.version}."""',
                f'    name = {ir.name!r}',
                f'    version = {ir.version!r}',
                f'    mime_types = {tuple(ir.mime_types)!r}',
                f'    extensions = {tuple(ir.extensions)!r}',
                f'    features = {tuple(ir.features)!r}',
                f'    framework_contract = {ir.framework_contract!r}',
                '',
                '    def read(self, source: str):',
                '        events = [Event(EventType.START_DOCUMENT, source)]',
                '        parts = []',
                '        position = 0',
                '        alternatives = [re.escape(marker) for marker, _ in _TOKEN_RULES]',
                '        pattern = re.compile("(" + "|".join(alternatives) + ")") if alternatives else None',
                '        for match in pattern.finditer(source) if pattern else () :',
                '            if match.start() > position:',
                '                parts.append(source[position:match.start()])',
                '            marker = match.group(0)',
                '            rule = next((item for item in _TOKEN_RULES if item[0] == marker), None)',
                '            if rule is None:',
                '                parts.append(marker)',
                '            else:',
                '                close = source.find(marker, match.end())',
                '                if close >= 0:',
                '                    parts.append(Code(marker, rule[1]))',
                '                    parts.append(source[match.end():close])',
                '                    parts.append(Code(marker, rule[1]))',
                '                    position = close + len(marker)',
                '                    continue',
                '                parts.append(marker)',
                '            position = match.end()',
                '        if position < len(source):',
                '            parts.append(source[position:])',
                '        events.append(Event(EventType.TEXT_UNIT, TextUnit("generated-1", (TextFragment(tuple(parts or [source])),))))',
                '        events.append(Event(EventType.END_DOCUMENT, None))',
                '        return tuple(events)',
                '',
                '    def write(self, events) -> str:',
                '        output = []',
                '        for event in events:',
                '            if event.type is EventType.TEXT_UNIT:',
                '                for fragment in event.resource.fragments:',
                '                    for part in fragment.parts:',
                '                        output.append(part.data if isinstance(part, Code) else part)',
                '        return "".join(output)',
                '',
                '    def round_trip(self, source: str) -> str:',
                '        return self.write(self.read(source))',
                '',
            ]
            behavior_source = 'rule-generated'
        else:
            filter_source = [
                'from __future__ import annotations',
                '',
                f'class {class_name}:',
                f'    """Generated executable adapter for {ir.name} {ir.version}."""',
                f'    name = {ir.name!r}',
                f'    version = {ir.version!r}',
                f'    mime_types = {tuple(ir.mime_types)!r}',
                f'    extensions = {tuple(ir.extensions)!r}',
                f'    features = {tuple(ir.features)!r}',
                f'    framework_contract = {ir.framework_contract!r}',
                '',
                '    def __init__(self) -> None:',
                '        self._source: str | None = None',
                '        self._closed = True',
                '        self._emitted = False',
                '',
                '    def open(self, source: str) -> None:',
                '        self._source = source',
                '        self._closed = False',
                '        self._emitted = False',
                '',
                '    def has_next(self) -> bool:',
                '        return not self._closed and self._source is not None and not self._emitted',
                '',
                '    def next(self) -> str:',
                '        if not self.has_next():',
                '            raise StopIteration',
                '        self._emitted = True',
                '        return self._source or ""',
                '',
                '    def close(self) -> None:',
                '        self._closed = True',
                '',
                '    def round_trip(self, source: str) -> str:',
                '        self.open(source)',
                '        try:',
                '            return self.next() if self.has_next() else source',
                '        finally:',
                '            self.close()',
                '',
            ]
            behavior_source = 'contract-adapter'
        (out / 'filter.py').write_text("\n".join(filter_source), encoding='utf-8')


        (out / 'filter_ir.json').write_text(
            json.dumps(asdict(ir), ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        report = adapter_report or AdapterReport.from_ir(ir)
        (out / 'conversion_report.json').write_text(
            json.dumps({
                'filter': ir.name,
                'entry_class': ir.entry_class,
                'adapter_features': list(report.required_features),
                'behavior_source': behavior_source,
                'unsupported_token_rules': unsupported_token_rules,
                'used_parameters': list(ir.used_parameters),
                'token_rule_coverage': {
                    'supported': supported_token_rule_count,
                    'total': token_rule_total,
                    'ratio': token_rule_ratio,
                },
                'unsupported_features': unsupported_features,
                'status': 'generated',
            }, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8',
        )
        return out


def _camel_to_snake(value: str) -> str:
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", value).lower()
