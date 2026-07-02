# Grid Bot Advisor and Monitor

A Telegram bot that answers one question before every grid launch: **should I start the bot right now?**

It pulls live data from the Pionex Futures API, runs three independent risk gates, and delivers a `LAUNCH / REVIEW / HOLD` verdict with the full reasoning trail attached. No order is ever placed automatically — the verdict is advisory and requires a manual `/confirm_launch` to proceed.

---

## How it works

Before each potential launch the engine runs three gates in sequence. If any gate fails, subsequent gates are skipped.

### Gate 1 — Market Regime
Checks whether the market is range-bound rather than trending.

| Indicator | PASS | CAUTION | FAIL |
|---|---|---|---|
| ADX 14 | ≤ 25 | 25 – 30 | > 30 |
| Grid range vs ATR 14 | ≥ 3× ATR | — | < 3× ATR |
| Price vs 14d swing | inside range | outside range | — |
| Realized vol term structure | flat / falling | 1d < 7d < 30d | — |

### Gate 2 — Positioning
Checks that funding rates and open interest do not signal a crowded or high-risk setup.

| Indicator | PASS | CAUTION | FAIL |
|---|---|---|---|
| Funding rate annualized | < 20% | 20 – 40% | > 40% |
| OI 7d change | < 10% | 10 – 20% | > 20% |
| OI history | ≥ 7 days | < 7 days (CAUTION, not free pass) | — |

> Open interest is sampled daily and stored locally — Pionex provides only the current value, so history must be built up over time.

### Gate 3 — Liquidation Safety
Validates that the proposed grid parameters leave enough distance to the liquidation price. Calls Pionex's `checkParams` endpoint — no position is opened.

| Check | Result |
|---|---|
| Leverage > 5× | FAIL |
| Liquidation buffer < 2.5× grid range width (up or down) | FAIL |
| Stop-loss at or beyond liquidation price (LONG: SL ≤ liq; SHORT: SL ≥ liq) | FAIL |
| Stop-loss too close to price (< 1% for crypto, < 0.5% for XAUT) | CAUTION |
| Take-profit inside the grid range (LONG: TP < top; SHORT: TP > bottom) | CAUTION |
| Otherwise | PASS |

### Verdict

| Condition | Verdict |
|---|---|
| All gates PASS | 🟢 LAUNCH |
| No FAIL, at least one CAUTION | 🟡 REVIEW |
| Any gate FAIL | 🔴 HOLD |

---

## Bot commands

| Command | Description |
|---|---|
| `/start` | Introduction and overview |
| `/weekly_assessment` | Run a full three-gate assessment immediately |
| `/daily_assessment` | Run Gate 2 (positioning) check only |
| `/verdict` | Show the most recent stored verdict with gate details |
| `/help` | List available commands |

When a verdict suggests `LAUNCH`, an inline keyboard appears with:
- 🪄 **Launch** — places the grid via Pionex API
- 🦽 **Manual** — registers the grid as manually launched (no API call)

---

## Scheduling

The bot runs two automatic jobs:

| Job | Schedule | Gates run | Action |
|---|---|---|---|
| Daily positioning check | Every day at 00:05 UTC | Gate 2 only | Stores OI snapshot; sends alert only if status changed |
| Weekly full assessment | Every Saturday | Gates 1 – 3 | Sends digest regardless of verdict |

---

## Architecture

Clean Architecture — domain → application → infrastructure → presentation. No business logic outside the domain layer.

```
source/
├── domain/              # entities, value objects, exceptions
├── application/
│   ├── ports.py         # abstract interfaces (Notifier, MarketDataPort, GridPort)
│   ├── exceptions.py    # application-layer errors
│   ├── utils.py         # evaluate_checks — aggregates gate rules into verdict
│   ├── services/        # gate orchestrators, indicator computation, grid builder, OI snapshots
│   │   └── gates/       # assess_market_regime, assess_positioning, assess_liquidation_safety
│   └── use_cases/       # pure rule functions: check_regime_rules, check_positioning_rules, liquidation_safety_checks
├── infrastructure/
│   ├── http/pionex/     # Pionex API client, request/response models, staleness guard adapter
│   ├── database/        # SQLAlchemy models, alembic migrations, repositories (alchemy impl)
│   │   └── repositories/
│   │       ├── base.py          # AbstractRepository[ET] — generic CRUD contract
│   │       ├── filters.py       # BaseQueryFilter, BaseFieldCondition
│   │       └── alchemy/         # SQLAlchemyBaseRepository + concrete repos
│   └── telegram/        # aiogram notifier, message formatter
└── presentation/
    ├── bot/handlers/    # /weekly_assessment, /daily_assessment, /verdict, /start, /help, grid launch callbacks
    │   └── keyboards/   # inline keyboard builder for verdict reactions
    └── scheduler/       # APScheduler cron jobs (daily positioning, weekly assessment)
```

---

## Requirements

- Python 3.13
- Pionex account with API key (Bot API scope for `checkParams`)
- Telegram bot token and chat ID

---

## Configuration

All settings are read from environment variables (or a `.env` file).

| Variable | Description | Required |
|---|---|---|
| `TOKENT` | Telegram bot token | ✅ |
| `CHAT_ID` | Telegram chat ID to send messages to | ✅ |
| `API_KEY` | Pionex API key | ✅ |
| `API_SECRET` | Pionex API secret | ✅ |
| `NAME` | SQLite database name / path (default: `advisor`) | — |
| `LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING` (default: `DEBUG`) | — |
| `LOG_JSON` | Emit logs as JSON (default: `true`) | — |

Create a `.env` file in the project root:

```env
TOKENT=your_telegram_bot_token
CHAT_ID=your_chat_id
API_KEY=your_pionex_api_key
API_SECRET=your_pionex_api_secret
```

---

## Running with Docker

```bash
# First run — builds the image and initialises the database
docker compose up -d

# View logs
docker compose logs -f bot

# Inspect the database
sqlite3 data/advisor.db .tables
```

The database file is written to `./data/advisor.db` on the host. Logs are written to `./logs/`.

The `migrate` service runs `alembic upgrade head` before the bot starts. If migration fails, the bot does not start.

---

## Testing

```bash
# Run all tests
uv run pytest

# Run only unit tests (fast, no I/O)
uv run pytest tests/unit/

# Run integration tests (marked with DB/HTTP access)
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov --cov-report=term-missing

# Type checking
uv run mypy

# Lint + auto-fix
uv run ruff check . --fix
```

### Test structure

```
tests/
├── conftest.py              # shared fixtures (clock, settings, base entities)
├── fixtures/
│   ├── factories.py         # make_* factories for test data
│   ├── fakes.py             # shared fake repositories (in-memory, AbstractRepository)
│   └── pionex_responses/    # real API response fixtures (JSON)
├── unit/
│   ├── domain/              # entity validation, evaluate_checks, gate rules
│   ├── application/
│   │   ├── services/        # DecisionLogService, OISnapshotService, GridProposalBuilder, IndicatorService, GridBotService
│   │   ├── use_cases/
│   │   │   └── gates/       # market regime, positioning, liquidation safety rules (+ property-based)
│   │   └── formatters/      # alert & digest message formatting
│   └── presentation/
│       └── bot/             # decision & launch handlers
└── integration/
    ├── pionex/              # HTTP client + staleness guard adapter
    ├── persistence/         # SQLAlchemy repositories (SQLite in-memory)
    └── test_full_assessment_pipeline.py  # end-to-end three-gate run
```

### Testing philosophy

- **Unit tests** follow the classical (Detroit) school: use real objects where possible, mock only external I/O (HTTP, DB). Hand-rolled fakes (`tests/fixtures/fakes.py`) replace real repositories — faster and more predictable than SQLite.
- **Property-based tests** (`test_property_based.py`) use Hypothesis to verify gate rules never crash on any valid input.
- **Gate rule tests** are parametrized to cover boundary values (ADX thresholds, funding rate thresholds) without duplicating test code.
- **Integration tests** use `respx` for HTTP mocking and SQLite `:memory:` for repository tests. Marked separately from unit tests.

---

## Local development

```bash
# Install dependencies
uv sync

# Apply database migrations
uv run alembic upgrade head

# Run the bot
uv run python -m source.main

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov --cov-report=term-missing

# Type checking
uv run mypy

# Lint + auto-fix
uv run ruff check . --fix
```

---

## Data persistence

| Table | Purpose |
|---|---|
| `oi_snapshots` | Daily OI samples — used to compute the 7-day change for Gate 2 |
| `decision_logs` | Full verdict history with gate results and raw values — audit trail |
| `grid_launches` | Launched grids (auto via API or manual) — linked to decision verdicts |
