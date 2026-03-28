# CLAUDE.md — AI Assistant Conventions for Spent

This file tells AI coding assistants (Claude Code, GitHub Copilot, etc.) how to
work effectively in this repository. Read this before making any changes.

---

## Project Summary

**Spent** is a self-hosted personal budget tracker with:
- A **FastAPI** backend (Python 3.11, SQLAlchemy 2.0 async, PostgreSQL 15)
- A **Telegram bot** for natural-language expense input
- **Claude AI** for automatic expense categorization
- A **Scriptable** JavaScript widget for the iOS home screen

---

## Tech Stack Quick Reference

| Concern          | Tool / Library              | Version  |
|------------------|-----------------------------|----------|
| Web framework    | FastAPI                     | 0.111.x  |
| ORM              | SQLAlchemy (async)          | 2.0.x    |
| Migrations       | Alembic                     | 1.13.x   |
| Validation       | Pydantic                    | v2       |
| Database         | PostgreSQL                  | 15       |
| Async driver     | asyncpg                     | 0.29.x   |
| Settings         | pydantic-settings           | 2.x      |
| ASGI server      | uvicorn                     | 0.29.x   |

---

## Dev Workflow

### Always use Docker Compose for local dev
```bash
docker-compose up --build        # start all services
docker-compose down              # stop and remove containers
docker-compose logs -f backend   # tail backend logs
```

### After any change to SQLAlchemy models
```bash
# Generate a new migration
docker-compose exec backend alembic revision --autogenerate -m "describe the change"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Check current migration state
docker-compose exec backend alembic current
```

### Running the app outside Docker (rarely needed)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix       | When to use                                       |
|--------------|---------------------------------------------------|
| `feat:`      | New endpoint, new feature, new model field        |
| `fix:`       | Bug fix                                           |
| `chore:`     | Tooling, config, dependency updates, scaffolding  |
| `docs:`      | README, CLAUDE.md, docstrings, comments           |
| `refactor:`  | Code restructure without behavior change          |
| `test:`      | Adding or updating tests                          |
| `migration:` | New Alembic migration file                        |

**Examples:**
```
feat: add GET /transactions endpoint with category filter
fix: handle null ai_confidence in TransactionResponse schema
migration: add composite index on (category, created_at)
docs: document Phase 2 bot setup in README
```

---

## Key Files Map

| File                                  | Purpose                                          |
|---------------------------------------|--------------------------------------------------|
| `backend/app/main.py`                 | FastAPI app, lifespan, router registration       |
| `backend/app/config.py`               | All env vars via pydantic-settings               |
| `backend/app/services/db.py`          | Async engine, session factory, Base class        |
| `backend/app/models/transaction.py`   | SQLAlchemy ORM model for the transactions table  |
| `backend/app/models/schemas.py`       | Pydantic request/response schemas                |
| `backend/app/routes/transactions.py`  | POST and GET /transactions endpoints             |
| `backend/alembic/env.py`              | Alembic async migration configuration            |
| `backend/alembic/versions/`           | All migration files — treat these like code      |
| `docker-compose.yml`                  | Service definitions (postgres, backend, bot)     |
| `.env.example`                        | Template for environment variables               |

---

## Coding Conventions

- **Async everywhere**: all DB calls must use `await`, all sessions via `async with`
- **Pydantic v2**: use `model_config = ConfigDict(from_attributes=True)` (not `orm_mode`)
- **No raw SQL**: always use SQLAlchemy ORM or `select()` queries
- **Dependency injection**: DB sessions via `Depends(get_session)`, never global state
- **Error handling**: raise `HTTPException` with appropriate status codes in routes
- **Type hints**: all function signatures must have type hints
- **Docstrings**: all public functions and classes must have a one-line docstring

---

## Learning Scaffold Note

Files marked with `# TODO:` blocks are **intentionally incomplete** — the user
is learning FastAPI and SQLAlchemy by filling in the implementation themselves.

**Do not fill in TODO blocks unless the user explicitly asks you to.**

When helping with TODO blocks:
1. Explain *why* the code is structured the way it is
2. Walk through the concepts involved before showing the answer
3. Suggest the user attempt it first, then offer a solution

---

## What NOT to do

- Never commit `.env` (only `.env.example` with placeholder values)
- Never use synchronous SQLAlchemy calls (`session.execute` without `await`)
- Never skip Alembic — always migrate, never use `Base.metadata.create_all()`
- Never hardcode credentials or API keys
- Never remove `TODO:` scaffold comments without the user's instruction
- Never use `@app.on_event` (deprecated) — use `lifespan` context manager

---

## Testing (Phase 2+)

Tests will live in `backend/tests/`. Use:
- `pytest` + `pytest-asyncio` for async tests
- `httpx.AsyncClient` for endpoint integration tests
- A separate test database (`spent_test`) via override of `get_session`

---

## Environment Variables

| Variable                   | Required | Description                              |
|----------------------------|----------|------------------------------------------|
| `DATABASE_URL`             | Yes      | asyncpg connection string                |
| `ANTHROPIC_API_KEY`        | Phase 3  | Claude API key for categorization        |
| `TELEGRAM_BOT_TOKEN`       | Phase 2  | Telegram bot token                       |
| `AI_CONFIDENCE_THRESHOLD`  | Phase 3  | Min confidence to accept AI category     |
| `ENVIRONMENT`              | No       | `development` or `production`            |
