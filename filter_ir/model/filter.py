from __future__ import annotations

from dataclasses import dataclass


class FilterIRValidationError(ValueError):
    """Błąd walidacji formalnego opisu filtra."""


@dataclass(frozen=True, slots=True)
class ParameterRule:
    name: str
    value_type: str
    default: object

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise FilterIRValidationError("Nazwa parametru nie może być pusta.")
        if self.value_type not in {"boolean", "string", "integer", "pattern"}:
            raise FilterIRValidationError("Nieobsługiwany typ parametru.")


@dataclass(frozen=True, slots=True)
class TokenRule:
    token_type: str
    code_type: str
    tag_strategy: str
    translatable: bool

    def __post_init__(self) -> None:
        if not self.token_type.strip() or not self.code_type.strip():
            raise FilterIRValidationError("Reguła tokenu musi mieć typ tokenu i kodu.")
        if self.tag_strategy not in {"isolated", "paired", "document_part", "text"}:
            raise FilterIRValidationError("Nieobsługiwana strategia tagu tokenu.")


@dataclass(frozen=True, slots=True)
class FilterIR:
    name: str
    version: str
    mime_types: tuple[str, ...]
    extensions: tuple[str, ...]
    features: tuple[str, ...]
    parameters: tuple[str, ...] = ()
    parameter_rules: tuple[ParameterRule, ...] = ()
    token_rules: tuple[TokenRule, ...] = ()
    superclass: str | None = None
    lifecycle_methods: tuple[str, ...] = ()
    framework_contract: str | None = None
    entry_class: str | None = None
    used_parameters: tuple[str, ...] = ()
    java_evidence: object | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise FilterIRValidationError("Nazwa filtra nie może być pusta.")
        if not self.version.strip():
            raise FilterIRValidationError("Wersja filtra nie może być pusta.")
        if not self.mime_types:
            raise FilterIRValidationError("Filtr musi mieć co najmniej jeden typ MIME.")
        if not self.extensions:
            raise FilterIRValidationError("Filtr musi mieć co najmniej jedno rozszerzenie.")
        if any(not extension.startswith(".") for extension in self.extensions):
            raise FilterIRValidationError("Każde rozszerzenie musi zaczynać się od kropki.")
        if not self.features:
            raise FilterIRValidationError("Filtr musi deklarować co najmniej jedną cechę.")
        parameter_names = [rule.name for rule in self.parameter_rules]
        if len(parameter_names) != len(set(parameter_names)):
            raise FilterIRValidationError("Reguły parametrów nie mogą się powtarzać.")
        if self.parameters and any(rule.name not in self.parameters for rule in self.parameter_rules):
            raise FilterIRValidationError("Każda reguła parametru musi być zadeklarowana w parameters.")
