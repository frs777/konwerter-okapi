from __future__ import annotations

from filter_ir.model.filter import FilterIR
from importer.extraction.metadata import ExtractedFilter


def filter_ir_from_extracted(extracted: ExtractedFilter) -> FilterIR:
    m = extracted.metadata
    behavior = getattr(extracted, "behavior", None)
    mime_types = (behavior.mime_type,) if behavior and behavior.mime_type else ("application/octet-stream",)
    extensions = behavior.extensions if behavior and behavior.extensions else (f".{m.name}",)
    features = behavior.features if behavior and behavior.features else ("text",)
    parameters = behavior.parameters if behavior else ()
    parameter_rules = behavior.parameter_rules if behavior else ()
    used_parameters = behavior.used_parameters if behavior else ()
    token_rules = behavior.token_rules if behavior else ()
    return FilterIR(
        name=m.name,
        version="1.0",
        mime_types=mime_types,
        extensions=extensions,
        features=features,
        parameters=parameters,
        parameter_rules=parameter_rules,
        token_rules=token_rules,
        superclass=behavior.superclass if behavior else None,
        lifecycle_methods=behavior.lifecycle_methods if behavior else (),
        framework_contract=behavior.framework_contract if behavior else None,
        entry_class=behavior.class_name if behavior else m.entry_class.rsplit(".", 1)[-1],
        used_parameters=used_parameters,
    )
