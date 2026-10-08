from __future__ import annotations

from abc import ABC, abstractmethod

from core.events.model import Event


class Writer(ABC):
    @abstractmethod
    def write(self, event: Event) -> None:
        raise NotImplementedError
