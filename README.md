# ReportsBot

A Telegram bot for collecting and scoring daily team reports using Azure OpenAI.

## Tech Stack

- **FastAPI** — HTTP server and webhook handler
- **Telegram Bot API** — long-polling mode implementation
- **Azure OpenAI (gpt-5.4)** — report scoring across 4 criteria
- **MariaDB/MySQL** — data storage
- **APScheduler** — daily reminders at 14:00 (Asia/Almaty)
- **Systemd** — background service management on Linux

## Report Format

Pin this in your chat:

```
/report

done:
- ...

problems:
- ...

plan:
- ...
```

## Scoring (LLM)

| Criterion | Description |
|---|---|
| `format_score` | Structure presence (done/problems/plan) |
| `clarity_score` | Specificity and clarity of description |
| `execution_score` | Alignment with yesterday's plan |
| `discipline_score` | Sent before 23:59 (Asia/Almaty) |
| `total_score` | Overall weighted result |

**Status:** `1` — Poor (<0.4), `2` — Good (0.4–0.7), `3` — Excellent (>0.7)

## Quick Start (Local)

```bash
# 1. Copy .env
cp .env.example .env
# Fill in AZURE_OPENAI_API_KEY and TEAM_MEMBERS

# 2. Start DB
docker compose up -d

# 3. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Run bot
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Server Deployment (systemd)

```bash
git clone https://github.com/Nikita95727/ReportsBot.git /opt/reportsbot
cd /opt/reportsbot
cp .env.example .env && nano .env   # Fill in values
bash deploy.sh                      # Install as a systemd service
```

Management:
```bash
systemctl status reportsbot
journalctl -u reportsbot -f
```

## Project Structure

```
app/
  config.py        — Settings from .env
  database.py      — SQLAlchemy Report model
  parser.py        — Parsing of /report messages
  llm.py           — Scoring via Azure OpenAI
  db_operations.py — CRUD for reports
  telegram.py      — Webhook/update handler
  reminders.py     — 14:00 reminder logic
  main.py          — FastAPI + scheduler + polling
tests/
  test_parser.py
  test_db.py
  test_telegram.py
```

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot API token |
| `AZURE_OPENAI_ENDPOINT` | Deployment URL |
| `AZURE_OPENAI_API_KEY` | Azure API Key |
| `AZURE_OPENAI_API_VERSION` | API Version (e.g., 2024-06-01) |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment Name (e.g., gpt-5.4) |
| `MYSQL_HOST` | DB Host |
| `MYSQL_PORT` | DB Port |
| `MYSQL_USER` | DB User |
| `MYSQL_PASSWORD` | DB Password |
| `MYSQL_DATABASE` | DB Name |
| `TEAM_MEMBERS` | Team list: `id:username,...` |
| `TIMEZONE` | Timezone (e.g., Asia/Almaty) |
