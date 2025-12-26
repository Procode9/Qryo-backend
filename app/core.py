# app/core.py
import hashlib
import json


def execute_core(payload: dict) -> dict:
    """
    Deterministic core execution.
    Same input => same output.
    """
    normalized = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return {
        "input_hash": digest,
        "payload_size": len(normalized),
        "message": "deterministic computation complete",
    }