from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json

from core.document.model import Code, Markup, Skeleton, TextFragment, TextUnit
from core.events.model import Event, EventType, StartDocument, Ending
from filters.docx.styles import StyleRegistry
from filters.docx.markup import MarkupComponentParser
from filters.docx.fields import ComplexFieldStream

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
DC = "http://purl.org/dc/elements/1.1/"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"


class DocxReader:
    """Reader DOCX zachowujący podstawową strukturę dokumentu."""

    def __init__(
        self,
        *,
        translate_word_hidden: bool = False,
        translate_word_numbering_level_text: bool = False,
        translate_external_hyperlinks: bool = False,
        translate_word_in_exclude_style_mode: bool = True,
        exclude_word_styles: set[str] | None = None,
        translate_word_exclude_colors: bool = False,
        exclude_word_colors: set[str] | None = None,
        translate_word_in_exclude_highlight_mode: bool = True,
        word_highlight_colors: set[str] | None = None,
    ) -> None:
        self._complex_fields: tuple = ()
        self._translate_word_hidden = translate_word_hidden
        self._translate_word_numbering_level_text = translate_word_numbering_level_text
        self._translate_external_hyperlinks = translate_external_hyperlinks
        self._translate_word_in_exclude_style_mode = translate_word_in_exclude_style_mode
        self._exclude_word_styles = set(exclude_word_styles or ())
        self._translate_word_exclude_colors = translate_word_exclude_colors
        self._exclude_word_colors = {self._canonical_color(value) for value in (exclude_word_colors or ())}
        self._translate_word_in_exclude_highlight_mode = translate_word_in_exclude_highlight_mode
        self._word_highlight_colors = {self._canonical_color(value) for value in (word_highlight_colors or ())}
        self._field_stream = ComplexFieldStream()
        self._part_paragraph_counters: dict[str, int] = {}

    @property
    def complex_fields(self):
        return self._complex_fields

    def read(self, source: str | Path):
        path = Path(source)
        self._part_paragraph_counters = {}
        with ZipFile(path) as archive:
            root = ET.fromstring(archive.read("word/document.xml"))
            styles = StyleRegistry.from_xml(archive.read("word/styles.xml")) if "word/styles.xml" in archive.namelist() else StyleRegistry()
            relationships = self._read_relationships(archive, "word/_rels/document.xml.rels")
            auxiliary_parts = self._read_auxiliary_parts(archive, relationships)
            note_parts = self._read_note_parts(archive)
            core_properties = (
                ET.fromstring(archive.read("docProps/core.xml"))
                if "docProps/core.xml" in archive.namelist()
                else None
            )
            numbering_root = (
                ET.fromstring(archive.read("word/numbering.xml"))
                if "word/numbering.xml" in archive.namelist()
                else None
            )

        yield Event(EventType.START_DOCUMENT, StartDocument(path.name, str(path.resolve())))
        unit_id = 0
        if core_properties is not None:
            for element_name, element in self._core_property_elements(core_properties):
                unit_id += 1
                yield Event(
                    EventType.TEXT_UNIT,
                    TextUnit(
                        str(unit_id),
                        (TextFragment((element.text or "",)),),
                        {
                            "part": "core_properties",
                            "source_part_name": "docProps/core.xml",
                            "source_element_tag": element_name,
                            "source_element_index": str(
                                sum(1 for candidate in core_properties.iter(element.tag) if candidate is element)
                                - 1
                            ),
                            "source_text_parts": json.dumps(
                                [element.text or ""],
                                ensure_ascii=False,
                                separators=(",", ":"),
                            ),
                        },
                    ),
                )
        if self._translate_external_hyperlinks:
            for unit in self._external_hyperlink_units(path):
                unit_id += 1
                yield Event(EventType.TEXT_UNIT, unit)
        if self._translate_word_numbering_level_text and numbering_root is not None:
            for unit in self._numbering_text_units(root, numbering_root, unit_id):
                unit_id += 1
                yield Event(EventType.TEXT_UNIT, unit)

        skeleton_parts = []
        body = root.find(f"{W}body")
        if body is not None:
            for block in body:
                if block.tag == f"{W}p":
                    skeleton_parts.append("paragraph")
                    unit_id += 1
                    yield from self._paragraph_event(block, unit_id, relationships=relationships, part="body", source_part_name="word/document.xml", style_registry=styles)
                    textbox_index = 0
                    seen_textbox_keys: set[tuple] = set()
                    for textbox_paragraph, textbox_key, paragraph_index, drawingml, vml in self._textbox_entries(block):
                        dedupe_key = (textbox_key, paragraph_index)
                        if dedupe_key in seen_textbox_keys:
                            continue
                        seen_textbox_keys.add(dedupe_key)
                        unit_id += 1
                        textbox_metadata = {
                            "text_box": "true",
                            "text_box_index": str(textbox_index),
                            "text_box_id": f"{textbox_key[0]}:{textbox_key[1]}",
                            "text_box_paragraph_index": str(paragraph_index),
                        }
                        if drawingml is not None:
                            textbox_metadata["textbox_drawingml"] = json.dumps(drawingml, ensure_ascii=False, separators=(",", ":"))
                        if vml is not None:
                            textbox_metadata["textbox_vml"] = json.dumps(vml, ensure_ascii=False, separators=(",", ":"))
                        yield from self._paragraph_event(
                            textbox_paragraph,
                            unit_id,
                            relationships=relationships,
                            part="body",
                            metadata_extra=textbox_metadata,
                            style_registry=styles,
                            source_part_name="word/document.xml",
                        )
                        textbox_index += 1
                elif block.tag == f"{W}tbl":
                    skeleton_parts.append("table")
                    table_index = skeleton_parts.count("table") - 1
                    for row_index, row in enumerate(block.findall(f"{W}tr")):
                        for cell_index, cell in enumerate(row.findall(f"{W}tc")):
                            for paragraph in cell.findall(f".//{W}p"):
                                unit_id += 1
                                yield from self._paragraph_event(
                                    paragraph, unit_id,
                                    relationships=relationships,
                                    metadata_extra={
                                        "container": "table",
                                        "table": str(table_index),
                                        "row": str(row_index),
                                        "cell": str(cell_index),
                                    },
                                    style_registry=styles,
                                    source_part_name="word/document.xml",
                                )

        yield Event(EventType.DOCUMENT_PART, Skeleton(tuple(skeleton_parts)))

        for part_name, part_root in auxiliary_parts:
            part_kind = "header" if "/header" in part_name else "footer"
            for paragraph in part_root.iter(f"{W}p"):
                unit_id += 1
                yield from self._paragraph_event(
                    paragraph, unit_id, relationships=relationships, part=part_kind, source_part_name=part_name, style_registry=styles
                )

        for note_part_name, part_kind, part_root in note_parts:
            for note in part_root:
                allowed = (f"{W}footnote", f"{W}endnote", f"{W}comment")
                if note.tag not in allowed or (part_kind != "comment" and note.get(f"{W}id") in {"-1", "0"}):
                    continue
                for paragraph in note.findall(f"{W}p"):
                    unit_id += 1
                    yield from self._paragraph_event(paragraph, unit_id, relationships=relationships, part=part_kind, metadata_extra={("comment_id" if part_kind == "comment" else "note_id"): note.get(f"{W}id", "")}, source_part_name=note_part_name, style_registry=styles)

        self._complex_fields = self._field_stream.finish()
        yield Event(EventType.END_DOCUMENT, Ending())

    @staticmethod
    def _core_property_elements(root: ET.Element):
        translatable = {
            f"{{{DC}}}title",
            f"{{{DC}}}subject",
            f"{{{DC}}}creator",
            f"{{{DC}}}description",
            f"{{{CP}}}category",
            f"{{{CP}}}contentStatus",
            f"{{{CP}}}keywords",
        }
        for element in root:
            if element.tag in translatable and element.text is not None:
                yield element.tag, element

    def _external_hyperlink_units(self, archive_path: Path):
        hyperlink_type = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
        with ZipFile(archive_path) as archive:
            relationship_parts = sorted(
                name for name in archive.namelist()
                if name.endswith(".rels") and "/_rels/" in name
            )
            for name in relationship_parts:
                root = ET.fromstring(archive.read(name))
                for relationship in root:
                    if (
                        relationship.get("Type") == hyperlink_type
                        and relationship.get("TargetMode") == "External"
                        and relationship.get("Target")
                    ):
                        target = relationship.get("Target")
                        yield TextUnit(
                            f"relationship:{name}:{relationship.get('Id')}",
                            (TextFragment((target,)),),
                            {
                                "part": "relationships",
                                "source_part_name": name,
                                "source_relationship_id": relationship.get("Id", ""),
                                "source_original": target,
                                "source_text_parts": json.dumps([target], ensure_ascii=False, separators=(",", ":")),
                            },
                        )

    def _read_relationships(self, archive: ZipFile, name: str) -> dict[str, str]:
        if name not in archive.namelist():
            return {}
        root = ET.fromstring(archive.read(name))
        return {
            rel.get("Id"): rel.get("Target")
            for rel in root
            if rel.get("Id") and rel.get("Target")
        }

    def _read_note_parts(self, archive: ZipFile):
        result = []
        for name, kind in (("word/footnotes.xml", "footnote"), ("word/endnotes.xml", "endnote"), ("word/comments.xml", "comment")):
            if name in archive.namelist():
                result.append((name, kind, ET.fromstring(archive.read(name))))
        return result

    def _read_auxiliary_parts(self, archive: ZipFile, relationships: dict[str, str]):
        result = []
        for target in relationships.values():
            normalized = target.lstrip("/")
            if normalized in archive.namelist() and ("/header" in normalized or "/footer" in normalized):
                result.append((normalized, ET.fromstring(archive.read(normalized))))
        for name in archive.namelist():
            if name.startswith("word/header") and name.endswith(".xml") and not any(name == p[0] for p in result):
                result.append((name, ET.fromstring(archive.read(name))))
            if name.startswith("word/footer") and name.endswith(".xml") and not any(name == p[0] for p in result):
                result.append((name, ET.fromstring(archive.read(name))))
        return result

    def _textbox_container_key(self, node: ET.Element) -> tuple:
        """Return a representation-independent identity for a text-box container."""
        anchor_id = next(
            (value for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] == "anchorId"),
            None,
        )
        if anchor_id:
            return ("anchor-id", anchor_id)
        return (
            "container",
            node.tag.rsplit("}", 1)[-1],
            tuple(sorted(
                (key.rsplit("}", 1)[-1], value)
                for key, value in node.attrib.items()
                if key.rsplit("}", 1)[-1] not in {"editId", "docPr"}
            )),
        )

    def _textbox_entries(self, block: ET.Element):
        """Enumerate text-box paragraphs and pair DrawingML/VML representations."""
        groups: dict[tuple, dict[str, object]] = {}
        order: list[tuple] = []
        anchor_groups_by_signature: dict[tuple, list[tuple]] = {}

        def signature(node: ET.Element) -> tuple:
            content = node.find(f".//{{{W}}}txbxContent")
            if content is None:
                return ()
            return tuple(
                (element.tag.rsplit("}", 1)[-1], element.text or "")
                for element in content.iter()
            )

        def ensure_group(key: tuple) -> dict[str, object]:
            if key not in groups:
                groups[key] = {"drawingml": None, "vml": None, "paragraphs": []}
                order.append(key)
            return groups[key]

        for node in block.iter():
            local_name = node.tag.rsplit("}", 1)[-1]
            if local_name not in {"anchor", "shape"}:
                continue
            paragraphs = node.findall(f".//{W}txbxContent/{W}p")
            if not paragraphs:
                continue

            anchor_id = next(
                (value for key, value in node.attrib.items() if key.rsplit("}", 1)[-1] == "anchorId"),
                None,
            )
            if anchor_id:
                key = ("anchor-id", anchor_id)
                if local_name == "anchor":
                    anchor_groups_by_signature.setdefault(signature(node), []).append(key)
            elif local_name == "anchor":
                key = self._textbox_container_key(node)
                anchor_groups_by_signature.setdefault(signature(node), []).append(key)
            else:
                matching = [
                    candidate
                    for candidate in anchor_groups_by_signature.get(signature(node), [])
                    if groups[candidate]["vml"] is None
                ]
                key = matching[0] if matching else self._textbox_container_key(node)

            group = ensure_group(key)
            representation = "drawingml" if local_name == "anchor" else "vml"
            if group[representation] is None:
                group[representation] = {
                    "tag": node.tag,
                    "attrib": dict(node.attrib),
                    "xml": ET.tostring(node, encoding="unicode"),
                }
            if not group["paragraphs"]:
                group["paragraphs"] = list((paragraph, index) for index, paragraph in enumerate(paragraphs))

        entries = []
        for key in order:
            group = groups[key]
            for paragraph, paragraph_index in group["paragraphs"]:
                entries.append((
                    paragraph,
                    key,
                    paragraph_index,
                    group["drawingml"],
                    group["vml"],
                ))
        return entries

    def _textbox_templates(self, block: ET.Element, paragraph: ET.Element):
        """Capture matching DrawingML/VML containers for dynamic round-trip."""
        wanted = "".join(n.text or "" for n in paragraph.iter(f"{W}t"))
        drawingml = None
        vml = None
        for node in block.iter():
            if node.tag.endswith("}anchor") and any(
                "".join(n.text or "" for n in child.iter(f"{W}t")) == wanted
                for child in node.iter(f"{W}p")
            ):
                drawingml = {"tag": node.tag, "attrib": dict(node.attrib), "xml": ET.tostring(node, encoding="unicode")}
                break
        for node in block.iter():
            if node.tag.endswith("}shape") and any(
                "".join(n.text or "" for n in child.iter(f"{W}t")) == wanted
                for child in node.iter(f"{W}p")
            ):
                vml = {"tag": node.tag, "attrib": dict(node.attrib), "xml": ET.tostring(node, encoding="unicode")}
                break
        return drawingml, vml

    @staticmethod
    def _translatable_attribute_items(paragraph: ET.Element):
        items = []
        for element in paragraph.iter():
            local_name = element.tag.rsplit("}", 1)[-1]
            if local_name in {"docPr", "cNvPr"}:
                value = element.get("name")
                if value:
                    items.append(
                        (
                            value,
                            {
                                "tag": element.tag,
                                "attribute": "name",
                                "id_attribute": "id",
                                "id_value": element.get("id"),
                                "original": value,
                            },
                        )
                    )
            elif local_name == "textpath":
                value = element.get("string")
                if value:
                    items.append(
                        (
                            value,
                            {
                                "tag": element.tag,
                                "attribute": "string",
                                "id_attribute": None,
                                "id_value": None,
                                "original": value,
                            },
                        )
                    )
        return items

    def _numbering_text_units(self, document_root: ET.Element, numbering_root: ET.Element, unit_id: int):
        nums = {}
        for num in numbering_root.findall(f"{W}num"):
            num_id = num.get(f"{W}numId")
            abstract = num.find(f"{W}abstractNumId")
            if num_id and abstract is not None:
                nums[num_id] = abstract.get(f"{W}val")
        abstracts = {}
        for abstract in numbering_root.findall(f"{W}abstractNum"):
            abstract_id = abstract.get(f"{W}abstractNumId")
            if not abstract_id:
                continue
            levels = {}
            for lvl in abstract.findall(f"{W}lvl"):
                ilvl = lvl.get(f"{W}ilvl")
                text = lvl.find(f"{W}lvlText")
                if ilvl is not None and text is not None and text.get(f"{W}val") is not None:
                    levels[ilvl] = text
            abstracts[abstract_id] = levels
        referenced = []
        seen = set()
        for paragraph in document_root.findall(f".//{W}p"):
            numpr = paragraph.find(f"{W}pPr/{W}numPr")
            if numpr is None:
                continue
            num_id = numpr.find(f"{W}numId")
            ilvl = numpr.find(f"{W}ilvl")
            if num_id is None:
                continue
            num_id_value = num_id.get(f"{W}val", "")
            ilvl_value = ilvl.get(f"{W}val", "0") if ilvl is not None else "0"
            key = (num_id_value, ilvl_value)
            if key not in seen:
                seen.add(key)
                referenced.append(key)
        for num_id, ilvl in referenced:
            abstract_id = nums.get(num_id)
            if abstract_id is None:
                continue
            lvl = abstracts.get(abstract_id, {}).get(ilvl)
            if lvl is None:
                continue
            value = lvl.get(f"{W}val", "")
            parts: list[object] = []
            cursor = 0
            import re
            for match in re.finditer(r"%[1-9]", value):
                if match.start() > cursor:
                    parts.append(value[cursor:match.start()])
                parts.append(Code(match.group(0), "level_number"))
                cursor = match.end()
            if cursor < len(value):
                parts.append(value[cursor:])
            if not parts:
                parts = [""]
            yield TextUnit(
                str(unit_id + len(seen)),
                (TextFragment(tuple(parts)),),
                {
                    "part": "numbering",
                    "source_part_name": "word/numbering.xml",
                    "num_id": num_id,
                    "num_level": ilvl,
                    "source_original": value,
                },
            )

    def _paragraph_event(
        self,
        paragraph: ET.Element,
        unit_id: int,
        relationships: dict[str, str] | None = None,
        part: str | None = None,
        metadata_extra: dict[str, str] | None = None,
        style_registry: StyleRegistry | None = None,
        source_part_name: str | None = None,
    ):
        paragraph_style_id = None
        style = paragraph.find(f"{W}pPr/{W}pStyle")
        if style is not None:
            paragraph_style_id = style.get(f"{W}val")
        if self._paragraph_style_excluded(paragraph_style_id):
            return
        attribute_items = self._translatable_attribute_items(paragraph)
        fragments = [
            TextFragment((value,))
            for value, _ in attribute_items
        ]
        fragments.extend(
            self._collect_paragraph_fragments(
                paragraph,
                relationships or {},
                paragraph_style_id,
                style_registry,
            )
        )
        style = paragraph.find(f"{W}pPr/{W}pStyle")
        numbering = paragraph.find(f"{W}pPr/{W}numPr")
        metadata = dict(metadata_extra or {})
        if style is not None:
            metadata["style"] = style.get(f"{W}val")
        if numbering is not None:
            level = numbering.find(f"{W}ilvl")
            num_id = numbering.find(f"{W}numId")
            if level is not None and level.get(f"{W}val") is not None:
                metadata["num_level"] = level.get(f"{W}val")
            if num_id is not None and num_id.get(f"{W}val") is not None:
                metadata["num_id"] = num_id.get(f"{W}val")
        if part:
            metadata["part"] = part
        if attribute_items:
            metadata["source_attribute_locators"] = json.dumps(
                [locator for _, locator in attribute_items],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        if source_part_name:
            paragraph_index = self._part_paragraph_counters.get(source_part_name, 0)
            metadata["source_part_name"] = source_part_name
            metadata["source_paragraph_index"] = str(paragraph_index)
            metadata["source_text_parts"] = json.dumps(
                [
                    part
                    for fragment in fragments
                    for part in fragment.parts
                    if isinstance(part, str)
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            self._part_paragraph_counters[source_part_name] = paragraph_index + 1
        event = Event(
            EventType.TEXT_UNIT,
            TextUnit(str(unit_id), tuple(fragments), metadata or None),
        )
        self._field_stream.feed(tuple(part for fragment in event.resource.fragments for part in fragment.parts))
        yield event

    def _paragraph_style_excluded(self, style_id: str | None) -> bool:
        if not style_id or not self._exclude_word_styles:
            return False
        listed = style_id in self._exclude_word_styles
        if self._translate_word_in_exclude_style_mode:
            return listed
        return not listed

    def _run_style_excluded(self, paragraph_style_id: str | None, run_style: str | None) -> bool:
        # In Okapi's style mode, an explicitly styled run takes precedence;
        # otherwise the paragraph style controls the run.
        style_id = run_style or paragraph_style_id
        if not self._exclude_word_styles:
            return False
        if not style_id:
            # Inclusion mode means only explicitly listed styles are translated;
            # an unstyled run therefore has to be masked as well.
            return not self._translate_word_in_exclude_style_mode
        listed = style_id in self._exclude_word_styles
        if self._translate_word_in_exclude_style_mode:
            return listed
        return not listed

    @staticmethod
    def _canonical_color(value: object) -> str:
        aliases = {
            "black": "000000", "red": "ff0000", "green": "008000",
            "blue": "0000ff", "yellow": "ffff00", "white": "ffffff",
            "cyan": "00ffff", "magenta": "ff00ff",
        }
        normalized = str(value).strip().lower()
        return aliases.get(normalized, normalized.lstrip("#"))

    def _color_excluded(self, color: str | None) -> bool:
        return (
            self._translate_word_exclude_colors
            and color is not None
            and self._canonical_color(color) in self._exclude_word_colors
        )

    def _highlight_excluded(self, highlight: str | None) -> bool:
        colors = self._word_highlight_colors
        if self._translate_word_in_exclude_highlight_mode:
            return highlight is not None and self._canonical_color(highlight) in colors
        return highlight is None or self._canonical_color(highlight) not in colors

    def _run_content_excluded(self, resolved: dict[str, str], direct_properties: dict[str, str] | None) -> bool:
        properties = resolved or (direct_properties or {})
        return self._color_excluded(properties.get("color")) or self._highlight_excluded(properties.get("highlight"))

    def _mask_run_parts(self, parts: list[object], excluded: bool) -> list[object]:
        if not excluded:
            return parts
        return [
            Code(part, "excluded_style") if isinstance(part, str) else part
            for part in parts
        ]

    def _collect_paragraph_fragments(
        self, paragraph: ET.Element, relationships: dict[str, str], paragraph_style_id: str | None = None, style_registry: StyleRegistry | None = None
    ) -> list[TextFragment]:
        fragments: list[TextFragment] = []
        markup_parser = MarkupComponentParser()
        for child in paragraph:
            if child.tag == f"{W}hyperlink":
                runs = [node for node in child if node.tag == f"{W}r"]
                nested_hyperlinks = [node for node in child if node.tag == f"{W}hyperlink"]
                if len(runs) == 1 and not nested_hyperlinks:
                    text = "".join(node.text or "" for node in child.iter(f"{W}t"))
                    if text:
                        rel_id = child.get(f"{R}id")
                        fragments.append(TextFragment((Code(text, "hyperlink", relationships.get(rel_id)),)))
                else:
                    fragments.extend(self._hyperlink_fragments(child, relationships, paragraph_style_id, style_registry))
            elif child.tag == f"{W}fldSimple":
                text = "".join(node.text or "" for node in child.iter(f"{W}t"))
                if text:
                    fragments.append(TextFragment((Code(text, "protected"),)))
            elif child.tag == f"{W}ruby":
                for nested in child:
                    if nested.tag in {f"{W}rt", f"{W}rubyBase"}:
                        fragments.extend(self._collect_paragraph_fragments(nested, relationships, paragraph_style_id, style_registry))
            elif child.tag == f"{W}r":
                parts: list[object] = []
                for node in child:
                    if node.tag == f"{W}t" and node.text is not None:
                        parts.append(node.text)
                    elif node.tag == f"{W}delText" and node.text is not None:
                        parts.append(Code(node.text, "protected"))
                    elif node.tag == f"{W}footnoteReference":
                        parts.append(Code(node.get(f"{W}id", ""), "footnote"))
                    elif node.tag == f"{W}endnoteReference":
                        parts.append(Code(node.get(f"{W}id", ""), "endnote"))
                    elif node.tag == f"{W}tab":
                        parts.append(Code("\t", "tab"))
                    elif node.tag == f"{W}br":
                        parts.append(Code(node.get(f"{W}type", "textWrapping"), "line_break"))
                    elif node.tag == f"{W}noBreakHyphen":
                        parts.append(Code("-", "no_break_hyphen"))
                    elif node.tag == f"{W}bookmarkStart":
                        parts.append(Code(node.get(f"{W}name", ""), "bookmark_start", node.get(f"{W}id")))
                    elif node.tag == f"{W}bookmarkEnd":
                        parts.append(Code(node.get(f"{W}id", ""), "bookmark_end"))
                    elif node.tag == f"{W}fldChar":
                        parts.append(Code(node.get(f"{W}fldCharType", ""), "field_char"))
                    elif node.tag == f"{W}instrText" and node.text:
                        parts.append(Code(node.text, "field_instruction"))
                    elif node.tag == f"{W}ruby":
                        for text_node in node.iter(f"{W}t"):
                            if text_node.text is not None:
                                parts.append(text_node.text)
                if parts:
                    direct_properties = self._run_properties(child)
                    fragment_style = None
                    run_style = direct_properties.get("run_style") if direct_properties else None
                    excluded_style = self._run_style_excluded(paragraph_style_id, run_style)
                    if style_registry is not None:
                        resolved = style_registry.resolve_character_run_properties(paragraph_style_id, run_style, direct_properties)
                        fragment_style = {f"resolved_{key}": value for key, value in resolved.items()}
                        hidden = resolved.get("hidden") == "true"
                    else:
                        hidden = bool(direct_properties and direct_properties.get("hidden") == "true")
                    excluded_content = excluded_style or self._run_content_excluded(resolved if style_registry is not None else {}, direct_properties)
                    parts = self._mask_run_parts(parts, excluded_content)
                    if hidden and not self._translate_word_hidden:
                        parts = [part for part in parts if not isinstance(part, str)]
                    if parts:
                        fragments.append(TextFragment(tuple(parts), direct_properties, fragment_style))
            elif child.tag == f"{W}bookmarkStart":
                fragments.append(TextFragment((Code(child.get(f"{W}name", ""), "bookmark_start", child.get(f"{W}id")),)))
            elif child.tag == f"{W}bookmarkEnd":
                fragments.append(TextFragment((Code(child.get(f"{W}id", ""), "bookmark_end"),)))
            elif child.tag == f"{W}ins":
                # Okapi's default is to automatically accept inserted revisions:
                # the revision wrapper is skipped, while its run content remains
                # ordinary translatable content.
                fragments.extend(
                    self._collect_paragraph_fragments(
                        child,
                        relationships,
                        paragraph_style_id,
                        style_registry,
                    )
                )
            elif child.tag == f"{W}del":
                # Deleted revisions are skipped by Okapi's default revision policy.
                continue
            elif child.tag == f"{W}proofErr":
                fragments.append(TextFragment((markup_parser.empty(child),)))
        return fragments or [TextFragment(tuple())]

    def _hyperlink_fragments(self, hyperlink: ET.Element, relationships: dict[str, str], paragraph_style_id: str | None, style_registry: StyleRegistry | None) -> list[TextFragment]:
        parser = MarkupComponentParser()
        rel_id = hyperlink.get(f"{R}id")
        fragments: list[TextFragment] = [TextFragment((Markup.start(parser.name(hyperlink), parser.attributes(hyperlink), target=relationships.get(rel_id)),))]
        for child in hyperlink:
            if child.tag == f"{W}hyperlink":
                fragments.extend(self._hyperlink_fragments(child, relationships, paragraph_style_id, style_registry))
                continue
            if child.tag != f"{W}r":
                continue
            direct_properties = self._run_properties(child)
            fragment_style = None
            if style_registry is not None:
                run_style = direct_properties.get("run_style") if direct_properties else None
                resolved = style_registry.resolve_character_run_properties(paragraph_style_id, run_style, direct_properties)
                fragment_style = {f"resolved_{key}": value for key, value in resolved.items()}
            parts: list[object] = []
            for node in child:
                if node.tag == f"{W}t" and node.text is not None:
                    parts.append(node.text)
                elif node.tag == f"{W}tab":
                    parts.append(Code("\t", "tab"))
                elif node.tag == f"{W}br":
                    parts.append(Code(node.get(f"{W}type", "textWrapping"), "line_break"))
                elif node.tag == f"{W}noBreakHyphen":
                    parts.append(Code("-", "no_break_hyphen"))
            if parts:
                run_style = direct_properties.get("run_style") if direct_properties else None
                parts = self._mask_run_parts(
                    parts,
                    self._run_style_excluded(paragraph_style_id, run_style),
                )
                hidden = False
                if style_registry is not None:
                    resolved = style_registry.resolve_character_run_properties(paragraph_style_id, run_style, direct_properties)
                    hidden = resolved.get("hidden") == "true"
                elif direct_properties:
                    hidden = direct_properties.get("hidden") == "true"
                resolved_properties = resolved if style_registry is not None else (direct_properties or {})
                if self._run_content_excluded(resolved_properties, direct_properties):
                    parts = self._mask_run_parts(parts, True)
                if hidden and not self._translate_word_hidden:
                    parts = [part for part in parts if not isinstance(part, str)]
                if parts:
                    fragments.append(TextFragment(tuple(parts), direct_properties, fragment_style))
        fragments.append(TextFragment((Markup.end(parser.name(hyperlink)),)))
        return fragments

    def _run_properties(self, run: ET.Element) -> dict[str, str] | None:
        rpr = run.find(f"{W}rPr")
        if rpr is None:
            return None
        result: dict[str, str] = {}
        for tag, key in (("b", "bold"), ("i", "italic"), ("strike", "strike"), ("vanish", "hidden")):
            node = rpr.find(f"{W}{tag}")
            if node is not None:
                value = node.get(f"{W}val")
                result[key] = "false" if value in {"0", "false", "off", "no"} else "true"
        underline = rpr.find(f"{W}u")
        if underline is not None:
            result["underline"] = underline.get(f"{W}val", "single")
        for tag, key, attr in (
            ("color", "color", "val"),
            ("sz", "size", "val"),
            ("szCs", "size_cs", "val"),
            ("highlight", "highlight", "val"),
            ("vertAlign", "vert_align", "val"),
            ("rStyle", "run_style", "val"),
        ):
            element = rpr.find(f"{W}{tag}")
            if element is not None and element.get(f"{W}{attr}") is not None:
                result[key] = element.get(f"{W}{attr}")
        fonts = rpr.find(f"{W}rFonts")
        if fonts is not None:
            font_attrs = ("ascii", "hAnsi", "cs", "eastAsia", "asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme", "hint")
            present_fonts = {attr: fonts.get(f"{W}{attr}") for attr in font_attrs}
            present_fonts = {attr: value for attr, value in present_fonts.items() if value}
            # Keep the historical single-font representation compact; preserve
            # every category when the source actually distinguishes categories.
            if len(present_fonts) > 1 or any(attr.endswith("Theme") or attr == "hint" for attr in present_fonts):
                result.update({f"font_{attr}": value for attr, value in present_fonts.items()})
            for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
                value = fonts.get(f"{W}{attr}")
                if value:
                    result["font"] = value
                    break
        return result or None

