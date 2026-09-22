from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_provider
from app.models.user import User
from app.schemas.venue import VenueCreate, VenueRead
from app.services.providers import get_profile
from app.services.venues import create_venue, delete_venue, list_provider_venues, list_venues, update_venue

router = APIRouter(prefix="/venues", tags=["venues"])


@router.get("", response_model=list[VenueRead])
def list_all(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_venues(db)


@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create(data: VenueCreate, db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    return create_venue(db, get_profile(db, provider_user.provider_profile.id), data)


@router.get("/mine", response_model=list[VenueRead])
def list_mine(db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    return list_provider_venues(db, get_profile(db, provider_user.provider_profile.id))


@router.put("/{venue_id}", response_model=VenueRead)
def update(
    venue_id: int,
    data: VenueCreate,
    db: Session = Depends(get_db),
    provider_user: User = Depends(require_provider),
):
    return update_venue(db, get_profile(db, provider_user.provider_profile.id), venue_id, data)


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(venue_id: int, db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    delete_venue(db, get_profile(db, provider_user.provider_profile.id), venue_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
