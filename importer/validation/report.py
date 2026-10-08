from __future__ import annotations
from dataclasses import dataclass
from filter_ir.model.filter import FilterIR

@dataclass(frozen=True, slots=True)
class AdapterReport:
    required_features: tuple[str, ...]

    @classmethod
    def from_ir(cls, ir: FilterIR) -> 'AdapterReport':
        known = {'protected', 'tables', 'inline_code', 'text'}
        return cls(tuple(sorted(feature for feature in ir.features if feature in known and feature != 'text')))
