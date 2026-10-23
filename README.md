# Cricket Connect Backend - Phase 0

FastAPI backend for connecting players with provider-created cricket and sports sessions. Phase 0 uses a modular Router -> Service -> SQLAlchemy/Database architecture.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Create the database:

```powershell
psql -U postgres
CREATE DATABASE cricket_connect;
\q
```

Set `DATABASE_URL` and `JWT_SECRET_KEY` in `.env`.

## Migrations and seed data

```powershell
alembic upgrade head
python -m scripts.seed
```

The migration seeds Cricket, Football, Badminton, and Tennis. The seed command is idempotent and can be run again safely.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## AI assistant and RAG

The authenticated React chat widget calls `POST /api/v1/chat` using the existing bearer token. The FastAPI service retrieves relevant Markdown chunks from a persisted FAISS cosine-similarity index, adds current public session or venue records directly from PostgreSQL when relevant, and uses Google's Gemini API to answer only from that context. Responses contain source references. Unsupported questions receive a fixed fallback instead of an ungrounded answer. The assistant does not retrieve individual bookings or user profiles and cannot create or modify bookings.

Knowledge sources live in `knowledge/`. They must contain verified Cricket Connect guidance; retrieved text is treated as reference data, not instructions. Rebuild the index after adding or editing documents:

```bash
python -m scripts.ingest_knowledge
```

Ingestion chunks Markdown with a 700-character target and 100-character overlap, requests embeddings using `EMBEDDING_MODEL`, and writes a FAISS index plus chunk metadata under `CHAT_INDEX_DIR`. It does not call the chat-generation model. The index is ignored by Git and is not rebuilt during chat requests. Re-run ingestion after changing the embedding model. The index directory must be present on each deployed API instance.

The backend uses Google's official `google-genai` SDK. No provider key is sent to the browser. Configure these backend environment variables in `.env` (or the deployment environment):

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | empty | Google AI Studio key; preferred credential variable |
| `GOOGLE_API_KEY` | empty | Also accepted as a Google key variable |
| `LLM_API_KEY` | empty | Legacy fallback so existing deployments can keep their key name |
| `LLM_MODEL` | `gemini-2.5-flash` | Gemini generation model, used only for chat |
| `EMBEDDING_MODEL` | `gemini-embedding-001` | Gemini embedding model, used by ingestion and chat retrieval |
| `LLM_TIMEOUT_SECONDS` | `20` | Gemini request timeout |
| `CHAT_INDEX_DIR` | `data/chat_index` | Persisted FAISS index and metadata directory |

Install the additional RAG dependencies through the existing requirements file:

```bash
python -m pip install -r requirements.txt
```

Validate the key and confirm both configured models are listed as available to the API account:

```bash
python -m scripts.check_gemini
```

The check prints model names and sanitized errors only; it never prints the key. After setting one of the accepted key variables, run the check and ingestion command, then start the API as described above. `POST /api/v1/chat` requires an authenticated player or provider account. The request accepts a message up to 2,000 characters and at most eight history entries; the UI does not show the widget on login or registration pages.

Chat tests mock paid provider requests and use a temporary SQLite database:

```bash
pytest tests/test_chat.py
```

Known limitations: generation and embeddings require a configured Google AI Studio/Gemini API key; only currently stored platform facts are indexed; venue facilities and prices are not in the database and therefore cannot be answered; the initial live-data intent detection is keyword-based; model availability and deployment persistence must be configured by the operator.

## Frontend deployment

Set the Vercel build environment variable `VITE_API_URL` to the Render API origin, for example `https://<your-render-service>.onrender.com`. The frontend appends `/api/v1` automatically. Without this setting, production builds use the same-origin `/api/v1` path, which only works locally through the Vite development proxy. Keep the deployed frontend origin in the API CORS allowlist in `app/main.py`.

## Tests

```powershell
pytest
```

`tests/test_booking_concurrency.py` is an integration test using PostgreSQL row locks. It requires a dedicated database named `cricket_connect_test`; it does not use `DATABASE_URL`, skip when PostgreSQL is unavailable, or delete shared records. Each run creates and removes only its own randomly named schema inside that test database.

Start the isolated test PostgreSQL service and run the concurrency test:

```bash
docker compose -p cricket-connect-tests -f compose.test.yaml up -d --wait
TEST_DATABASE_URL=postgresql+psycopg://cricket_test:cricket_test@localhost:55432/cricket_connect_test \
  pytest tests/test_booking_concurrency.py::test_concurrent_bookings_never_exceed_capacity
```

Run the full test suite against the same isolated service:

```bash
TEST_DATABASE_URL=postgresql+psycopg://cricket_test:cricket_test@localhost:55432/cricket_connect_test pytest
```

When finished, stop the service without removing its data volume:

```bash
docker compose -p cricket-connect-tests -f compose.test.yaml down
```

The health and password tests run without a database connection.

## Database relationships

- `users` has one optional `provider_profiles` row and can own many `bookings`.
- `provider_profiles` belongs to one provider user and owns many `venues` and `sessions`.
- `sports` is a shared lookup table referenced by `sessions`.
- `venues` belongs to a provider and can host many sessions.
- `sessions` belongs to one provider, venue, and sport and has many bookings.
- `bookings` links a player to a session and has a unique `(session_id, player_id)` constraint.

## API endpoints

| Method | Endpoint | Access |
|---|---|---|
| GET | `/health` | Public |
| POST | `/api/v1/auth/register` | Public |
| POST | `/api/v1/auth/login` | Public |
| POST/GET/DELETE | `/api/v1/providers/me/profile`, `/api/v1/providers/{provider_id}/profile` | Provider / authenticated |
| GET | `/api/v1/venues` | Authenticated |
| POST | `/api/v1/venues` | Provider |
| GET | `/api/v1/venues/mine` | Provider |
| PUT/DELETE | `/api/v1/venues/{venue_id}` | Provider |
| POST/GET/PUT/DELETE | `/api/v1/sessions`, `/api/v1/sessions/mine`, `/api/v1/sessions/{session_id}` | Provider |
| GET | `/api/v1/sessions/search?sport=Cricket&city=Delhi` | Authenticated |
| POST/GET | `/api/v1/bookings`, `/api/v1/bookings/mine` | Player |
| GET/PATCH | `/api/v1/bookings/provider`, `/api/v1/bookings/{booking_id}` | Provider |
| POST | `/api/v1/chat` | Authenticated |

## Authentication

Register, then log in with email and password. Login returns a JWT bearer token. Send it as:

```text
Authorization: Bearer <access_token>
```

The token contains the user id and role. Dependencies load the user from PostgreSQL and enforce `PLAYER` or `PROVIDER` access at the router boundary.

## Example requests

Register a provider:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"provider@example.com","full_name":"A Provider","password":"password123","role":"PROVIDER"}'
```

Login:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"provider@example.com","password":"password123"}'
```

Create a provider profile:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/providers/me/profile `
  -H "Authorization: Bearer <provider-token>" -H "Content-Type: application/json" `
  -d '{"business_name":"Delhi Cricket Academy","bio":"Weekend cricket sessions","phone":"9999999999"}'
```

Create a booking as a player:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/bookings `
  -H "Authorization: Bearer <player-token>" -H "Content-Type: application/json" `
  -d '{"session_id":1}'
```

## Concurrency decision

Booking creation begins a database transaction and selects the target session with PostgreSQL `SELECT ... FOR UPDATE` through SQLAlchemy's `with_for_update()`. This serializes all capacity decisions for that session. The locked transaction counts active `PENDING` and `CONFIRMED` bookings and inserts only when the count is below capacity. The player/session unique constraint also prevents duplicate active booking records.

This is deliberately not an application-only capacity check. PostgreSQL is the source of truth for concurrent requests.

## Decisions and limitations

- Provider registration is self-service; a provider must create a profile before creating venues or sessions.
- Search uses case-insensitive exact matching for sport and city and is intentionally simple for Phase 0.
- Booking statuses remain exactly `PENDING`, `CONFIRMED`, and `CANCELLED`.
- The requested provider "mark completed" action is not implemented because the finalized Phase 0 status enum has no completion state. A completion-state representation (new enum value versus separate completion field) must be decided before adding that action.
- No cancellation endpoint is included yet; provider booking status management can set `CANCELLED`, while player cancellation policy is deferred.
- Redis, WebSockets, chat, payments, matchmaking, Elasticsearch, ML, frontend, per-sport tables, and EAV are intentionally excluded.
