import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, func, select

from app.database import SessionLocal
from app.models import Booking, BookingStatus, SessionModel, Sport, User, UserRole, Venue, ProviderProfile
from app.services.bookings import create_booking
from app.security import hash_password


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL", "").startswith("postgresql"),
    reason="Concurrency integration test requires PostgreSQL",
)


def test_concurrent_bookings_never_exceed_capacity():
    with SessionLocal.begin() as db:
        db.execute(delete(Booking))
        db.execute(delete(SessionModel))
        db.execute(delete(Venue))
        db.execute(delete(ProviderProfile))
        db.execute(delete(User).where(User.email.like("capacity-test-%")))
        db.execute(delete(User).where(User.email == "capacity-test-provider@example.com"))
        provider_user = User(
            email="capacity-test-provider@example.com",
            full_name="Capacity Provider",
            password_hash=hash_password("password123"),
            role=UserRole.PROVIDER,
        )
        db.add(provider_user)
        db.flush()
        provider = ProviderProfile(user_id=provider_user.id, business_name="Capacity Test")
        db.add(provider)
        sport = db.scalar(select(Sport).where(Sport.name == "Cricket"))
        if sport is None:
            sport = Sport(name="Cricket")
            db.add(sport)
            db.flush()
        venue = Venue(provider_id=provider.id, name="Test Ground", address="1 Test Road", city="Test City")
        db.add(venue)
        db.flush()
        session = SessionModel(
            provider_id=provider.id,
            venue_id=venue.id,
            sport_id=sport.id,
            title="Capacity test",
            starts_at=datetime(2030, 1, 1, 10, tzinfo=timezone.utc),
            ends_at=datetime(2030, 1, 1, 11, tzinfo=timezone.utc),
            capacity=1,
        )
        db.add(session)
        players = [
            User(
                email=f"capacity-test-{index}@example.com",
                full_name=f"Player {index}",
                password_hash=hash_password("password123"),
                role=UserRole.PLAYER,
            )
            for index in range(4)
        ]
        db.add_all(players)
        db.flush()
        session_id = session.id
        player_ids = [player.id for player in players]

    def attempt(player_id: int):
        with SessionLocal() as db:
            player = db.get(User, player_id)
            try:
                booking = create_booking(db, player, session_id)
                return booking.id
            except Exception:
                db.rollback()
                return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(attempt, player_ids))

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count(Booking.id)).where(
                Booking.session_id == session_id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            )
        )
        assert len([result for result in results if result is not None]) == 1
        assert count == 1
