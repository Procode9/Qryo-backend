from sqlalchemy.orm import Session
from fastapi import HTTPException
from .models import User

JOB_COST_CREDITS = 1

def get_or_create_user(db: Session, api_key: str) -> User:
    user = db.query(User).filter(User.api_key == api_key).first()
    if user:
        return user

    # First-time user: give small free credits (MVP growth hack)
    user = User(api_key=api_key, credits=5)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def charge_credits(db: Session, api_key: str, cost: int = JOB_COST_CREDITS) -> int:
    user = get_or_create_user(db, api_key)

    if user.credits < cost:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Needed={cost}, available={user.credits}"
        )

    user.credits -= cost
    db.commit()
    return user.credits
