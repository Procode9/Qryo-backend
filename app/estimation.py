from .config import settings

def estimate_cost(payload: dict) -> dict:
    """
    Returns a cost estimate WITHOUT running any job.
    """
    provider = payload.get("provider", settings.default_provider)
    shots = payload.get("shots", 256)

    try:
        shots = int(shots)
    except Exception:
        shots = 256

    shots = max(1, min(shots, settings.max_shots))

    if provider == "dwave":
        unit_cost = settings.cost_per_1000_shots_dwave
    else:
        provider = "sim"
        unit_cost = settings.cost_per_1000_shots_sim

    estimated_cost = round((shots / 1000) * unit_cost, 4)

    allowed = estimated_cost <= settings.max_estimated_cost_per_job

    return {
        "provider": provider,
        "shots": shots,
        "estimated_cost": estimated_cost,
        "currency": "USD",
        "allowed": allowed,
        "max_allowed_cost": settings.max_estimated_cost_per_job,
        "note": "Estimate only. No job executed."
    }
