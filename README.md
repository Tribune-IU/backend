# Tribune — Backend API

FastAPI backend for Tribune. Handles users, documents, alerts, AI agent calls, and seed data ingestion.

## Tech Stack

- **Python 3.12**, **FastAPI**, **Motor** (async MongoDB), **Pydantic v2**
- **uv** for dependency management
- **MongoDB**
- AI agent calls proxied to the Tribune Agents ADK server

## Getting Started

### Prerequisites

- Python >= 3.11
- MongoDB running locally or via Atlas URI
- [uv](https://docs.astral.sh/uv/) installed
- Tribune Agents ADK server running at `http://localhost:8080` (see `agents/`)

### Install and run

```bash
uv sync
uv run uvicorn app.main:app --reload
```

API available at [http://localhost:8000](http://localhost:8000).
Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).
Health check at [http://localhost:8000/healthz](http://localhost:8000/healthz).

### Environment Variables

Create a `.env` file:

```env
MONGO_SRV=mongodb+srv://<user>:<pass>@cluster.mongodb.net/
AGENTS_BASE_URL=http://127.0.0.1:8080
```


| Variable          | Default                     | Description                       |
| ----------------- | --------------------------- | --------------------------------- |
| `MONGO_SRV`       | `mongodb://localhost:27017` | MongoDB connection URI            |
| `AGENTS_BASE_URL` | `http://127.0.0.1:8080`     | Tribune ADK agent server base URL |


### Docker

```bash
docker build -t tribune-backend .
docker run -p 8000:8000 -e MONGO_SRV="mongodb+srv://..." tribune-backend
```

## Project Structure

```
app/
  api/v1/          # Route handlers (users, documents, alerts)
  models/          # MongoDB document models
  schemas/v1.py    # Pydantic request/response schemas
  services/
    agents.py      # ADK agent call wrappers
    seed_loader.py # Seed data ingestion
  config.py        # Settings (pydantic-settings)
  db/              # Index definitions
data/
  seed/            # JSON seed files (sourced from real Bloomington PDFs)
```

## API Overview


| Method | Path                               | Description                                  |
| ------ | ---------------------------------- | -------------------------------------------- |
| `POST` | `/v1/users`                        | Create or update a user                      |
| `GET`  | `/v1/users/{id}`                   | Get user profile                             |
| `GET`  | `/v1/users/{id}/alerts`            | Get personalized alerts for a user           |
| `GET`  | `/v1/documents`                    | List all documents                           |
| `GET`  | `/v1/documents/{id}`               | Get document detail                          |
| `POST` | `/v1/documents/{id}/chat`          | Q&A chat with a document                     |
| `POST` | `/v1/documents/{id}/draft-comment` | Draft a personalized public comment          |
| `POST` | `/v1/documents/{id}/relevance`     | Get/generate "why it affects you" for a user |
| `POST` | `/v1/documents/{id}/save-progress` | Persist chat history and draft state         |


## Seed Data

On startup, the backend automatically seeds the database from `data/seed/*.json`. Each document references the source PDF packet it was extracted from via `pdf_url`. Raw PDFs live in `client/public/`.

## Secrets

Use `vault.py` to manage encrypted environment variables:

```bash
uv run vault.py lock    # encrypt .env -> .env.enc
uv run vault.py unlock  # decrypt .env.enc -> .env
```

Never commit `.env` or `.vault.key`.