# app/providers/sim.py
from __future__ import annotations

import asyncio
from typing import Any, Dict

from .base import BaseProvider


class SimProvider(BaseProvider):
    name = "sim"

    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(2)

        return {
            "provider": self.name,
            "echo": payload,
            "message": "simulated quantum execution completed",
        }