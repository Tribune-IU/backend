# Tribune API Backend

This is the backend repository for the Tribune application. It is built using FastAPI and MongoDB.

## Features

- Framework: [FastAPI](https://fastapi.tiangolo.com/) for high-performance REST APIs.
- Database: [Motor](https://motor.readthedocs.io/en/stable/) for asynchronous MongoDB operations.
- Secret Management: Included `vault.py` utility for securely storing encrypted environment variables (`.env.enc`).
- Package Management: Uses `uv` for fast dependency resolution.

## Getting Started

### Prerequisites

- Python >= 3.11
- MongoDB running locally or accessible via URI
- [uv](https://docs.astral.sh/uv/) installed

### Installation

1. Sync the dependencies:

   ```bash
   uv sync
   ```

2. Setup Environment Variables:
   If you have the encrypted secrets (`.env.enc`) and the vault key (`.vault.key`), you can decrypt your environment:
   ```bash
   uv run vault.py unlock
   ```
   _Note: Never commit `.vault.key` or `.env` to version control._

### Running the Server

Start the application with Uvicorn in development mode:

```bash
uv run uvicorn app.main:app --reload
```

The API will be accessible at [http://127.0.0.1:8000](http://127.0.0.1:8000).
Check out the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
