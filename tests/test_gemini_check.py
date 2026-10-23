from types import SimpleNamespace

import pytest

from app.config import Settings
from scripts import check_gemini


def test_connectivity_check_reports_available_models_without_key(monkeypatch, capsys):
    settings = Settings(_env_file=None, gemini_api_key="never-print-this")
    monkeypatch.setattr(check_gemini, "get_settings", lambda: settings)
    monkeypatch.setattr(
        check_gemini,
        "get_gemini_api_key",
        lambda _settings: "never-print-this",
    )

    class Models:
        def list(self):
            return [
                SimpleNamespace(
                    name="models/gemini-2.5-flash",
                    supported_actions=["generateContent"],
                ),
                SimpleNamespace(
                    name="models/gemini-embedding-001",
                    supported_actions=["embedContent"],
                ),
            ]

    class FakeClient:
        models = Models()

    monkeypatch.setattr(check_gemini.genai, "Client", lambda **_kwargs: FakeClient())

    check_gemini.main()

    output = capsys.readouterr().out
    assert "Gemini connectivity succeeded" in output
    assert "gemini-2.5-flash" in output
    assert "gemini-embedding-001" in output
    assert "never-print-this" not in output


def test_connectivity_check_sanitizes_api_rejection(monkeypatch):
    settings = Settings(_env_file=None, gemini_api_key="never-print-this")
    monkeypatch.setattr(check_gemini, "get_settings", lambda: settings)
    monkeypatch.setattr(
        check_gemini,
        "get_gemini_api_key",
        lambda _settings: "never-print-this",
    )

    class Models:
        def list(self):
            raise check_gemini.genai_errors.APIError(
                code=403,
                response_json={"error": {"message": "never-print-this error details"}},
            )

    class FakeClient:
        models = Models()

    monkeypatch.setattr(check_gemini.genai, "Client", lambda **_kwargs: FakeClient())

    with pytest.raises(SystemExit) as error:
        check_gemini.main()

    assert "rejected" in str(error.value)
    assert "never-print-this" not in str(error.value)
