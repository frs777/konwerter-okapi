"""Capabilities advertised by a document filter backend."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FilterCapabilities:
    supports_skeleton: bool = False
    supports_inline_codes: bool = False
    supports_subdocuments: bool = False
    supports_round_trip: bool = True
