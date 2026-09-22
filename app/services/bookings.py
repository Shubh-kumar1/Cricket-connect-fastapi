from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.models.session import SessionModel
from app.models.user import User


def create_booking(db: Session, player: User, session_id: int) -> Booking:
    # Lock the session row so concurrent transactions serialize capacity decisions.
    session = db.scalar(select(SessionModel).where(SessionModel.id == session_id).with_for_update())
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    existing = db.scalar(
        select(Booking).where(Booking.session_id == session_id, Booking.player_id == player.id)
    )
    if existing and existing.status != BookingStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Player already has a booking")
    active_count = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.session_id == session_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        )
    )
    if active_count >= session.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session is full")
    if existing:
        existing.status = BookingStatus.PENDING
        db.commit()
        db.refresh(existing)
        return existing
    booking = Booking(session_id=session_id, player_id=player.id, status=BookingStatus.PENDING)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def list_player_bookings(db: Session, player: User) -> list[Booking]:
    return list(db.scalars(select(Booking).where(Booking.player_id == player.id).order_by(Booking.created_at.desc())))


def list_provider_bookings(db: Session, provider_id: int) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .join(SessionModel)
            .where(SessionModel.provider_id == provider_id)
            .order_by(Booking.created_at.desc())
        )
    )


def update_provider_booking(
    db: Session, provider_id: int, booking_id: int, status_value: BookingStatus
) -> Booking:
    booking = db.scalar(
        select(Booking)
        .join(SessionModel)
        .where(Booking.id == booking_id, SessionModel.provider_id == provider_id)
        .with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    booking.status = status_value
    db.commit()
    db.refresh(booking)
    return booking

