# app/providers/registry.py
from .sim import SimProvider
from .base import Provider


_PROVIDERS: dict[str, Provider] = {
    "sim": SimProvider(),
}


def get_provider(name: str) -> Provider:
    provider = _PROVIDERS.get(name)
    if not provider:
        raise ValueError(f"Unsupported provider: {name}")
    return provider