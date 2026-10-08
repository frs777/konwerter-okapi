from __future__ import annotations
from differential.comparator.comparator import ComparisonResult

class DifferentialReport:
    def render(self, result: ComparisonResult) -> str:
        if result.equal:
            return 'Wyniki są równoważne.'
        return 'Różnice:\n' + '\n'.join(f'- {item}' for item in result.differences)
