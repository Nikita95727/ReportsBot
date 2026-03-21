import logging
from datetime import datetime

import httpx
import pytz

from app.config import settings
from app.database import SessionLocal
from app.db_operations import get_users_who_reported_today

logger = logging.getLogger(__name__)


async def send_reminder():
    """
    Check who hasn't reported today and send a reminder to all active chats.
    Called daily at 14:00 Asia/Almaty.
    """
    from app.telegram import active_chat_ids

    if not active_chat_ids:
        logger.warning("No active chats to send reminders to")
        return

    team = settings.team_members
    if not team:
        logger.warning("No team members configured, skipping reminder")
        return

    tz = pytz.timezone(settings.TIMEZONE)
    today = datetime.now(tz).date()

    session = SessionLocal()
    try:
        reported = get_users_who_reported_today(session, today)
    finally:
        session.close()

    # Find who hasn't reported
    missing = []
    for tid, uname in team.items():
        if tid not in reported:
            missing.append(f"- @{uname}")

    if not missing:
        logger.info("Everyone has reported today, no reminder needed")
        return

    missing_list = "\n".join(missing)
    text = (
        "Напоминание: не забудьте отправить /report сегодня до 23:59\n\n"
        f"Не отправили:\n{missing_list}"
    )

    # Send to all active chats
    for chat_id in list(active_chat_ids):
        try:
            url = f"{settings.bot_api_url}/sendMessage"
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                })
                result = resp.json()
                if result.get("ok"):
                    logger.info(f"Reminder sent to chat {chat_id}")
                else:
                    logger.warning(f"Failed to send reminder to chat {chat_id}: {result}")
        except Exception as e:
            logger.error(f"Error sending reminder to chat {chat_id}: {e}")
