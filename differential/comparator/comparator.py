from __future__ import annotations

from dataclasses import dataclass
from differential.event_normalizer.normalizer import EventNormalizer


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    equal: bool
    differences: tuple[str, ...]


class DifferentialComparator:
    def __init__(self, normalizer: EventNormalizer | None = None):
        self.normalizer = normalizer or EventNormalizer()

    def compare(self, left, right) -> ComparisonResult:
        a, b = self.normalizer.normalize(left), self.normalizer.normalize(right)
        differences = []
        if len(a) != len(b):
            differences.append(f"Liczba zdarzeń: lewa={len(a)}, prawa={len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                differences.append(f"Pozycja {i}: {x!r} != {y!r}")
        return ComparisonResult(not differences, tuple(differences))
