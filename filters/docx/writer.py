from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile
import shutil
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring, fromstring
import json

from core.document.model import Code, Markup, TextUnit
from core.events.model import Event, EventType

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
register_namespace("w", W)
register_namespace("r", R)
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
WPS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
register_namespace("wp", WP)
register_namespace("a", A)
register_namespace("wps", WPS)

HYPERLINK_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
HEADER_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
FOOTER_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer"


class DocxWriter:
    """Writer DOCX zachowujący podstawową strukturę dokumentu."""

    def write(self, events, target: str | Path) -> None:
        start_document = next(
            (event.resource for event in events if event.type == EventType.START_DOCUMENT),
            None,
        )
        source_path = getattr(start_document, "source_path", None)
        if source_path:
            self._write_from_source_package(events, target, Path(source_path))
            return

        units = [event.resource for event in events if event.type == EventType.TEXT_UNIT]
        body_units = [u for u in units if (u.metadata or {}).get("part", "body") == "body"]
        header_units = [u for u in units if (u.metadata or {}).get("part") == "header"]
        footer_units = [u for u in units if (u.metadata or {}).get("part") == "footer"]
        footnote_units = [u for u in units if (u.metadata or {}).get("part") == "footnote"]
        endnote_units = [u for u in units if (u.metadata or {}).get("part") == "endnote"]
        comment_units = [u for u in units if (u.metadata or {}).get("part") == "comment"]

        relationships: list[dict[str, str]] = []
        numbered_units = [u for u in body_units if (u.metadata or {}).get("num_id") is not None]
        if numbered_units:
            relationships.append({"id": "rIdNumbering", "target": "numbering.xml", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering"})
        if header_units:
            relationships.append({"id": "rIdHeader", "target": "header1.xml", "type": HEADER_REL_TYPE})
        if footer_units:
            relationships.append({"id": "rIdFooter", "target": "footer1.xml", "type": FOOTER_REL_TYPE})
        if footnote_units:
            relationships.append({"id": "rIdFootnotes", "target": "footnotes.xml", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes"})
        if endnote_units:
            relationships.append({"id": "rIdEndnotes", "target": "endnotes.xml", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes"})
        if comment_units:
            relationships.append({"id": "rIdComments", "target": "comments.xml", "type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"})

        root = Element(f"{{{W}}}document")
        body = SubElement(root, f"{{{W}}}body")
        self._append_body_units(body, body_units, relationships)
        sectpr = SubElement(body, f"{{{W}}}sectPr")
        if header_units:
            ref = SubElement(sectpr, f"{{{W}}}headerReference")
            ref.set(f"{{{W}}}type", "default")
            ref.set(f"{{{R}}}id", "rIdHeader")
        if footer_units:
            ref = SubElement(sectpr, f"{{{W}}}footerReference")
            ref.set(f"{{{W}}}type", "default")
            ref.set(f"{{{R}}}id", "rIdFooter")

        document_xml = tostring(root, encoding="utf-8", xml_declaration=True)
        path = Path(target)
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types(bool(header_units), bool(footer_units), bool(numbered_units), bool(footnote_units), bool(endnote_units), bool(comment_units)))
            archive.writestr("_rels/.rels", self._rels())
            archive.writestr("word/document.xml", document_xml)
            if relationships:
                archive.writestr("word/_rels/document.xml.rels", self._document_rels(relationships))
            if numbered_units:
                archive.writestr("word/numbering.xml", self._numbering_xml(numbered_units))
            if header_units:
                archive.writestr("word/header1.xml", self._part_xml(header_units, relationships))
            if footer_units:
                archive.writestr("word/footer1.xml", self._part_xml(footer_units, relationships))
            if footnote_units:
                archive.writestr("word/footnotes.xml", self._notes_xml(footnote_units, "footnote"))
            if endnote_units:
                archive.writestr("word/endnotes.xml", self._notes_xml(endnote_units, "endnote"))
            if comment_units:
                archive.writestr("word/comments.xml", self._notes_xml(comment_units, "comment"))

    def _write_from_source_package(self, events, target: str | Path, source_path: Path) -> None:
        if not source_path.is_file():
            raise FileNotFoundError(f"DOCX source package not found: {source_path}")

        units = [
            event.resource
            for event in events
            if event.type == EventType.TEXT_UNIT
            and (event.resource.metadata or {}).get("source_part_name")
        ]
        changes_by_part: dict[str, list[TextUnit]] = {}
        for unit in units:
            part = (unit.metadata or {}).get("source_part_name")
            if part:
                changes_by_part.setdefault(part, []).append(unit)

        path = Path(target)
        in_place = path.resolve() == source_path.resolve()
        write_path = path
        if in_place:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            os.close(descriptor)
            write_path = Path(temporary_name)

        try:
            with ZipFile(source_path, "r") as source, ZipFile(write_path, "w", ZIP_DEFLATED) as output:
                for info in source.infolist():
                    data = source.read(info.filename)
                    part_units = changes_by_part.get(info.filename)
                    if part_units and (info.filename.endswith(".xml") or info.filename.endswith(".rels")):
                        data = self._patch_source_xml(data, part_units)
                    output.writestr(info, data)
            if in_place:
                os.chmod(write_path, stat.S_IMODE(source_path.stat().st_mode))
                os.replace(write_path, path)
        except BaseException:
            if in_place:
                write_path.unlink(missing_ok=True)
            raise

    def _patch_source_xml(self, data: bytes, units: list[TextUnit]) -> bytes:
        root = fromstring(data)
        paragraphs = root.findall(f".//{{{W}}}p")
        changed = False
        for unit in units:
            metadata = unit.metadata or {}
            translated_parts = [
                part
                for fragment in unit.fragments
                for part in fragment.parts
                if isinstance(part, str)
            ]
            if not translated_parts:
                continue
            original_parts = json.loads(metadata.get("source_text_parts", "[]"))
            if translated_parts == original_parts:
                continue

            attribute_locators = json.loads(metadata.get("source_attribute_locators", "[]"))
            if attribute_locators:
                if len(translated_parts) < len(attribute_locators):
                    raise ValueError("DOCX translation removed a translatable graphic attribute")
                for locator, value in zip(attribute_locators, translated_parts):
                    candidates = [
                        element
                        for element in root.iter(locator["tag"])
                        if (
                            locator.get("id_value") is None
                            or element.get(locator.get("id_attribute", "id")) == locator.get("id_value")
                        )
                        and element.get(locator["attribute"]) == locator.get("original")
                    ]
                    if not candidates:
                        raise ValueError(
                            f"DOCX translatable attribute not found: {locator['tag']}@{locator['attribute']}"
                        )
                    candidates[0].set(locator["attribute"], value)
                    changed = True
                translated_parts = translated_parts[len(attribute_locators):]
                original_parts = original_parts[len(attribute_locators):]
                if not translated_parts:
                    changed = True
                    continue

            if metadata.get("part") == "relationships":
                relationship_id = metadata.get("source_relationship_id", "")
                original_target = metadata.get("source_original", "")
                if len(translated_parts) != 1:
                    raise ValueError("DOCX external hyperlink must contain exactly one text part")
                if translated_parts[0] == original_target:
                    continue
                candidates = [
                    element for element in root
                    if element.get("Id") == relationship_id
                    and element.get("Type") == HYPERLINK_REL_TYPE
                    and element.get("Target") == original_target
                ]
                if not candidates:
                    raise ValueError(f"DOCX external hyperlink relationship not found: {relationship_id}")
                candidates[0].set("Target", translated_parts[0])
                changed = True
                continue

            if metadata.get("part") == "numbering":
                translated_value = "".join(
                    part.data if isinstance(part, Code) and part.kind == "level_number" else part
                    for fragment in unit.fragments
                    for part in fragment.parts
                    if isinstance(part, str) or (isinstance(part, Code) and part.kind == "level_number")
                )
                original_value = metadata.get("source_original", "")
                if translated_value == original_value:
                    continue
                num_id = metadata.get("num_id", "")
                ilvl = metadata.get("num_level", "0")
                nums = [n for n in root.findall(f".//{{{W}}}num") if n.get(f"{{{W}}}numId") == num_id]
                if not nums:
                    raise ValueError(f"DOCX numbering definition not found: numId={num_id}")
                num = nums[0]
                lvl = None
                text_node = None
                for override in num.findall(f"{{{W}}}lvlOverride"):
                    if override.get(f"{{{W}}}ilvl") == ilvl:
                        candidate = override.find(f"{{{W}}}lvl")
                        if candidate is not None:
                            lvl = candidate
                            break
                        direct_text = override.find(f"{{{W}}}lvlText")
                        if direct_text is not None:
                            text_node = direct_text
                            lvl = override
                            break
                if lvl is None:
                    abstract_id = num.find(f"{{{W}}}abstractNumId")
                    if abstract_id is not None:
                        abstract = next((a for a in root.findall(f".//{{{W}}}abstractNum") if a.get(f"{{{W}}}abstractNumId") == abstract_id.get(f"{{{W}}}val")), None)
                        if abstract is not None:
                            lvl = next((candidate for candidate in abstract.findall(f"{{{W}}}lvl") if candidate.get(f"{{{W}}}ilvl") == ilvl), None)
                if lvl is None:
                    raise ValueError(f"DOCX numbering level not found: numId={num_id}, ilvl={ilvl}")
                if text_node is None:
                    text_node = lvl.find(f"{{{W}}}lvlText")
                if text_node is None:
                    raise ValueError(f"DOCX numbering level has no lvlText: numId={num_id}, ilvl={ilvl}")
                text_node.set(f"{{{W}}}val", translated_value)
                text_node = None
                changed = True
                continue

            source_element_tag = metadata.get("source_element_tag")
            if source_element_tag is not None:
                candidates = list(root.iter(source_element_tag))
                element_index = int(metadata.get("source_element_index", "0"))
                if element_index < 0 or element_index >= len(candidates):
                    raise ValueError(
                        f"DOCX source element index out of range: {source_element_tag}[{element_index}]"
                    )
                if len(translated_parts) != 1:
                    raise ValueError("DOCX core property must contain exactly one text part")
                candidates[element_index].text = translated_parts[0]
                changed = True
                continue

            index_text = metadata.get("source_paragraph_index")
            if index_text is None:
                continue
            index = int(index_text)
            if index < 0 or index >= len(paragraphs):
                raise ValueError(f"DOCX source paragraph index out of range: {index}")
            if metadata.get("text_box") == "true":
                text_box_id = metadata.get("text_box_id", "")
                anchor_id = text_box_id.split(":", 1)[1] if ":" in text_box_id else ""
                paragraphs_to_patch = []
                textbox_index = int(metadata.get("text_box_paragraph_index", metadata.get("text_box_index", "0")))
                for container in root.iter():
                    local_name = container.tag.rsplit("}", 1)[-1]
                    if local_name not in {"anchor", "shape"}:
                        continue
                    candidate_id = next(
                        (value for key, value in container.attrib.items() if key.rsplit("}", 1)[-1] == "anchorId"),
                        "",
                    )
                    if candidate_id != anchor_id:
                        continue
                    candidates = container.findall(f".//{{{W}}}txbxContent/{{{W}}}p")
                    if textbox_index >= len(candidates):
                        raise ValueError(f"DOCX text-box paragraph index out of range: {textbox_index}")
                    paragraphs_to_patch.append(candidates[textbox_index])
                if not paragraphs_to_patch:
                    raise ValueError(f"DOCX text-box container not found: {text_box_id}")
            else:
                paragraphs_to_patch = [paragraphs[index]]
            for paragraph in paragraphs_to_patch:
                text_nodes = list(paragraph.iter(f"{{{W}}}t"))
                if metadata.get("text_box") != "true":
                    textbox_contents = list(paragraph.iter(f"{{{W}}}txbxContent"))
                    excluded = {
                        node
                        for content in textbox_contents
                        for node in content.iter(f"{{{W}}}t")
                    }
                    text_nodes = [node for node in text_nodes if node not in excluded]
                if len(text_nodes) != len(translated_parts):
                    # Style exclusion/inclusion can leave protected source runs
                    # in the same paragraph. Map only the source text parts that
                    # were actually exposed as translatable TextUnit content.
                    matched_nodes = []
                    cursor = 0
                    for original in original_parts:
                        while cursor < len(text_nodes) and text_nodes[cursor].text != original:
                            cursor += 1
                        if cursor >= len(text_nodes):
                            raise ValueError(
                                "DOCX translation could not map a translatable run-text node "
                                f"in paragraph {index}: missing source={original!r}"
                            )
                        matched_nodes.append(text_nodes[cursor])
                        cursor += 1
                    text_nodes = matched_nodes
                if len(text_nodes) != len(translated_parts):
                    raise ValueError(
                        "DOCX translation changed the number of translatable run-text nodes "
                        f"in paragraph {index}: source={len(text_nodes)}, target={len(translated_parts)}"
                    )
                for node, text in zip(text_nodes, translated_parts):
                    if node.text != text:
                        node.text = text
                        if text[:1].isspace() or text[-1:].isspace():
                            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        changed = True

        if not changed:
            return data
        return tostring(root, encoding="utf-8", xml_declaration=True)

    def _append_body_units(self, body: Element, units: list[TextUnit], relationships: list[dict[str, str]]) -> None:
        i = 0
        while i < len(units):
            metadata = units[i].metadata or {}
            if metadata.get("text_box") == "true":
                group = []
                text_box_id = metadata.get("text_box_id")
                while i < len(units):
                    current = units[i]
                    current_meta = current.metadata or {}
                    if current_meta.get("text_box") != "true":
                        break
                    if text_box_id is not None and current_meta.get("text_box_id") != text_box_id:
                        break
                    group.append(current)
                    i += 1
                self._append_textbox(body, group, relationships)
                continue
            if metadata.get("container") == "table":
                table_id = metadata.get("table", "0")
                table = SubElement(body, f"{{{W}}}tbl")
                while i < len(units):
                    current = units[i]
                    current_meta = current.metadata or {}
                    if current_meta.get("container") != "table" or current_meta.get("table", "0") != table_id:
                        break
                    row_id = current_meta.get("row", "0")
                    row = SubElement(table, f"{{{W}}}tr")
                    while i < len(units):
                        current = units[i]
                        current_meta = current.metadata or {}
                        if (current_meta.get("container") != "table"
                                or current_meta.get("table", "0") != table_id
                                or current_meta.get("row", "0") != row_id):
                            break
                        cell = SubElement(row, f"{{{W}}}tc")
                        self._append_unit(cell, current, relationships)
                        i += 1
                continue
            self._append_unit(body, units[i], relationships)
            i += 1

    def _append_textbox(self, body: Element, units: list[TextUnit], relationships: list[dict[str, str]]) -> None:
        outer = SubElement(body, f"{{{W}}}p")
        metadata = units[0].metadata or {}
        drawing_meta = metadata.get("textbox_drawingml")
        vml_meta = metadata.get("textbox_vml")

        if drawing_meta:
            drawing = SubElement(SubElement(outer, f"{{{W}}}r"), f"{{{W}}}drawing")
            anchor = fromstring(json.loads(drawing_meta)["xml"])
            content = anchor.find(f".//{{{W}}}txbxContent")
            if content is not None:
                content.clear()
                for unit in units:
                    self._append_unit(content, unit, relationships)
            drawing.append(anchor)
        else:
            # Legacy/generated fallback when no source DrawingML template exists.
            drawing = SubElement(SubElement(outer, f"{{{W}}}r"), f"{{{W}}}drawing")
            anchor = SubElement(drawing, f"{{{WP}}}anchor", {"distT": "45720", "distB": "45720", "distL": "114300", "distR": "114300", "simplePos": "0", "relativeHeight": "251942912", "behindDoc": "0", "locked": "0", "layoutInCell": "1", "allowOverlap": "1", "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}anchorId": "7F96FC78", "{http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing}editId": "5A50DFE3"})
            SubElement(anchor, f"{{{WP}}}simplePos", {"x": "0", "y": "0"})
            position_h = SubElement(anchor, f"{{{WP}}}positionH", {"relativeFrom": "page"})
            SubElement(position_h, f"{{{WP}}}posOffset").text = "3980443"
            position_v = SubElement(anchor, f"{{{WP}}}positionV", {"relativeFrom": "paragraph"})
            SubElement(position_v, f"{{{WP}}}posOffset").text = "303375"
            SubElement(anchor, f"{{{WP}}}extent", {"cx": "2219960", "cy": "474980"})
            SubElement(anchor, f"{{{WP}}}effectExtent", {"l": "0", "t": "0", "r": "0", "b": "1270"})
            SubElement(anchor, f"{{{WP}}}wrapNone")
            SubElement(anchor, f"{{{WP}}}docPr", {"id": "32", "name": "Text Box 2"})
            frame_locks = SubElement(anchor, f"{{{WP}}}cNvGraphicFramePr")
            SubElement(frame_locks, f"{{{A}}}graphicFrameLocks", {"noChangeAspect": "1"})
            graphic = SubElement(anchor, f"{{{A}}}graphic")
            graphic_data = SubElement(graphic, f"{{{A}}}graphicData", {"uri": WPS})
            wsp = SubElement(graphic_data, f"{{{WPS}}}wsp")
            SubElement(wsp, f"{{{WPS}}}cNvSpPr", {"txBox": "1"})
            sp_pr = SubElement(wsp, f"{{{WPS}}}spPr", {"bwMode": "auto"})
            xfrm = SubElement(sp_pr, f"{{{A}}}xfrm")
            SubElement(xfrm, f"{{{A}}}off", {"x": "0", "y": "0"})
            SubElement(xfrm, f"{{{A}}}ext", {"cx": "2219960", "cy": "474980"})
            SubElement(sp_pr, f"{{{A}}}prstGeom", {"prst": "rect"})
            SubElement(sp_pr, f"{{{A}}}noFill")
            SubElement(sp_pr, f"{{{A}}}ln", {"w": "9525"})
            content = SubElement(SubElement(wsp, f"{{{WPS}}}txbx"), f"{{{W}}}txbxContent")
            SubElement(wsp, f"{{{WPS}}}bodyPr", {"rot": "0", "vert": "horz", "wrap": "square", "lIns": "91440", "tIns": "45720", "rIns": "91440", "bIns": "45720", "anchor": "t", "anchorCtr": "0"})
            for unit in units:
                self._append_unit(content, unit, relationships)

        if vml_meta or not drawing_meta:
            pict = SubElement(SubElement(outer, f"{{{W}}}r"), f"{{{W}}}pict")
            if vml_meta:
                shape = fromstring(json.loads(vml_meta)["xml"])
            else:
                shape = SubElement(pict, "{urn:schemas-microsoft-com:vml}shape", {
                    "id": "_x0000_s1026",
                    "type": "#_x0000_t202",
                    "style": "position:absolute;margin-left:313.4pt;margin-top:0;width:174.8pt;height:37.4pt;z-index:251942912;visibility:visible;mso-wrap-style:square;mso-position-horizontal:absolute;mso-position-horizontal-relative:page;mso-position-vertical:absolute;mso-position-vertical-relative:text;v-text-anchor:top",
                    "coordsize": "21600,21600",
                })
            content = shape.find(f".//{{{W}}}txbxContent")
            if content is None:
                content = SubElement(shape, f"{{{W}}}txbxContent")
            else:
                content.clear()
            for unit in units:
                self._append_unit(content, unit, relationships)
            pict.append(shape)

    def _append_unit(self, parent: Element, unit: TextUnit, relationships: list[dict[str, str]]) -> None:
        paragraph = SubElement(parent, f"{{{W}}}p")
        metadata = unit.metadata or {}
        style = metadata.get("style")
        if style:
            ppr = SubElement(paragraph, f"{{{W}}}pPr")
            pstyle = SubElement(ppr, f"{{{W}}}pStyle")
            pstyle.set(f"{{{W}}}val", style)
        if metadata.get("num_id") is not None:
            ppr = paragraph.find(f"{{{W}}}pPr")
            if ppr is None:
                ppr = SubElement(paragraph, f"{{{W}}}pPr")
            numpr = SubElement(ppr, f"{{{W}}}numPr")
            ilvl = SubElement(numpr, f"{{{W}}}ilvl")
            ilvl.set(f"{{{W}}}val", metadata.get("num_level", "0"))
            num_id = SubElement(numpr, f"{{{W}}}numId")
            num_id.set(f"{{{W}}}val", metadata["num_id"])

        markup_stack = [paragraph]
        for fragment in unit.fragments:
            for part in fragment.parts:
                if isinstance(part, Markup):
                    if part.kind == "start":
                        element = self._markup_element(part, relationships)
                        markup_stack[-1].append(element)
                        markup_stack.append(element)
                    elif part.kind == "end":
                        if len(markup_stack) > 1:
                            markup_stack.pop()
                    else:
                        markup_stack[-1].append(self._markup_element(part))
                elif isinstance(part, str):
                    run = SubElement(markup_stack[-1], f"{{{W}}}r")
                    self._apply_run_properties(run, fragment.metadata)
                    text = SubElement(run, f"{{{W}}}t")
                    text.text = part
                elif isinstance(part, Code):
                    if part.kind == "field_char":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        field = SubElement(run, f"{{{W}}}fldChar")
                        field.set(f"{{{W}}}fldCharType", part.data)
                    elif part.kind == "field_instruction":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        instruction = SubElement(run, f"{{{W}}}instrText")
                        instruction.text = part.data
                    elif part.kind == "tab":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        SubElement(run, f"{{{W}}}tab")
                    elif part.kind == "line_break":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        br = SubElement(run, f"{{{W}}}br")
                        if part.data:
                            br.set(f"{{{W}}}type", part.data)
                    elif part.kind == "no_break_hyphen":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        SubElement(run, f"{{{W}}}noBreakHyphen")
                    elif part.kind == "bookmark_start":
                        element = SubElement(markup_stack[-1], f"{{{W}}}bookmarkStart")
                        element.set(f"{{{W}}}id", part.target or "0")
                        element.set(f"{{{W}}}name", part.data)
                    elif part.kind == "bookmark_end":
                        element = SubElement(markup_stack[-1], f"{{{W}}}bookmarkEnd")
                        element.set(f"{{{W}}}id", part.data)
                    elif part.kind == "footnote":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        element = SubElement(run, f"{{{W}}}footnoteReference")
                        element.set(f"{{{W}}}id", part.data)
                    elif part.kind == "endnote":
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        element = SubElement(run, f"{{{W}}}endnoteReference")
                        element.set(f"{{{W}}}id", part.data)
                    elif part.kind == "protected":
                        field = SubElement(markup_stack[-1], f"{{{W}}}fldSimple")
                        field.set(f"{{{W}}}instr", "PROTECTED")
                        field_run = SubElement(field, f"{{{W}}}r")
                        field_text = SubElement(field_run, f"{{{W}}}t")
                        field_text.text = part.data
                    elif part.kind == "hyperlink":
                        rel_id = self._add_hyperlink_relationship(relationships, part.target or "https://example.com")
                        hyperlink = SubElement(markup_stack[-1], f"{{{W}}}hyperlink")
                        hyperlink.set(f"{{{R}}}id", rel_id)
                        link_run = SubElement(hyperlink, f"{{{W}}}r")
                        link_text = SubElement(link_run, f"{{{W}}}t")
                        link_text.text = part.data
                    else:
                        run = SubElement(markup_stack[-1], f"{{{W}}}r")
                        text = SubElement(run, f"{{{W}}}t")
                        text.text = part.data

    def _markup_element(self, markup: Markup, relationships: list[dict[str, str]] | None = None) -> Element:
        namespace = W
        local_name = markup.name
        if ":" in local_name:
            prefix, local_name = local_name.split(":", 1)
            namespace = {"w": W, "r": R}.get(prefix, W)
        element = Element(f"{{{namespace}}}{local_name}")
        for key, value in markup.attributes:
            attr_namespace = W
            attr_name = key
            if ":" in key:
                prefix, attr_name = key.split(":", 1)
                attr_namespace = {
                    "w": W,
                    "r": R,
                    "xml": "http://www.w3.org/XML/1998/namespace",
                }.get(prefix, W)
            element.set(f"{{{attr_namespace}}}{attr_name}", value)
        if markup.name == "w:hyperlink" and markup.target and relationships is not None:
            rel_id = self._add_hyperlink_relationship(relationships, markup.target)
            element.set(f"{{{R}}}id", rel_id)
        return element

    def _apply_run_properties(self, run: Element, metadata: dict[str, str] | None) -> None:
        if not metadata:
            return
        # `metadata` is the direct rPr layer; resolved_* is diagnostic/base
        # information from the reader and must never be serialized as direct rPr.
        metadata = {key: value for key, value in metadata.items() if not key.startswith("resolved_")}
        if not metadata:
            return
        rpr = SubElement(run, f"{{{W}}}rPr")
        for key, tag in (("bold", "b"), ("italic", "i"), ("strike", "strike"), ("hidden", "vanish")):
            if key in metadata:
                element = SubElement(rpr, f"{{{W}}}{tag}")
                if metadata[key] == "false":
                    element.set(f"{{{W}}}val", "false")
                elif metadata[key] != "true":
                    element.set(f"{{{W}}}val", metadata[key])
        if metadata.get("underline"):
            underline = SubElement(rpr, f"{{{W}}}u")
            underline.set(f"{{{W}}}val", metadata["underline"])
        for key, tag in (("color", "color"), ("size", "sz"), ("size_cs", "szCs"), ("highlight", "highlight"), ("vert_align", "vertAlign"), ("run_style", "rStyle")):
            if metadata.get(key):
                element = SubElement(rpr, f"{{{W}}}{tag}")
                element.set(f"{{{W}}}val", metadata[key])
        font_values = {key[5:]: value for key, value in metadata.items() if key.startswith("font_") and value}
        if metadata.get("font"):
            font_values.setdefault("ascii", metadata["font"])
        if font_values:
            fonts = SubElement(rpr, f"{{{W}}}rFonts")
            for attr in ("ascii", "hAnsi", "cs", "eastAsia", "asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme", "hint"):
                if attr in font_values:
                    fonts.set(f"{{{W}}}{attr}", font_values[attr])

    def _add_hyperlink_relationship(self, relationships: list[dict[str, str]], target: str) -> str:
        for rel in relationships:
            if rel["target"] == target and rel["type"] == HYPERLINK_REL_TYPE:
                return rel["id"]
        rel_id = f"rIdHyper{sum(r['type'] == HYPERLINK_REL_TYPE for r in relationships) + 1}"
        relationships.append({"id": rel_id, "target": target, "type": HYPERLINK_REL_TYPE})
        return rel_id

    def _part_xml(self, units: list[TextUnit], relationships: list[dict[str, str]]) -> bytes:
        root = Element(f"{{{W}}}hdr" if units[0].metadata.get("part") == "header" else f"{{{W}}}ftr")
        for unit in units:
            self._append_unit(root, unit, relationships)
        return tostring(root, encoding="utf-8", xml_declaration=True)

    def _notes_xml(self, units: list[TextUnit], kind: str) -> bytes:
        root_name = {"footnote": "footnotes", "endnote": "endnotes", "comment": "comments"}[kind]
        item_name = {"footnote": "footnote", "endnote": "endnote", "comment": "comment"}[kind]
        root = Element(f"{{{W}}}{root_name}")
        grouped: dict[str, list[TextUnit]] = {}
        for unit in units:
            metadata = unit.metadata or {}
            note_id = metadata.get("note_id", metadata.get("comment_id", "0"))
            grouped.setdefault(note_id, []).append(unit)
        for note_id, note_units in grouped.items():
            item = SubElement(root, f"{{{W}}}{item_name}")
            item.set(f"{{{W}}}id", note_id)
            for unit in note_units:
                self._append_unit(item, unit, [])
        return tostring(root, encoding="utf-8", xml_declaration=True)

    def _content_types(self, has_header: bool, has_footer: bool, has_numbering: bool = False, has_footnotes: bool = False, has_endnotes: bool = False, has_comments: bool = False) -> str:
        overrides = [
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        ]
        if has_header:
            overrides.append('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>')
        if has_footer:
            overrides.append('<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>')
        if has_numbering:
            overrides.append('<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>')
        if has_footnotes:
            overrides.append('<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>')
        if has_endnotes:
            overrides.append('<Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>')
        if has_comments:
            overrides.append('<Override PartName="/word/comments.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"/>')
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides) + "</Types>"
        )

    def _numbering_xml(self, units: list[TextUnit]) -> bytes:
        root = Element(f"{{{W}}}numbering")
        abstract = SubElement(root, f"{{{W}}}abstractNum")
        abstract.set(f"{{{W}}}abstractNumId", "0")
        levels = sorted({int((u.metadata or {}).get("num_level", "0")) for u in units})
        for level in levels:
            lvl = SubElement(abstract, f"{{{W}}}lvl")
            lvl.set(f"{{{W}}}ilvl", str(level))
            fmt = SubElement(lvl, f"{{{W}}}numFmt")
            fmt.set(f"{{{W}}}val", "decimal")
            text = SubElement(lvl, f"{{{W}}}lvlText")
            text.set(f"{{{W}}}val", "%" + str(level + 1) + ".")
        for num_id in sorted({int((u.metadata or {}).get("num_id", "0")) for u in units}):
            num = SubElement(root, f"{{{W}}}num")
            num.set(f"{{{W}}}numId", str(num_id))
            abstract_id = SubElement(num, f"{{{W}}}abstractNumId")
            abstract_id.set(f"{{{W}}}val", "0")
        return tostring(root, encoding="utf-8", xml_declaration=True)

    def _rels(self) -> str:
        return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'

    def _document_rels(self, relationships: list[dict[str, str]]) -> str:
        items = [
            f'<Relationship Id="{rel["id"]}" Type="{rel["type"]}" Target="{rel["target"]}"'
            + (' TargetMode="External"/>' if rel["type"] == HYPERLINK_REL_TYPE else '/>')
            for rel in relationships
        ]
        return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(items) + "</Relationships>"
