from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from core.events.model import Event


class Reader(ABC):
    @abstractmethod
    def read(self, source: str) -> Iterable[Event]:
        raise NotImplementedError
