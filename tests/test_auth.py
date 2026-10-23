import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        with test_session() as db:
            yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_register_duplicate_login_and_restore_user(auth_client):
    details = {
        "email": "new.player@example.com",
        "full_name": "New Player",
        "password": "cricket-pass-123",
    }
    registered = auth_client.post("/api/v1/auth/register", json=details)

    assert registered.status_code == 201
    assert registered.json()["email"] == details["email"]
    assert "password_hash" not in registered.json()

    duplicate = auth_client.post(
        "/api/v1/auth/register",
        json={**details, "email": "NEW.PLAYER@example.com"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Email is already registered"

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"email": details["email"], "password": details["password"]},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    user = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert user.status_code == 200
    assert user.json()["email"] == details["email"]


def test_login_rejects_incorrect_password(auth_client):
    auth_client.post(
        "/api/v1/auth/register",
        json={
            "email": "player@example.com",
            "full_name": "Test Player",
            "password": "cricket-pass-123",
        },
    )

    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "player@example.com", "password": "incorrect-pass"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "not-an-email", "password": "some-password"},
        {"email": "", "password": ""},
    ],
)
def test_login_rejects_invalid_fields(auth_client, payload):
    response = auth_client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422


def test_current_user_rejects_invalid_token(auth_client):
    response = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


def test_login_database_failure_is_safe_and_logged(caplog):
    previous_overrides = app.dependency_overrides.copy()

    def unavailable_db():
        raise OperationalError(
            "database query failed",
            {},
            ConnectionRefusedError("connection refused"),
        )

    app.dependency_overrides[get_db] = unavailable_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "database-probe@example.com",
                    "password": "safe-probe-only",
                },
            )
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is temporarily unavailable"}
    assert "Database request failed: ConnectionRefusedError" in caplog.text
    assert "safe-probe-only" not in caplog.text
    assert "database-probe@example.com" not in caplog.text