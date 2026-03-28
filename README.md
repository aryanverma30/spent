# Spent 💸

A self-hosted personal spending tracker. Log expenses via a Telegram bot or API,
get AI-powered categorization, and visualize your spending with charts and a home-screen widget.

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────┐
│  Telegram Bot   │──────▶ │   FastAPI Backend     │──────▶ │ PostgreSQL  │
│  (bot/)         │        │   (backend/)          │        │  Database   │
└─────────────────┘        └──────────┬───────────┘        └─────────────┘
                                       │
                           ┌──────────▼───────────┐
                           │  Scriptable Widget   │
                           │  (widget/spent.js)   │
                           └──────────────────────┘
```

**Data flow:**
1. You send a message like `12 chipotle` to the Telegram bot
2. The bot calls `POST /api/v1/transactions` with the parsed data
3. The backend uses Claude AI to categorize the expense and stores it in PostgreSQL
4. The Scriptable widget polls `GET /api/v1/summary` and renders a donut chart on your iPhone

---

## Tech Stack

| Layer       | Technology                          | Why                                      |
|-------------|-------------------------------------|------------------------------------------|
| API         | FastAPI (Python 3.11+)              | Fast, async, auto-generates Swagger docs |
| Database    | PostgreSQL 15                       | Reliable, free via Docker locally        |
| ORM         | SQLAlchemy 2.0 (async)              | Type-safe, async-native query builder    |
| Migrations  | Alembic                             | Version-controlled schema changes        |
| Validation  | Pydantic v2                         | Fast request/response parsing            |
| AI          | Anthropic Claude API                | Natural language → category inference    |
| Bot         | python-telegram-bot                 | Telegram interface for expense input     |
| Widget      | Scriptable (JavaScript)             | iOS home-screen widget                   |
| Containers  | Docker + Docker Compose             | Reproducible local dev environment       |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- Python 3.11+ (for running scripts outside Docker if needed)
- [GitHub CLI](https://cli.github.com/) (`gh`) — optional, for repo management
- An [Anthropic API key](https://console.anthropic.com/) — for AI categorization (Phase 3)
- A Telegram bot token — for the bot interface (Phase 2)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/spent.git
cd spent

# 2. Set up environment variables
cp .env.example .env
# Open .env and fill in your DATABASE_URL, ANTHROPIC_API_KEY, etc.

# 3. Start all services
docker-compose up --build

# 4. Run database migrations (in a new terminal tab)
docker-compose exec backend alembic upgrade head

# 5. Open the interactive API docs
open http://localhost:8000/docs
```

---

## API Reference (Phase 1)

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint         | Description                              |
|--------|------------------|------------------------------------------|
| POST   | `/transactions`  | Create a new transaction                 |
| GET    | `/transactions`  | List transactions (paginated)            |
| GET    | `/summary`       | Spending summary by category *(stub)*    |
| GET    | `/trends`        | Spending trends over time *(stub)*       |
| GET    | `/insights`      | AI-generated insights *(stub)*           |

### POST /transactions — Request body

```json
{
  "amount": 12.00,
  "merchant": "Chipotle",
  "category": "food",
  "raw_input": "12 chipotle bowl",
  "ai_confidence": 0.95,
  "note": "lunch"
}
```

### GET /transactions — Query params

| Param      | Type    | Default | Description                  |
|------------|---------|---------|------------------------------|
| `limit`    | integer | 10      | Number of results to return  |
| `offset`   | integer | 0       | Pagination offset            |
| `category` | string  | —       | Filter by category           |

---

## Project Structure

```
spent/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── main.py          # App entry point, router wiring
│   │   ├── config.py        # Environment variable settings
│   │   ├── routes/          # API endpoint handlers
│   │   ├── models/          # SQLAlchemy ORM models + Pydantic schemas
│   │   └── services/        # Business logic (db, ai, charts)
│   ├── alembic/      # Database migration scripts
│   └── Dockerfile
├── bot/              # Telegram bot (Phase 2)
├── widget/           # Scriptable iOS widget (Phase 4)
├── docker-compose.yml
├── .env.example
└── CLAUDE.md         # AI assistant conventions for this project
```

---

## Phase Roadmap

| Phase | Focus                            | Status      |
|-------|----------------------------------|-------------|
| 1     | FastAPI + PostgreSQL backend     | ✅ Current  |
| 2     | Telegram bot for expense input   | 🔜 Next     |
| 3     | AI categorization via Claude     | 🔜 Planned  |
| 4     | Scriptable iOS widget            | 🔜 Planned  |

---

## Development Notes

- All migrations live in `backend/alembic/versions/` — commit them like code
- Never commit `.env` — use `.env.example` as the template
- The Swagger UI at `/docs` is your best friend for testing endpoints
- See `CLAUDE.md` for conventions when working with AI coding assistants
