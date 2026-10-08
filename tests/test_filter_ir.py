import pytest

from filter_ir.model.filter import FilterIR, FilterIRValidationError


def test_filter_ir_describes_markdown_filter():
    ir = FilterIR(
        name="markdown",
        version="1",
        mime_types=("text/markdown",),
        extensions=(".md", ".markdown"),
        features=("text_units", "inline_codes", "skeleton"),
    )

    assert ir.name == "markdown"
    assert ir.mime_types == ("text/markdown",)
    assert ".md" in ir.extensions


def test_filter_ir_rejects_empty_name():
    with pytest.raises(FilterIRValidationError):
        FilterIR(
            name="",
            version="1",
            mime_types=("text/markdown",),
            extensions=(".md",),
            features=("text_units",),
        )


def test_filter_ir_rejects_extension_without_dot():
    with pytest.raises(FilterIRValidationError):
        FilterIR(
            name="markdown",
            version="1",
            mime_types=("text/markdown",),
            extensions=("md",),
            features=("text_units",),
        )



def test_filter_ir_models_parameters_and_token_rules():
    from filter_ir.model.filter import ParameterRule, TokenRule

    ir = FilterIR(
        name="markdown",
        version="okapi-source",
        mime_types=("text/markdown",),
        extensions=(".md", ".markdown"),
        features=("text_units", "inline_codes", "skeleton"),
        parameters=("translateUrls",),
        parameter_rules=(ParameterRule("translateUrls", "boolean", False),),
        token_rules=(
            TokenRule("LINK", "link", "paired", True),
            TokenRule("CODE", "CODE", "isolated", False),
        ),
    )
    assert ir.parameter_rules[0].default is False
    assert ir.token_rules[0].code_type == "link"
    assert ir.token_rules[1].tag_strategy == "isolated"


def test_filter_ir_rejects_duplicate_parameter_rules():
    from filter_ir.model.filter import ParameterRule

    with pytest.raises(FilterIRValidationError):
        FilterIR(
            name="markdown",
            version="1",
            mime_types=("text/markdown",),
            extensions=(".md",),
            features=("text_units",),
            parameter_rules=(
                ParameterRule("translateUrls", "boolean", False),
                ParameterRule("translateUrls", "boolean", True),
            ),
        )


def test_filter_ir_rejects_invalid_token_rule_strategy():
    from filter_ir.model.filter import TokenRule

    with pytest.raises(FilterIRValidationError):
        FilterIR(
            name="markdown",
            version="1",
            mime_types=("text/markdown",),
            extensions=(".md",),
            features=("text_units",),
            token_rules=(TokenRule("LINK", "link", "unknown", True),),
        )



def test_filter_ir_json_parser_and_normalizer_round_trip():
    from filter_ir.parser.json_parser import FilterIRJsonParser
    from filter_ir.normalizer.normalizer import FilterIRNormalizer

    payload = {
        "name": "markdown",
        "version": "1",
        "mime_types": ["text/markdown"],
        "extensions": [".md"],
        "features": ["text_units"],
        "parameters": ["translateUrls"],
        "parameter_rules": [{"name": "translateUrls", "value_type": "boolean", "default": False}],
        "token_rules": [{"token_type": "LINK", "code_type": "link", "tag_strategy": "paired", "translatable": True}],
    }
    ir = FilterIRJsonParser().parse(payload)
    normalized = FilterIRNormalizer().normalize(ir)
    assert normalized["parameter_rules"][0]["name"] == "translateUrls"
    assert normalized["token_rules"][0]["tag_strategy"] == "paired"
