from .config import settings
from .providers.sim_provider import SimProvider
from .providers.dwave_provider import DWaveProvider


def pick_provider(payload: dict) -> str:
    if settings.allow_user_provider_override:
        p = payload.get("provider")
        if isinstance(p, str) and p.strip():
            return p.strip().lower()
    return settings.default_provider.lower()


def route_job(payload: dict):
    provider_key = pick_provider(payload)

    # Safety clamp for shots
    if "shots" in payload:
        try:
            shots = int(payload["shots"])
        except Exception:
            shots = 256
        payload["shots"] = max(1, min(shots, settings.max_shots))

    # Kill-switch: if real disabled, ALWAYS simulate
    if not settings.enable_real_quantum:
        p = SimProvider()
        return p.name, p.run(payload)

    # Real enabled
    if provider_key == "dwave":
        p = DWaveProvider()
        return p.name, p.run(payload)

    # Default fallback
    p = SimProvider()
    return p.name, p.run(payload)
