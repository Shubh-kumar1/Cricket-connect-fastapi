import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import Base, normalize_database_url
from app.models import Booking, BookingStatus, SessionModel, Sport, User, UserRole, Venue, ProviderProfile
from app.services.bookings import create_booking
from app.security import hash_password


@pytest.fixture
def test_session_factory():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "TEST_DATABASE_URL must point to the dedicated cricket_connect_test PostgreSQL database. "
            "See the test instructions in README.md."
        )

    normalized_test_url = normalize_database_url(database_url)
    test_url = make_url(normalized_test_url)
    if test_url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL; this test verifies PostgreSQL row-lock behavior.")
    if test_url.database != "cricket_connect_test":
        pytest.fail("TEST_DATABASE_URL must use the dedicated cricket_connect_test database.")

    application_url = make_url(normalize_database_url(get_settings().database_url))
    if (
        test_url.host == application_url.host
        and test_url.port == application_url.port
        and test_url.database == application_url.database
    ):
        pytest.fail("TEST_DATABASE_URL must not point to the application database.")

    admin_engine = create_engine(normalized_test_url, pool_pre_ping=True)
    schema_name = f"booking_test_{uuid.uuid4().hex}"
    quoted_schema = admin_engine.dialect.identifier_preparer.quote(schema_name)
    with admin_engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {quoted_schema}"))

    test_engine = create_engine(
        normalized_test_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema_name}"},
    )
    try:
        Base.metadata.create_all(test_engine)
        yield sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {quoted_schema} CASCADE"))
        admin_engine.dispose()


def test_concurrent_bookings_never_exceed_capacity(test_session_factory):
    with test_session_factory.begin() as db:
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
        with test_session_factory() as db:
            player = db.get(User, player_id)
            try:
                booking = create_booking(db, player, session_id)
                return booking.id
            except HTTPException as error:
                db.rollback()
                if error.status_code == 409:
                    return None
                raise

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(attempt, player_ids))

    with test_session_factory() as db:
        count = db.scalar(
            select(func.count(Booking.id)).where(
                Booking.session_id == session_id,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            )
        )
        assert len([result for result in results if result is not None]) == 1
        assert count == 1
