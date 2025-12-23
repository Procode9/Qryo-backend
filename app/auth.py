from fastapi import Header, HTTPException

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> str:
    if not x_api_key or not x_api_key.strip():
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    return x_api_key.strip()
