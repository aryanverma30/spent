# Spent

A self-hosted personal finance tracker. Log expenses via a Telegram bot or the REST API, get AI-powered categorization, and visualize spending with a web dashboard and an iOS home-screen widget.

---

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────┐
│  Telegram Bot   │──────▶ │   FastAPI Backend     │──────▶ │ PostgreSQL  │
│  (bot/)         │        │   (backend/)          │        │  Database   │
└─────────────────┘        └──────────┬───────────┘        └─────────────┘
                                       │
                           ┌──────────▼───────────┐
                           │  Web Dashboard /     │
                           │  iOS Widget (/)      │
                           └──────────────────────┘
```

**Data flow:**
1. Send a message like `12 chipotle` to the Telegram bot
2. The bot calls `POST /api/v1/transactions`
3. Claude AI categorizes the expense and stores it in PostgreSQL
4. The web dashboard and Scriptable widget poll `/api/v1/summary` for live charts

---

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| API         | FastAPI (Python 3.11+)              |
| Database    | PostgreSQL 15                       |
| ORM         | SQLAlchemy 2.0 (async)              |
| Migrations  | Alembic                             |
| Validation  | Pydantic v2                         |
| AI          | Anthropic Claude API                |
| Bot         | python-telegram-bot                 |
| Widget      | Scriptable (JavaScript, iOS)        |
| Containers  | Docker + Docker Compose             |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- An [Anthropic API key](https://console.anthropic.com/)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/aryanverma30/spent.git
cd spent

# 2. Configure environment
cp .env.example .env
# Fill in DATABASE_URL, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN

# 3. Start all services
docker-compose up --build

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Open the dashboard
open http://localhost:8000
```

The interactive API docs are available at `http://localhost:8000/docs`.

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

| Method | Endpoint         | Description                              |
|--------|------------------|------------------------------------------|
| POST   | `/transactions`  | Create a new transaction                 |
| GET    | `/transactions`  | List transactions (paginated, filterable)|
| GET    | `/summary`       | Spending breakdown by category           |
| GET    | `/insights`      | AI-generated spending insights           |
| GET    | `/categories`    | List all categories with totals          |
| GET    | `/charts/donut`  | Donut chart PNG for a given period       |

### POST /transactions — Request body

```json
{
  "amount": 12.00,
  "merchant": "Chipotle",
  "category": "Food & Drink",
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
├── backend/
│   ├── app/
│   │   ├── main.py          # App entry point and router wiring
│   │   ├── config.py        # Environment variable settings
│   │   ├── routes/          # Endpoint handlers (transactions, summary, insights, …)
│   │   ├── models/          # SQLAlchemy ORM models + Pydantic schemas
│   │   ├── services/        # Business logic (db, ai, charts)
│   │   └── templates/       # Jinja2 dashboard HTML
│   ├── alembic/             # Database migration scripts
│   └── Dockerfile
├── bot/                     # Telegram bot
├── widget/                  # Scriptable iOS widget (spent.js)
├── docker-compose.yml
└── .env.example
```

---

## Development

```bash
# Tail backend logs
docker-compose logs -f backend

# Generate a migration after model changes
docker-compose exec backend alembic revision --autogenerate -m "describe change"

# Apply migrations
docker-compose exec backend alembic upgrade head
```

All migrations live in `backend/alembic/versions/` — commit them like code. Never commit `.env`.
