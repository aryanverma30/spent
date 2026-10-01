# 💸 Spent

> A self-hosted personal spending tracker powered by AI. Text a Telegram bot your expenses in plain English, Claude automatically categorizes them, and an iOS home screen widget shows your spending at a glance.

## Features

- **Natural language expense logging** via Telegram — `"$12 Chipotle"`, `"Jewel Osco $45 groceries"`, `"Uber $22"`
- **AI-powered categorization** using Claude (Anthropic API) — learns from your corrections
- **10 spending categories** with color-coded donut chart
- **iOS Scriptable home screen widget** with live data
- **Daily, weekly, and monthly spending summaries** in the Telegram bot and web dashboard
- **Natural language spending queries** — ask `"how much did I spend last week?"` and get a breakdown
- **Inline category correction** directly in Telegram — tap to fix any miscategorization, bot learns for next time
- **Web dashboard** with real-time charts served from the backend

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| AI | Anthropic Claude API (claude-haiku-4-5) |
| Bot | python-telegram-bot |
| Widget | Scriptable (JavaScript, iOS) |
| Containers | Docker + Docker Compose |
| Deployment | Railway |

## Architecture

```
┌─────────────────┐        ┌──────────────────────┐        ┌─────────────┐
│  Telegram Bot   │──────▶ │   FastAPI Backend     │──────▶ │ PostgreSQL  │
│  (bot/)         │        │   (backend/)          │        │  Database   │
└─────────────────┘        └──────────┬───────────┘        └─────────────┘
                                       │
                           ┌──────────▼───────────┐
                           │  Web Dashboard  /    │
                           │  iOS Widget          │
                           └──────────────────────┘
```

**Data flow:**

1. User texts `"$12 Chipotle"` to the Telegram bot
2. Bot calls `POST /api/v1/ai/parse` — Claude categorizes the expense
3. If confidence is high, bot calls `POST /api/v1/transactions` to save it
4. If confidence is low, bot asks the user to confirm or recategorize
5. The web dashboard and iOS widget poll `/api/v1/summary` for live charts

**Apple Pay auto-logging:** an iOS Shortcuts automation POSTs every Apple Pay purchase to
`/api/v1/transactions/auto`. The backend categorizes it (your learned merchant rules first,
then Claude), saves it, and messages you on Telegram with **Change Category** / **Undo** buttons.

## Project Structure

```
spent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, router wiring
│   │   ├── config.py            # All env vars via pydantic-settings
│   │   ├── constants.py         # Shared category list and colors (single source of truth)
│   │   ├── routes/
│   │   │   ├── transactions.py  # POST/GET/PATCH/DELETE /transactions
│   │   │   ├── summary.py       # GET /summary — breakdown by category
│   │   │   ├── insights.py      # GET /insights — AI-generated summary
│   │   │   ├── categories.py    # GET /categories — full category list with totals
│   │   │   ├── charts.py        # GET /charts/donut — PNG donut chart
│   │   │   ├── ai.py            # POST /ai/parse, POST /ai/learn
│   │   │   └── dashboard.py     # GET / — serves the web UI
│   │   ├── models/
│   │   │   ├── transaction.py   # SQLAlchemy ORM model
│   │   │   ├── merchant_override.py  # Learned merchant→category mappings
│   │   │   └── schemas.py       # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── ai.py            # Claude API calls (parse + insights)
│   │   │   ├── charts.py        # Matplotlib chart generation + period utilities
│   │   │   ├── db.py            # Async engine, session factory, FastAPI dependency
│   │   │   └── merchant_learning.py  # Merchant override upsert/lookup
│   │   └── templates/
│   │       └── dashboard.html   # Jinja2 web dashboard
│   ├── alembic/
│   │   └── versions/            # Migration files — treat like code, commit them
│   ├── tests/                   # pytest + pytest-asyncio integration tests
│   ├── Dockerfile
│   ├── railway.toml             # Railway deploy config (runs migrations before start)
│   └── requirements.txt
├── bot/
│   ├── bot.py                   # Telegram bot — handles messages and inline buttons
│   ├── constants.py             # Mirror of backend/app/constants.py for the bot container
│   ├── Dockerfile
│   ├── railway.toml
│   └── requirements.txt
├── widget/
│   └── spent.js                 # iOS Scriptable widget
├── docker-compose.yml
├── .env.example                 # Template — copy to .env and fill in secrets
└── CLAUDE.md                    # AI assistant conventions for this repo
```

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- An [Anthropic API key](https://console.anthropic.com/) (for Claude AI categorization)
- A Telegram bot token (create one via [@BotFather](https://t.me/BotFather) on Telegram)

### Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/spent.git
cd spent

# 2. Create your .env file
cp .env.example .env
```

Open `.env` and fill in your real values:

```env
DATABASE_URL=postgresql+asyncpg://spent:spent@postgres:5432/spent
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_ALLOWED_USER_IDS=123456789
API_TOKEN=generate-with-secrets.token_urlsafe
AI_CONFIDENCE_THRESHOLD=0.75
ENVIRONMENT=development
```

```bash
# 3. Start all services (postgres + backend + bot)
docker-compose up --build

# 4. In a second terminal, apply database migrations
docker-compose exec backend alembic upgrade head

# 5. Open the web dashboard
open http://localhost:8000
```

The interactive API docs are at `http://localhost:8000/docs`.

Now text your Telegram bot something like `"$12 Chipotle"` — it will be categorized and saved.

### Running tests

```bash
docker-compose exec backend pytest tests/ -v
```

### Useful dev commands

```bash
# Tail backend logs
docker-compose logs -f backend

# Generate a migration after changing SQLAlchemy models
docker-compose exec backend alembic revision --autogenerate -m "describe the change"

# Apply pending migrations
docker-compose exec backend alembic upgrade head

# Check current migration state
docker-compose exec backend alembic current
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | asyncpg PostgreSQL connection string |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key from console.anthropic.com |
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USER_IDS` | Yes (bot) | — | Comma-separated Telegram user IDs the bot responds to; everyone else is ignored. Message the bot once and copy your id from its logs. Set it on the backend too so auto-logged purchases can notify you |
| `API_TOKEN` | Yes (production) | — | Bearer token required on every `/api/v1` request. Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`. If unset, the API is open in development and refuses all requests in production |
| `AI_CONFIDENCE_THRESHOLD` | No | `0.75` | Min AI confidence to auto-save (0.0–1.0) |
| `ENVIRONMENT` | No | `development` | `development` or `production` (controls SQL echo) |

## Auto-log Apple Pay Purchases (iOS 17+)

Every time you pay with Apple Pay, an iOS Shortcuts automation sends the purchase to Spent. You
get a Telegram message a few seconds later and only need to act if the category is wrong.

**Backend:** make sure `API_TOKEN`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_ALLOWED_USER_IDS` are set
on the backend service (not just the bot), so it can send you the notification.

**iPhone:**

1. Open **Shortcuts** → **Automation** tab → **+** (New Automation) → **Transaction**
2. Choose the cards to watch (leave merchants/categories as **Any**), select **Run Immediately**, then **Next**
3. Choose **New Blank Automation** and add the **Get Contents of URL** action
4. Set the URL to `https://your-app.railway.app/api/v1/transactions/auto` and expand the action:
   - **Method:** `POST`
   - **Headers:** `Authorization` = `Bearer <your API_TOKEN>`
   - **Request Body:** `JSON`, with three **Text** fields. For each value, tap the field and pick the
     **Shortcut Input** variable, then tap it again to choose the property:
     - `merchant` → Shortcut Input › **Merchant**
     - `amount` → Shortcut Input › **Amount**
     - `card` → Shortcut Input › **Card or Pass** (optional)
5. Tap **Done**. Test it by sending the same request from the action's play button, or just buy a coffee.

`amount` can be a number or a currency string like `$1,234.56`. You can also send an optional
`occurred_at` (ISO 8601); it defaults to the time the request arrives.

**What it doesn't catch:** the Wallet trigger only fires for Apple Pay. Swiping or inserting a
physical card, or typing your card number online, still needs a Telegram message.

## iOS Widget Setup

The widget is a [Scriptable](https://scriptable.app/) script that polls your backend's `/api/v1/summary` endpoint.

1. Install the free **Scriptable** app from the App Store
2. Open Scriptable and tap **+** to create a new script
3. Paste the entire contents of `widget/spent.js` into the editor
4. Change `BASE_URL` at the top of the script to your Railway deployment URL, and `API_TOKEN` to the same value as the backend's `API_TOKEN`
5. Name the script **Spent** and save it
6. Add a **medium** Scriptable widget to your iOS home screen
7. Long-press the widget → **Edit Widget** → select **Spent**
8. Optionally set a Parameter: `daily`, `weekly`, or `monthly` to pin that period

The widget shows a donut chart with your top spending categories. Tapping it opens the web dashboard and passes along your token, so the dashboard works without logging in.

## Deployment (Railway)

Both `backend/` and `bot/` are deployed as separate Railway services.

1. Push this repo to GitHub
2. Create a new Railway project and add a **PostgreSQL** plugin
3. Add a new service from the GitHub repo, set the **Root Directory** to `backend/`
4. Set all environment variables in the Railway dashboard (same as `.env` above)
5. Railway will auto-build from `backend/Dockerfile` and run migrations before starting (configured in `backend/railway.toml`)
6. Repeat steps 3–5 for the bot, setting Root Directory to `bot/` and adding `BACKEND_URL=https://your-backend.railway.app`
7. Set `BASE_URL` in `widget/spent.js` to your backend's Railway URL

## Spending Categories

| Category | Color | Examples |
|---|---|---|
| Food & Drink | `#FF6B6B` (red) | Restaurants, coffee shops, bars, delivery apps |
| Groceries | `#52B788` (green) | Grocery stores, supermarkets, Costco |
| Transport | `#4ECDC4` (teal) | Uber, Lyft, gas, parking, transit |
| Entertainment | `#45B7D1` (blue) | Movies, concerts, streaming, games |
| Shopping | `#96CEB4` (sage) | Amazon, clothing, retail |
| Health | `#FFEAA7` (yellow) | Doctor, pharmacy, gym |
| Housing | `#DDA0DD` (plum) | Rent, utilities, internet |
| Travel | `#F0A500` (amber) | Flights, hotels, Airbnb |
| Pets | `#F8C8D4` (pink) | Vet, food, supplies |
| Other | `#B0BEC5` (gray) | Everything else |

## API Reference

Base URL: `https://your-app.railway.app/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/transactions` | Create a new transaction |
| `GET` | `/transactions` | List transactions (paginated, filterable by category/period) |
| `PATCH` | `/transactions/{id}` | Update a transaction's category or note |
| `DELETE` | `/transactions/{id}` | Delete a transaction |
| `GET` | `/summary` | Spending breakdown by category for a period |
| `GET` | `/insights` | AI-generated spending summary for the current month |
| `GET` | `/categories` | All categories with period totals |
| `GET` | `/charts/donut` | Donut chart PNG for a period |
| `POST` | `/ai/parse` | Parse a natural language expense string |
| `POST` | `/ai/learn` | Record a user-confirmed merchant→category mapping |
| `GET` | `/health` | Health check |

Query params for period-based endpoints: `period=daily|weekly|monthly`, `date=YYYY-MM-DD`.

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes, following the conventions in [CLAUDE.md](CLAUDE.md)
4. Run `docker-compose exec backend pytest tests/ -v` and ensure tests pass
5. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `chore:`, etc.
6. Open a pull request

## License

MIT
