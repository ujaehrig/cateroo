# Cateroo

Fetches ordered meals from the Cateroo portal API, stores them in
SQLite, and generates an `.ics` calendar file. Serve the file via
nginx and subscribe from Outlook/Google Calendar.

## Flow

```
Cron (07:00) → API login → bookings → menu details → SQLite → .ics file
```

## Setup

```bash
# Clone and install
cd /path/to/cateroo
uv sync

# Configure
cp .env.example .env
# Edit .env with your credentials and output path

# Run manually
uv run cateroo

# Set up cron (runs daily at 07:00)
crontab -e
# Add the line from crontab.example
```

## Configuration

All configuration lives in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| CATEROO_URL | yes | — | Portal base URL |
| CATEROO_USER | yes | — | Portal login email |
| CATEROO_PASSWORD | yes | — | Portal password |
| ICS_OUTPUT_PATH | no | ./cateroo.ics | Output .ics file path |
| DB_PATH | no | ./cateroo.db | SQLite database path |

## Serving the calendar

The app generates a static `.ics` file. Serve it via nginx with a
secret UUID path (no auth needed — the UUID is the secret):

```nginx
location /6fd9593f-81d2-4780-8162-c71ce2239a7b/cateroo.ics {
    alias /path/to/cateroo.ics;
    default_type text/calendar;
}
```

Subscribe URL:
`https://your-domain/6fd9593f-81d2-4780-8162-c71ce2239a7b/cateroo.ics`

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/

# Type check
uv run pyright

# Format
uv run ruff format src/ tests/
```

## Architecture

```
src/cateroo/
├── config.py         — .env loading and validation
├── api_client.py     — Cateroo portal API (login, bookings, menus)
├── parser.py         — Parse gastro_text HTML for meal title/ingredients
├── db.py             — SQLite persistence (meals)
├── ics.py            — Generate combined .ics file from meals
└── main.py           — Orchestration entry point
```
