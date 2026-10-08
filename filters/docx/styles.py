from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WP = f"{{{W}}}"


@dataclass(frozen=True, slots=True)
class StyleDefinition:
    style_id: str
    style_type: str
    based_on: str | None = None
    linked_style: str | None = None
    default: bool = False
    run_properties: dict[str, str] | None = None
    paragraph_properties: dict[str, str] | None = None


class StyleRegistry:
    """Minimal Word style registry following Okapi's basedOn resolution order."""

    def __init__(
        self,
        styles: list[StyleDefinition] | tuple[StyleDefinition, ...] = (),
        *,
        document_defaults: dict[str, str] | None = None,
    ) -> None:
        self._styles = {style.style_id: style for style in styles}
        self._document_defaults = dict(document_defaults or {})

    @classmethod
    def from_xml(cls, xml: bytes | str) -> "StyleRegistry":
        root = ET.fromstring(xml)
        defaults = cls._run_properties_from_element(
            root.find(f"{WP}docDefaults/{WP}rPrDefault/{WP}rPr")
        )
        styles: list[StyleDefinition] = []
        for element in root.findall(f"{WP}style"):
            style_id = element.get(f"{WP}styleId")
            if not style_id:
                continue
            run_properties = cls._run_properties_from_element(
                element.find(f"{WP}rPr")
            )
            paragraph_properties = cls._paragraph_properties_from_element(
                element.find(f"{WP}pPr")
            )
            based_on = element.find(f"{WP}basedOn")
            linked = element.find(f"{WP}link")
            styles.append(
                StyleDefinition(
                    style_id=style_id,
                    style_type=element.get(f"{WP}type", "paragraph"),
                    based_on=based_on.get(f"{WP}val") if based_on is not None else None,
                    linked_style=linked.get(f"{WP}val") if linked is not None else None,
                    default=element.get(f"{WP}default", "0") in {"1", "true", "on"},
                    run_properties=run_properties,
                    paragraph_properties=paragraph_properties,
                )
            )
        return cls(styles, document_defaults=defaults)

    @staticmethod
    def _run_properties_from_element(element: ET.Element | None) -> dict[str, str]:
        if element is None:
            return {}
        result: dict[str, str] = {}
        boolean_names = {
            "b": "bold",
            "i": "italic",
            "strike": "strike",
            "vanish": "hidden",
        }
        for tag, key in boolean_names.items():
            node = element.find(f"{WP}{tag}")
            if node is not None:
                result[key] = "false" if node.get(f"{WP}val") in {"0", "false", "off"} else "true"
        scalar = {
            "u": "underline",
            "color": "color",
            "sz": "size",
            "szCs": "size_cs",
            "highlight": "highlight",
            "vertAlign": "vert_align",
            "rStyle": "run_style",
        }
        for tag, key in scalar.items():
            node = element.find(f"{WP}{tag}")
            if node is not None:
                value = node.get(f"{WP}val")
                if value is not None:
                    result[key] = value
        fonts = element.find(f"{WP}rFonts")
        if fonts is not None:
            for attribute in ("ascii", "hAnsi", "cs", "eastAsia"):
                value = fonts.get(f"{WP}{attribute}")
                if value:
                    result["font"] = value
                    break
        return result

    @staticmethod
    def _paragraph_properties_from_element(element: ET.Element | None) -> dict[str, str]:
        if element is None:
            return {}
        result: dict[str, str] = {}
        for child in element:
            value = child.get(f"{WP}val")
            result[child.tag.removeprefix(WP)] = "true" if value is None else value
        return result

    def resolve_run_properties(self, style_id: str | None) -> dict[str, str]:
        result = dict(self._document_defaults)
        target = self._effective_style(style_id, "paragraph")
        if target is not None:
            for style in self._chain(target):
                result.update(style.run_properties or {})
        return result

    def resolve_character_run_properties(
        self,
        paragraph_style: str | None,
        run_style: str | None,
        direct: dict[str, str] | None = None,
    ) -> dict[str, str]:
        result = dict(self._document_defaults)
        paragraph = self._effective_style(paragraph_style, "paragraph")
        if paragraph is not None:
            for style in self._chain(paragraph):
                result.update(style.run_properties or {})
        character = self._effective_style(run_style, "character")
        if character is not None:
            if character.linked_style:
                linked = self._styles.get(character.linked_style)
                if linked is not None and linked.style_type == "paragraph":
                    for style in self._chain(linked):
                        result.update(style.run_properties or {})
            for style in self._chain(character):
                result.update(style.run_properties or {})
        result.update(direct or {})
        return result

    def _effective_style(self, style_id: str | None, expected_type: str) -> StyleDefinition | None:
        if style_id:
            style = self._styles.get(style_id)
            if style is not None and style.style_type == expected_type:
                return style
        candidates = [s for s in self._styles.values() if s.style_type == expected_type and s.default]
        return candidates[0] if candidates else None

    def _chain(self, style: StyleDefinition):
        chain: list[StyleDefinition] = []
        seen: set[str] = set()
        current: StyleDefinition | None = style
        while current is not None:
            if current.style_id in seen:
                raise ValueError(f"basedOn cycle detected at style '{current.style_id}'")
            seen.add(current.style_id)
            chain.append(current)
            parent = self._styles.get(current.based_on) if current.based_on else None
            if parent is not None and parent.style_type != current.style_type:
                parent = None
            current = parent
        yield from reversed(chain)
