# providers package
# app/providers/__init__.py
from .sim import SimProvider

PROVIDERS = {
    "sim": SimProvider(),
}
