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

    # Safety limits (shots)
    if "shots" in payload:
        try:
            shots = int(payload["shots"])
        except Exception:
            shots = 256
        payload["shots"] = max(1, min(shots, settings.max_shots))

    # Real quantum disabled => always simulate
    if not settings.enable_real_quantum:
        provider = SimProvider()
        return provider.name, provider.run(payload)

    # Real enabled => route to selected provider
    if provider_key == "dwave":
        provider = DWaveProvider()
        return provider.name, provider.run(payload)

    # default fallback
    provider = SimProvider()
    return provider.name, provider.run(payload)
