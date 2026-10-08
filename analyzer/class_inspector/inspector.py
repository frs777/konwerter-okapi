from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import zipfile


@dataclass(frozen=True, slots=True)
class MethodInspection:
    name: str
    descriptor: str
    access_flags: int


@dataclass(frozen=True, slots=True)
class ClassInspection:
    class_name: str
    super_name: str
    this_class: str
    constant_pool_count: int
    methods: tuple[MethodInspection, ...] = ()


class ClassInspector:
    def inspect_jar_class(self, jar: str | Path, class_name: str) -> ClassInspection:
        entry = class_name.replace(".", "/") + ".class"
        with zipfile.ZipFile(jar) as zf:
            data = zf.read(entry)

        if len(data) < 10:
            raise ValueError("Classfile jest zbyt krótki.")
        magic, _minor, _major, cp_count = struct.unpack(">IHHH", data[:10])
        if magic != 0xCAFEBABE:
            raise ValueError("Nieprawidłowy nagłówek classfile.")

        cp: list[object | None] = [None] * cp_count
        pos = 10
        index = 1
        while index < cp_count:
            tag = data[pos]
            pos += 1
            if tag == 1:
                length = struct.unpack_from(">H", data, pos)[0]
                pos += 2
                cp[index] = ("utf8", data[pos:pos + length].decode("utf-8"))
                pos += length
            elif tag in (3, 4):
                pos += 4
            elif tag in (5, 6):
                pos += 8
                index += 1
            elif tag in (7, 8, 16, 19, 20):
                cp[index] = (tag, struct.unpack_from(">H", data, pos)[0])
                pos += 2
            elif tag in (9, 10, 11, 12, 17, 18):
                pos += 4
            elif tag == 15:
                pos += 3
            else:
                raise ValueError(f"Nieznany tag constant pool: {tag}")
            index += 1

        _access, this_idx, super_idx = struct.unpack_from(">HHH", data, pos)
        pos += 6

        interface_count = struct.unpack_from(">H", data, pos)[0]
        pos += 2 + interface_count * 2

        field_count = struct.unpack_from(">H", data, pos)[0]
        pos += 2
        for _ in range(field_count):
            pos = self._skip_member(data, pos)

        method_count = struct.unpack_from(">H", data, pos)[0]
        pos += 2
        methods: list[MethodInspection] = []
        for _ in range(method_count):
            access_flags, name_idx, descriptor_idx = struct.unpack_from(">HHH", data, pos)
            pos += 6
            name = self._resolve_utf8(cp, name_idx)
            descriptor = self._resolve_utf8(cp, descriptor_idx)
            attribute_count = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            for _ in range(attribute_count):
                pos = self._skip_attribute(data, pos)
            methods.append(MethodInspection(name, descriptor, access_flags))

        def resolve_class(idx: int) -> str:
            ref = cp[idx]
            if not isinstance(ref, tuple):
                return str(idx)
            name_ref = ref[1]
            name_entry = cp[name_ref]
            return name_entry[1] if isinstance(name_entry, tuple) and name_entry[0] == "utf8" else str(name_ref)

        this_internal = resolve_class(this_idx)
        super_internal = resolve_class(super_idx)
        return ClassInspection(
            class_name,
            super_internal.replace("/", "."),
            this_internal,
            cp_count,
            tuple(methods),
        )

    @staticmethod
    def _resolve_utf8(cp: list[object | None], index: int) -> str:
        entry = cp[index]
        if not isinstance(entry, tuple) or entry[0] != "utf8":
            raise ValueError(f"Constant pool entry {index} nie jest UTF8.")
        return entry[1]

    @staticmethod
    def _skip_attribute(data: bytes, pos: int) -> int:
        pos += 2
        length = struct.unpack_from(">I", data, pos)[0]
        return pos + 4 + length

    def _skip_member(self, data: bytes, pos: int) -> int:
        pos += 6
        attribute_count = struct.unpack_from(">H", data, pos)[0]
        pos += 2
        for _ in range(attribute_count):
            pos = self._skip_attribute(data, pos)
        return pos
