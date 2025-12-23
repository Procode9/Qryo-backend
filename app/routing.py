from .providers.sim_provider import SimProvider
from .config import settings

def route_job(payload: dict):
    if settings.default_provider == "sim":
        provider = SimProvider()
    else:
        provider = SimProvider()

    return provider.name, provider.run(payload)
