import logging
from datetime import datetime

import httpx
import pytz
from fastapi import APIRouter, Request

from app.config import settings
from app.database import SessionLocal
from app.parser import parse_report
from app.llm import score_report
from app.db_operations import upsert_report, get_yesterday_plan, compute_status

logger = logging.getLogger(__name__)
router = APIRouter()

# Track chat IDs the bot is active in
active_chat_ids: set[int] = set()


async def send_message(chat_id: int, text: str, reply_markup: dict | None = None):
    url = f"{settings.bot_api_url}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle incoming Telegram webhook updates."""
    try:
        update = await request.json()
    except Exception:
        return {"ok": True}

    # Handle being added to a group — track the chat_id
    if "my_chat_member" in update:
        chat_member = update["my_chat_member"]
        chat_id = chat_member.get("chat", {}).get("id")
        new_status = chat_member.get("new_chat_member", {}).get("status", "")
        if new_status in ("member", "administrator"):
            if chat_id:
                active_chat_ids.add(chat_id)
                logger.info(f"Bot added to chat {chat_id}")
        elif new_status in ("left", "kicked"):
            active_chat_ids.discard(chat_id)
            logger.info(f"Bot removed from chat {chat_id}")
        return {"ok": True}

    # Process only messages
    message = update.get("message")
    if not message:
        return {"ok": True}

    # Track chat_id from any message
    chat_id = message.get("chat", {}).get("id")
    if chat_id:
        active_chat_ids.add(chat_id)

    text = message.get("text", "")
    if not text:
        return {"ok": True}

    # Extract user info
    from_user = message.get("from", {})
    telegram_id = from_user.get("id")
    username = from_user.get("username", "")
    first_name = from_user.get("first_name", "")
    last_name = from_user.get("last_name", "")
    user_name = username or f"{first_name} {last_name}".strip() or str(telegram_id)
    chat_type = message.get("chat", {}).get("type", "")

    # Current date in Asia/Almaty
    tz = pytz.timezone(settings.TIMEZONE)
    now = datetime.now(tz)
    report_date = now.date()

    # UI LOGIC (Available to anyone in private chat)
    if chat_type == "private":
        if text.strip() == "/start":
            keyboard = {
                "keyboard": [[{"text": "📊 Просмотреть отчеты"}]],
                "resize_keyboard": True
            }
            await send_message(
                chat_id=chat_id,
                text="Привет! Тебе доступна панель управления отчетами.",
                reply_markup=keyboard
            )
            return {"ok": True}

        if text.strip() == "📊 Просмотреть отчеты":
            session = SessionLocal()
            try:
                from app.db_operations import get_reports_for_date
                reports = get_reports_for_date(session, report_date)
                
                if not reports:
                    await send_message(chat_id, f"За сегодня ({report_date}) отчетов еще нет.")
                else:
                    msg = f"📊 **Отчеты за {report_date}**\n\n"
                    for r in reports:
                        status_emoji = "🔴" if r.status == 1 else "🟡" if r.status == 2 else "🟢"
                        msg += f"{status_emoji} **{r.user_name}** | Скор: {r.total_score}\n"
                        msg += f"План: {'✅' if r.has_plan else '❌'} | Формат: {'✅' if r.format_valid else '❌'}\n"
                        if r.comment:
                            msg += f"💬 _{r.comment}_\n"
                        msg += "\n"
                    await send_message(chat_id, msg)
            except Exception as e:
                logger.error(f"Error fetching reports: {e}", exc_info=True)
                await send_message(chat_id, "Произошла ошибка при получении отчетов.")
            finally:
                session.close()
            return {"ok": True}

    # Only process /report messages
    if not text.strip().lower().startswith("/report"):
        return {"ok": True}

    logger.info(f"Processing /report from {user_name} (id={telegram_id}) in chat {chat_id}")

    # Parse report
    parsed = parse_report(text)

    # Get yesterday's plan for LLM comparison
    session = SessionLocal()
    try:
        yesterday_plan = get_yesterday_plan(session, telegram_id, report_date)

        # LLM scoring — pass submission time for discipline_score
        scores = score_report(parsed["raw_text"], yesterday_plan, submitted_at=now)

        # Compute status
        total = scores.get("total_score", 0.0)
        status = compute_status(total)

        # Build report data
        report_data = {
            "date": report_date,
            "user_name": user_name,
            "telegram_id": telegram_id,
            "has_report": 1 if parsed["has_report"] else 0,
            "has_plan": 1 if parsed["has_plan"] else 0,
            "format_valid": 1 if parsed["format_valid"] else 0,
            "format_score": scores.get("format_score", 0.0),
            "clarity_score": scores.get("clarity_score", 0.0),
            "execution_score": scores.get("execution_score", 0.0),
            "discipline_score": scores.get("discipline_score", 0.0),
            "total_score": total,
            "status": status,
            "comment": scores.get("comment", ""),
            "raw_text": parsed["raw_text"],
        }

        # Upsert to DB
        upsert_report(session, report_data)
        logger.info(f"Report saved for {user_name}, total_score={total}, status={status}")

    except Exception as e:
        logger.error(f"Error processing report: {e}", exc_info=True)
    finally:
        session.close()

    # Silent — no response to chat
    return {"ok": True}


async def set_webhook(webhook_url: str):
    """Register the webhook URL with Telegram."""
    url = f"{settings.bot_api_url}/setWebhook"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "url": webhook_url,
            "allowed_updates": ["message", "my_chat_member"],
        })
        result = resp.json()
        logger.info(f"Set webhook result: {result}")
        return result


async def delete_webhook():
    """Delete the current webhook."""
    url = f"{settings.bot_api_url}/deleteWebhook"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url)
        result = resp.json()
        logger.info(f"Delete webhook result: {result}")
        return result
