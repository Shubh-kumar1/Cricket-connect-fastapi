from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_player, require_provider
from app.models.booking import BookingStatus
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingRead, BookingStatusUpdate
from app.services.bookings import (
    create_booking,
    list_player_bookings,
    list_provider_bookings,
    update_provider_booking,
)
from app.services.providers import get_profile

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create(
    data: BookingCreate,
    db: Session = Depends(get_db),
    player: User = Depends(require_player),
):
    return create_booking(db, player, data.session_id)


@router.get("/mine", response_model=list[BookingRead])
def list_mine(db: Session = Depends(get_db), player: User = Depends(require_player)):
    return list_player_bookings(db, player)


@router.get("/provider", response_model=list[BookingRead])
def list_for_provider(db: Session = Depends(get_db), provider: User = Depends(require_provider)):
    return list_provider_bookings(db, get_profile(db, provider.provider_profile.id).id)


@router.patch("/{booking_id}", response_model=BookingRead)
def update_for_provider(
    booking_id: int,
    data: BookingStatusUpdate,
    db: Session = Depends(get_db),
    provider: User = Depends(require_provider),
):
    # COMPLETED is intentionally not exposed: the Phase 0 status enum does not define it.
    return update_provider_booking(db, provider.provider_profile.id, booking_id, data.status)

