import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import Report

logger = logging.getLogger(__name__)


def upsert_report(session: Session, data: dict) -> Report:
    """
    Insert or update a report row by (telegram_id, date).
    If a row already exists for this user+date, update it.
    """
    existing = session.query(Report).filter(
        and_(
            Report.telegram_id == data["telegram_id"],
            Report.date == data["date"],
        )
    ).first()

    if existing:
        # Update existing row
        for key, value in data.items():
            if key != "id" and hasattr(existing, key):
                setattr(existing, key, value)
        existing.created_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(existing)
        logger.info(f"Updated report for user {data['telegram_id']} on {data['date']}")
        return existing
    else:
        # Insert new row
        report = Report(**data)
        report.created_at = datetime.now(timezone.utc)
        session.add(report)
        session.commit()
        session.refresh(report)
        logger.info(f"Created report for user {data['telegram_id']} on {data['date']}")
        return report


def get_yesterday_plan(session: Session, telegram_id: int, today: date) -> Optional[str]:
    """
    Fetch yesterday's raw_text for a given user to compare execution.
    """
    yesterday = today - timedelta(days=1)
    report = session.query(Report).filter(
        and_(
            Report.telegram_id == telegram_id,
            Report.date == yesterday,
        )
    ).first()

    if report and report.raw_text:
        return report.raw_text
    return None


def get_users_who_reported_today(session: Session, today: date) -> set[int]:
    """
    Return set of telegram_ids that have a report for today.
    """
    reports = session.query(Report.telegram_id).filter(
        Report.date == today
    ).all()
    return {r[0] for r in reports}


def get_reports_for_date(session: Session, target_date: date) -> list[Report]:
    """Retrieve all reports for a specific date."""
    return session.query(Report).filter(Report.date == target_date).all()


def compute_status(total_score: float) -> int:
    """
    Compute status from total_score:
    0 - no report
    1 - bad (< 0.4)
    2 - ok (0.4 - 0.7)
    3 - good (> 0.7)
    """
    if total_score > 0.7:
        return 3
    elif total_score >= 0.4:
        return 2
    else:
        return 1
