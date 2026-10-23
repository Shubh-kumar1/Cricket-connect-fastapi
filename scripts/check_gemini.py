import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.config import get_gemini_api_key, get_settings


def main() -> None:
    settings = get_settings()
    api_key = get_gemini_api_key(settings)
    if not api_key:
        raise SystemExit(
            "Gemini API key is missing. Set GEMINI_API_KEY, GOOGLE_API_KEY, or legacy LLM_API_KEY."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(
            timeout=int(settings.llm_timeout_seconds * 1000)
        ),
    )
    try:
        models = list(client.models.list())
    except (
        genai_errors.APIError,
        httpx.RequestError,
        OSError,
        TimeoutError,
    ) as exc:
        status_code = exc.code if isinstance(exc, genai_errors.APIError) else None
        if status_code in {401, 403}:
            raise SystemExit("Gemini rejected the configured API key.") from None
        if status_code == 429:
            raise SystemExit("Gemini API rate limit reached; retry the connectivity check later.") from None
        if status_code:
            raise SystemExit(f"Gemini model listing failed (HTTP {status_code}).") from None
        raise SystemExit("Gemini model listing failed due to a network or timeout error.") from None

    by_name = {
        model.name.rsplit("/", 1)[-1]: set(model.supported_actions or [])
        for model in models
        if model.name
    }
    checks = (
        (settings.llm_model, "generateContent"),
        (settings.embedding_model, "embedContent"),
    )
    unavailable = [
        f"{model_name} (requires {action})"
        for model_name, action in checks
        if model_name not in by_name or action not in by_name[model_name]
    ]
    if unavailable:
        print("Gemini API key authenticated, but configured model access is incomplete:")
        for model in unavailable:
            print(f"- {model}")
        raise SystemExit(1)

    print("Gemini connectivity succeeded; both configured models are available to this API key:")
    print(f"- generation: {settings.llm_model}")
    print(f"- embeddings: {settings.embedding_model}")


if __name__ == "__main__":
    main()
