from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_provider
from app.models.user import User
from app.schemas.provider import ProviderProfileCreate, ProviderProfileRead
from app.services.providers import create_or_update_profile, delete_profile, get_profile

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("/me/profile", response_model=ProviderProfileRead)
def upsert_profile(
    data: ProviderProfileCreate,
    db: Session = Depends(get_db),
    provider: User = Depends(require_provider),
):
    return create_or_update_profile(db, provider, data)


@router.get("/{provider_id}/profile", response_model=ProviderProfileRead)
def read_profile(provider_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_profile(db, provider_id)


@router.delete("/me/profile", status_code=status.HTTP_204_NO_CONTENT)
def remove_profile(provider: User = Depends(require_provider), db: Session = Depends(get_db)):
    delete_profile(db, provider)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
