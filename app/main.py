import asyncio
import logging
from contextlib import asynccontextmanager

import pytz
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import init_db
from app.telegram import router as telegram_router, delete_webhook
from app.reminders import send_reminder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Scheduler
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Startup
    logger.info("Starting ReportsBot...")

    # Init database tables
    init_db()
    logger.info("Database initialized")

    # Delete any old webhook (for polling/dev mode)
    await delete_webhook()
    logger.info("Old webhook deleted (running in polling-compatible mode)")

    # Schedule daily reminder at 14:00 Asia/Almaty
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=14, minute=0, timezone=tz),
        id="daily_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (reminder at 14:00 Asia/Almaty)")

    # Start polling in background for development
    polling_task = asyncio.create_task(_poll_updates())

    yield

    # Shutdown
    polling_task.cancel()
    scheduler.shutdown(wait=False)
    logger.info("ReportsBot stopped")


app = FastAPI(title="ReportsBot", version="1.0.0", lifespan=lifespan)
app.include_router(telegram_router)


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "ReportsBot"}


async def _poll_updates():
    """
    Long-polling fallback for development (no webhook needed).
    In production, set a webhook and this won't be used.
    """
    import httpx

    logger.info("Starting long-polling for Telegram updates...")
    offset = 0
    url = f"{settings.bot_api_url}/getUpdates"

    while True:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message", "my_chat_member"],
                })
                data = resp.json()

                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        # Process through our webhook handler
                        await _process_update(update)

        except asyncio.CancelledError:
            logger.info("Polling stopped")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            await asyncio.sleep(5)


async def _process_update(update: dict):
    """Process a single update from polling (reuses webhook logic)."""
    from app.telegram import telegram_webhook

    class MockRequest:
        async def json(self):
            return update

    try:
        await telegram_webhook(MockRequest())
    except Exception as e:
        logger.error(f"Error processing update {update.get('update_id')}: {e}")
