from .base import QuantumProvider

class DWaveProvider(QuantumProvider):
    """
    Adapter skeleton.
    We keep it dependency-free by default.
    If you later want real runs, we’ll install dwave-ocean-sdk and implement run().
    """
    name = "dwave"

    def run(self, payload: dict) -> dict:
        # Placeholder: implemented in Step 5 (real execution)
        return {
            "backend": self.name,
            "note": "D-Wave adapter is wired, but real execution is not enabled yet."
        }
