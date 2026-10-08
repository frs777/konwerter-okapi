from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RunPropertySet:
    values: dict[str, str]

    def merge(self, override: "RunPropertySet") -> "RunPropertySet":
        result = dict(self.values)
        result.update(override.values)
        return RunPropertySet(result)

    def minify(self, base: "RunPropertySet") -> "RunPropertySet":
        return RunPropertySet({k: v for k, v in self.values.items() if base.values.get(k) != v})

    def map_fonts(self, mappings: dict[str, str]) -> "RunPropertySet":
        return RunPropertySet({
            key: mappings.get(value, value) if key.startswith("font") else value
            for key, value in self.values.items()
        })
