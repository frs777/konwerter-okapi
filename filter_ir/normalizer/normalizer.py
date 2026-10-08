from __future__ import annotations

from dataclasses import asdict

from filter_ir.model.filter import FilterIR


class FilterIRNormalizer:
    def normalize(self, ir: FilterIR) -> dict:
        data = asdict(ir)
        data["mime_types"] = sorted(data["mime_types"])
        data["extensions"] = sorted(data["extensions"])
        data["features"] = sorted(data["features"])
        data["parameters"] = sorted(data["parameters"])
        data["parameter_rules"] = sorted(data["parameter_rules"], key=lambda item: item["name"])
        data["token_rules"] = sorted(data["token_rules"], key=lambda item: item["token_type"])
        return data
