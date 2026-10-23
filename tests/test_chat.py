import asyncio
import json
from types import SimpleNamespace
from datetime import UTC, datetime, timedelta

import faiss
import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.dependencies import get_current_user
from app.main import app
from app.config import Settings, get_gemini_api_key
from app.models.booking import Booking, BookingStatus
from app.models.provider import ProviderProfile
from app.models.session import SessionModel
from app.models.sport import Sport
from app.models.user import User, UserRole
from app.models.venue import Venue
from app.services import chat as chat_service


@pytest.fixture
def chat_client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with test_session() as db:
            yield db

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, role=UserRole.PLAYER, is_active=True
    )
    try:
        with TestClient(app) as client:
            yield client, test_session
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_chat_requires_authentication():
    response = TestClient(app).post("/api/v1/chat", json={"message": "How do bookings work?"})

    assert response.status_code == 401


def test_chat_falls_back_when_no_relevant_documents_or_live_data(chat_client, monkeypatch):
    monkeypatch.setattr(chat_service, "retrieve_documents", _async_result([]))
    client, _ = chat_client

    response = client.post("/api/v1/chat", json={"message": "What is the weather on Mars?"})

    assert response.status_code == 200
    assert "couldn't find verified information" in response.json()["answer"]
    assert response.json()["sources"] == []


def test_live_session_context_uses_database_without_private_fields(chat_client, monkeypatch):
    client, session_factory = chat_client
    with session_factory() as db:
        player = User(
            email="private@example.com",
            full_name="Private Player",
            password_hash="not-a-real-password",
            role=UserRole.PLAYER,
        )
        provider_user = User(
            email="provider@example.com",
            full_name="Provider",
            password_hash="not-a-real-password",
            role=UserRole.PROVIDER,
        )
        db.add_all([player, provider_user])
        db.flush()
        provider = ProviderProfile(user_id=provider_user.id, business_name="Community Cricket")
        sport = Sport(name="Cricket")
        db.add_all([provider, sport])
        db.flush()
        venue = Venue(
            provider_id=provider.id,
            name="Central Ground",
            address="1 Main Road",
            city="Delhi",
        )
        db.add(venue)
        db.flush()
        session = SessionModel(
            provider_id=provider.id,
            venue_id=venue.id,
            sport_id=sport.id,
            title="Saturday Cricket",
            description="Friendly match",
            starts_at=datetime.now(UTC) + timedelta(days=2),
            ends_at=datetime.now(UTC) + timedelta(days=2, hours=2),
            capacity=10,
        )
        db.add(session)
        db.flush()
        db.add(Booking(session_id=session.id, player_id=player.id, status=BookingStatus.PENDING))
        db.commit()
        session_id = session.id

    monkeypatch.setattr(chat_service, "retrieve_documents", _async_result([]))
    captured: dict[str, object] = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="One session has nine places remaining.")

    class FakeClient:
        models = FakeModels()

        def close(self):
            pass

    monkeypatch.setattr(
        chat_service,
        "_gemini_client",
        lambda _settings: FakeClient(),
    )
    response = client.post(
        "/api/v1/chat",
        json={"message": "Show upcoming sessions and venues"},
    )

    assert response.status_code == 200
    assert "Saturday Cricket" in str(captured["contents"])
    assert "remaining places 9" in str(captured["contents"])
    assert "Central Ground" in str(captured["contents"])
    assert "private@example.com" not in str(captured["contents"])
    assert response.json()["sources"] == [
        {"title": "Saturday Cricket", "type": "session", "reference": f"session:{session_id}"},
        {"title": "Central Ground", "type": "venue", "reference": "venue:1"},
    ]


def test_chat_request_limits_and_empty_message(chat_client):
    client, _ = chat_client

    empty = client.post("/api/v1/chat", json={"message": "  "})
    too_long = client.post("/api/v1/chat", json={"message": "x" * 2001})
    too_many_history = client.post(
        "/api/v1/chat",
        json={
            "message": "How do bookings work?",
            "history": [{"role": "user", "content": "hello"}] * 9,
        },
    )

    assert empty.status_code == 422
    assert too_long.status_code == 422
    assert too_many_history.status_code == 422


def test_missing_provider_credentials_are_reported_safely(monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "get_settings",
        lambda: Settings(llm_api_key="", gemini_api_key=""),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(chat_service.create_embedding("test question"))

    assert error.value.status_code == 503
    assert "GEMINI_API_KEY" in error.value.detail


def test_provider_timeout_is_a_gateway_timeout(monkeypatch):
    class TimeoutModels:
        def embed_content(self, **_kwargs):
            raise chat_service.httpx.TimeoutException("timeout")

    class TimeoutClient:
        models = TimeoutModels()

        def close(self):
            pass

    monkeypatch.setattr(chat_service, "_gemini_client", lambda _settings: TimeoutClient())
    with pytest.raises(HTTPException) as error:
        asyncio.run(chat_service.create_embedding("query"))

    assert error.value.status_code == 504
    assert "Gemini timed out" in error.value.detail


def test_provider_rejected_credentials_are_reported_safely(monkeypatch):
    class RejectedModels:
        def embed_content(self, **_kwargs):
            raise chat_service.genai_errors.APIError(
                code=403,
                response_json={"error": {"message": "private provider details"}},
            )

    class RejectedClient:
        models = RejectedModels()

        def close(self):
            pass

    monkeypatch.setattr(chat_service, "_gemini_client", lambda _settings: RejectedClient())
    with pytest.raises(HTTPException) as error:
        asyncio.run(chat_service.create_embedding("query"))

    assert error.value.status_code == 503
    assert "Gemini rejected" in error.value.detail
    assert "private provider details" not in error.value.detail


def test_gemini_key_variable_precedence_and_legacy_compatibility():
    preferred = Settings(
        _env_file=None,
        GEMINI_API_KEY="gemini-key",
        GOOGLE_API_KEY="google-key",
        LLM_API_KEY="legacy-key",
    )
    google = Settings(_env_file=None, GOOGLE_API_KEY="google-key")
    legacy = Settings(_env_file=None, llm_api_key="legacy-key")

    assert get_gemini_api_key(preferred) == "gemini-key"
    assert get_gemini_api_key(google) == "google-key"
    assert get_gemini_api_key(legacy) == "legacy-key"


def test_faiss_retrieval_returns_relevant_chunks_and_sources(tmp_path, monkeypatch):
    index = faiss.IndexFlatIP(2)
    index.add(np.asarray([[1, 0], [0, 1]], dtype=np.float32))
    index_path = tmp_path / "index.faiss"
    chunks_path = tmp_path / "chunks.json"
    faiss.write_index(index, str(index_path))
    chunks_path.write_text(
        json.dumps(
            [
                {"content": "Session search supports a city filter.", "source": "sessions.md"},
                {"content": "The venue has an address.", "source": "venues.md"},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(chat_service, "_index_files", lambda: (index_path, chunks_path))
    monkeypatch.setattr(
        chat_service,
        "create_embedding",
        _async_result(np.asarray([1, 0], dtype=np.float32)),
    )

    results = asyncio.run(chat_service.retrieve_documents("find a session"))

    assert results == [
        {"content": "Session search supports a city filter.", "source": "sessions.md"}
    ]


def test_missing_knowledge_index_is_reported_as_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(
        chat_service,
        "_index_files",
        lambda: (tmp_path / "index.faiss", tmp_path / "chunks.json"),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(chat_service.retrieve_documents("How do bookings work?"))

    assert error.value.status_code == 503
    assert "not initialized" in error.value.detail


def test_document_chunking_has_overlap_and_validates_parameters():
    chunks = chat_service.split_document("abcdefghij", chunk_size=6, overlap=2)

    assert chunks == ["abcdef", "efghij"]
    with pytest.raises(ValueError):
        chat_service.split_document("text", chunk_size=5, overlap=5)


def _async_result(value):
    async def result(*_args, **_kwargs):
        return value

    return result
