from pathlib import Path

import pytest

from execution.contracts import DocumentRequest, ExecutionResult, TranslationUnit


def test_document_request_is_format_neutral():
    request = DocumentRequest(
        document_id="doc-1",
        input_path=Path("input.docx"),
        format="docx",
        source_locale="pl",
        target_locale="en",
    )

    assert request.format == "docx"
    assert request.filter_id is None
    assert request.filter_config_id is None


def test_translation_unit_keeps_domain_data_without_okapi_types():
    unit = TranslationUnit(
        id="u1",
        source="Witaj",
        target="Hello",
        translatable=True,
    )

    assert unit.id == "u1"
    assert unit.source == "Witaj"
    assert unit.target == "Hello"
    assert unit.translatable is True


def test_execution_result_requires_a_terminal_status():
    with pytest.raises(ValueError, match="terminal"):
        ExecutionResult(job_id="job-1", status="EXTRACTING")
