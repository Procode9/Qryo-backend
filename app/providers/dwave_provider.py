from .base import QuantumProvider
from ..config import settings

class DWaveProvider(QuantumProvider):
    name = "dwave"

    def run(self, payload: dict) -> dict:
        """
        Minimal real D-Wave run.
        Uses a tiny BQM if no problem is provided.
        """
        if not settings.dwave_api_token:
            raise RuntimeError("DWAVE_API_TOKEN is not set")

        # Lazy imports (only when called)
        import dimod
        from dwave.system import DWaveSampler, EmbeddingComposite

        shots = int(payload.get("shots", 100))
        shots = max(1, min(shots, settings.max_shots))

        # Minimal default BQM (toy optimization)
        # Users can later send their own BQM via payload
        bqm = dimod.BinaryQuadraticModel(
            {"a": -1.0, "b": -1.0},
            {("a", "b"): 2.0},
            0.0,
            dimod.BINARY
        )

        sampler = EmbeddingComposite(
            DWaveSampler(token=settings.dwave_api_token)
        )
        sampleset = sampler.sample(bqm, num_reads=shots)

        best = sampleset.first
        return {
            "backend": self.name,
            "shots": shots,
            "best_sample": dict(best.sample),
            "energy": float(best.energy),
            "note": "Real D-Wave execution"
        }
