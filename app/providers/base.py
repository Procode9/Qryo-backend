# app/providers/base.py
from abc import ABC, abstractmethod


class Provider(ABC):
    name: str

    @abstractmethod
    def run(self, payload: dict) -> dict:
        raise NotImplementedError