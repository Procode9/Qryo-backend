import random
from .base import QuantumProvider

class SimProvider(QuantumProvider):
    name = "simulated"

    def run(self, payload: dict) -> dict:
        return {
            "solution": {
                "x": random.choice([0, 1]),
                "y": random.choice([0, 1])
            },
            "energy": round(random.uniform(-1.5, 0.5), 4),
            "note": "Simulated quantum run"
        }
