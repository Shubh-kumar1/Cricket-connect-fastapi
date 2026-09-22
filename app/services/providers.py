from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.provider import ProviderProfile
from app.models.user import User
from app.schemas.provider import ProviderProfileCreate


def create_or_update_profile(db: Session, user: User, data: ProviderProfileCreate) -> ProviderProfile:
    profile = user.provider_profile
    if profile is None:
        profile = ProviderProfile(user_id=user.id, **data.model_dump())
        db.add(profile)
    else:
        for key, value in data.model_dump().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


def get_profile(db: Session, provider_id: int) -> ProviderProfile:
    profile = db.get(ProviderProfile, provider_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider profile not found")
    return profile


def delete_profile(db: Session, user: User) -> None:
    profile = user.provider_profile
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider profile not found")
    db.delete(profile)
    db.commit()
