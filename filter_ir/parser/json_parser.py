from __future__ import annotations

from filter_ir.model.filter import FilterIR, ParameterRule, TokenRule


class FilterIRJsonParser:
    def parse(self, payload: dict) -> FilterIR:
        return FilterIR(
            name=payload["name"],
            version=payload["version"],
            mime_types=tuple(payload["mime_types"]),
            extensions=tuple(payload["extensions"]),
            features=tuple(payload["features"]),
            parameters=tuple(payload.get("parameters", ())),
            parameter_rules=tuple(ParameterRule(**item) for item in payload.get("parameter_rules", ())),
            token_rules=tuple(TokenRule(**item) for item in payload.get("token_rules", ())),
            used_parameters=tuple(payload.get("used_parameters", ())),
        )
