from __future__ import annotations

from collections.abc import Iterable
from xml.etree import ElementTree as ET

from core.document.model import Markup, MarkupComponent, Skeleton


_NS_PREFIXES_INV = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

_NS_PREFIXES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main": "w",
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships": "r",
    "http://www.w3.org/XML/1998/namespace": "xml",
}


class MarkupComponentParser:
    """Maps XML structural elements to the filter IR markup/skeleton model."""

    def name(self, element: ET.Element) -> str:
        if element.tag.startswith("{"):
            uri, local = element.tag[1:].split("}", 1)
            prefix = _NS_PREFIXES.get(uri)
            return f"{prefix}:{local}" if prefix else local
        return element.tag

    def attributes(self, element: ET.Element) -> tuple[tuple[str, str], ...]:
        pairs = []
        for key, value in element.attrib.items():
            if key.startswith("{"):
                uri, local = key[1:].split("}", 1)
                prefix = _NS_PREFIXES.get(uri)
                key = f"{prefix}:{local}" if prefix else local
            pairs.append((key, value))
        return tuple(sorted(pairs))

    def start(self, element: ET.Element) -> Markup:
        return Markup.start(self.name(element), self.attributes(element))

    def end(self, element: ET.Element) -> Markup:
        return Markup.end(self.name(element))

    def empty(self, element: ET.Element) -> Markup:
        return Markup.empty(self.name(element), self.attributes(element))

    def _specialization(self, element: ET.Element) -> tuple[str, bool]:
        local = self.name(element).split(":", 1)[-1]
        if local in {"rPr", "defRPr", "endParaRPr"}:
            return "run_properties", False
        if local in {"pPr", "tblPr", "tcPr", "trPr", "sectPr"}:
            styled = element.find(f"{{{_NS_PREFIXES_INV['w']}}}pStyle") is not None
            return "block_properties", styled
        if local in {"oMath", "oMathPara"}:
            return "formula", False
        return "generic", False

    def components(self, root: ET.Element) -> tuple[MarkupComponent, ...]:
        components: list[MarkupComponent] = []
        stack: list[MarkupComponent] = []
        counter = 0

        def visit(element: ET.Element) -> None:
            nonlocal counter
            counter += 1
            component_id = f"mc-{counter}"
            parent_id = stack[-1].component_id if stack else None
            role, styled = self._specialization(element)
            start = MarkupComponent.from_markup(self.start(element), component_id, parent_id, role=role, styled=styled)
            components.append(start)
            stack.append(start)
            for child in element:
                visit(child)
            counter += 1
            end_id = f"mc-{counter}"
            end = MarkupComponent.from_markup(self.end(element), end_id, parent_id, matches=start.component_id, role=start.role, styled=start.styled)
            components.append(end)
            stack.pop()

        visit(root)
        MarkupComponent.validate_sequence(components)
        return tuple(components)

    def skeleton(self, root: ET.Element) -> Skeleton:
        parts: list[Markup] = []

        def visit(element: ET.Element) -> None:
            parts.append(self.start(element))
            for child in element:
                visit(child)
            parts.append(self.end(element))

        visit(root)
        return Skeleton(tuple(parts))
