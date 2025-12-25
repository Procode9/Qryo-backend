import os
from fastapi import Header, HTTPException, status

API_KEY_HEADER = "x-api-key"

# Şimdilik ENV üzerinden
VALID_API_KEYS = {
    os.getenv("QRYO_API_KEY", "demo-key-123")
}

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return x_api_key
