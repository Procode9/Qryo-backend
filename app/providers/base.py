# app/providers/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseProvider(ABC):
    """
    All providers MUST implement this interface.
    """

    name: str

    @abstractmethod
    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a job and returns result dict.
        Must raise Exception on failure.
        """
        raise NotImplementedError