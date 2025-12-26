# app/providers/sim.py
from .base import Provider
from app.core import execute_core


class SimProvider(Provider):
    name = "sim"

    def run(self, payload: dict) -> dict:
        return execute_core(payload)