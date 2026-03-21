# ReportsBot

Telegram-бот для сбора и оценки ежедневных отчётов команды с помощью Azure OpenAI.

## Стек

- **FastAPI** — HTTP-сервер и webhook
- **Telegram Bot API** — long-polling
- **Azure OpenAI (gpt-5.4)** — оценка отчётов по 4 критериям
- **MariaDB/MySQL** — хранение данных
- **APScheduler** — ежедневное напоминание в 14:00 (Asia/Almaty)
- **Docker Compose** — запуск базы данных

## Формат отчёта

Закрепить в чате:

```
/report

done:
- ...

problems:
- ...

plan:
- ...
```

## Оценка (LLM)

| Критерий | Описание |
|---|---|
| `format_score` | Есть ли структура done/problems/plan |
| `clarity_score` | Насколько конкретно описано |
| `execution_score` | Насколько выполнен вчерашний план |
| `discipline_score` | Отправлен ли до 23:59 (Asia/Almaty) |
| `total_score` | Итоговая оценка |

**Status:** `1` — плохо (<0.4), `2` — норм (0.4–0.7), `3` — хорошо (>0.7)

## Быстрый старт (локально)

```bash
# 1. Скопировать .env
cp .env.example .env
# Заполнить AZURE_OPENAI_API_KEY и TEAM_MEMBERS

# 2. Запустить БД
docker compose up -d

# 3. Установить зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Запустить бота
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Деплой на сервер (systemd)

```bash
git clone https://github.com/Nikita95727/ReportsBot.git /opt/reportsbot
cd /opt/reportsbot
cp .env.example .env && nano .env   # заполнить значения
docker compose up -d                # запустить БД
bash deploy.sh                      # установить как systemd-сервис
```

Управление:
```bash
systemctl status reportsbot
journalctl -u reportsbot -f
```

## Структура

```
app/
  config.py        — настройки из .env
  database.py      — SQLAlchemy модель Report
  parser.py        — парсинг /report сообщений
  llm.py           — оценка через Azure OpenAI
  db_operations.py — CRUD для отчётов
  telegram.py      — webhook-обработчик
  reminders.py     — напоминание в 14:00
  main.py          — FastAPI + scheduler + polling
tests/
  test_parser.py
  test_db.py
  test_telegram.py
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота |
| `AZURE_OPENAI_ENDPOINT` | URL деплоймента |
| `AZURE_OPENAI_API_KEY` | API ключ Azure |
| `AZURE_OPENAI_API_VERSION` | Версия API (2024-06-01) |
| `AZURE_OPENAI_DEPLOYMENT` | Имя деплоймента (gpt-5.4) |
| `MYSQL_HOST` | Хост БД |
| `MYSQL_PORT` | Порт БД |
| `MYSQL_USER` | Пользователь БД |
| `MYSQL_PASSWORD` | Пароль БД |
| `MYSQL_DATABASE` | Имя базы данных |
| `TEAM_MEMBERS` | Список команды: `id:username,...` |
| `TIMEZONE` | Часовой пояс (Asia/Almaty) |
