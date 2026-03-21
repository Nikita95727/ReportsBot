"""Tests for app/db_operations.py — database CRUD operations.

Uses SQLite in-memory for isolation.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, Report
from app.db_operations import (
    upsert_report,
    get_yesterday_plan,
    get_users_who_reported_today,
    compute_status,
)


@pytest.fixture
def session():
    """Create an in-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    yield session
    session.close()


class TestUpsertReport:
    def test_insert_new_report(self, session):
        data = {
            "date": date(2026, 3, 21),
            "user_name": "testuser",
            "telegram_id": 12345,
            "has_report": 1,
            "has_plan": 1,
            "format_valid": 1,
            "format_score": 0.8,
            "clarity_score": 0.7,
            "execution_score": 0.6,
            "discipline_score": 1.0,
            "total_score": 0.75,
            "status": 3,
            "comment": "Good report",
            "raw_text": "/report\ndone:\n- task\nplan:\n- next",
        }
        report = upsert_report(session, data)

        assert report.id is not None
        assert report.telegram_id == 12345
        assert report.total_score == 0.75
        assert report.status == 3

    def test_update_existing_report(self, session):
        data1 = {
            "date": date(2026, 3, 21),
            "user_name": "testuser",
            "telegram_id": 12345,
            "has_report": 1,
            "has_plan": 0,
            "format_valid": 0,
            "format_score": 0.3,
            "clarity_score": 0.3,
            "execution_score": 0.3,
            "discipline_score": 1.0,
            "total_score": 0.3,
            "status": 1,
            "comment": "Bad report",
            "raw_text": "first attempt",
        }
        upsert_report(session, data1)

        data2 = {
            "date": date(2026, 3, 21),
            "user_name": "testuser",
            "telegram_id": 12345,
            "has_report": 1,
            "has_plan": 1,
            "format_valid": 1,
            "format_score": 0.9,
            "clarity_score": 0.8,
            "execution_score": 0.7,
            "discipline_score": 1.0,
            "total_score": 0.85,
            "status": 3,
            "comment": "Great report",
            "raw_text": "second attempt",
        }
        report = upsert_report(session, data2)

        # Should be the same row, updated
        count = session.query(Report).filter(
            Report.telegram_id == 12345,
            Report.date == date(2026, 3, 21),
        ).count()
        assert count == 1
        assert report.total_score == 0.85
        assert report.raw_text == "second attempt"

    def test_different_users_same_day(self, session):
        for tid in [111, 222, 333]:
            upsert_report(session, {
                "date": date(2026, 3, 21),
                "user_name": f"user_{tid}",
                "telegram_id": tid,
                "has_report": 1,
                "has_plan": 1,
                "format_valid": 1,
                "format_score": 0.5,
                "clarity_score": 0.5,
                "execution_score": 0.5,
                "discipline_score": 1.0,
                "total_score": 0.5,
                "status": 2,
                "comment": "ok",
                "raw_text": "report",
            })

        count = session.query(Report).filter(
            Report.date == date(2026, 3, 21)
        ).count()
        assert count == 3


class TestGetYesterdayPlan:
    def test_returns_yesterday_text(self, session):
        today = date(2026, 3, 21)
        yesterday = today - timedelta(days=1)

        upsert_report(session, {
            "date": yesterday,
            "user_name": "testuser",
            "telegram_id": 12345,
            "has_report": 1,
            "has_plan": 1,
            "format_valid": 1,
            "total_score": 0.5,
            "status": 2,
            "raw_text": "yesterday's report with plan",
        })

        result = get_yesterday_plan(session, 12345, today)
        assert result == "yesterday's report with plan"

    def test_returns_none_when_no_yesterday(self, session):
        result = get_yesterday_plan(session, 12345, date(2026, 3, 21))
        assert result is None


class TestGetUsersWhoReportedToday:
    def test_returns_reported_users(self, session):
        today = date(2026, 3, 21)

        for tid in [111, 222]:
            upsert_report(session, {
                "date": today,
                "user_name": f"user_{tid}",
                "telegram_id": tid,
                "has_report": 1,
                "has_plan": 1,
                "format_valid": 1,
                "total_score": 0.5,
                "status": 2,
                "raw_text": "report",
            })

        reported = get_users_who_reported_today(session, today)
        assert reported == {111, 222}

    def test_returns_empty_when_no_reports(self, session):
        reported = get_users_who_reported_today(session, date(2026, 3, 21))
        assert reported == set()


class TestComputeStatus:
    def test_good(self):
        assert compute_status(0.8) == 3
        assert compute_status(1.0) == 3

    def test_ok(self):
        assert compute_status(0.5) == 2
        assert compute_status(0.4) == 2
        assert compute_status(0.7) == 2

    def test_bad(self):
        assert compute_status(0.3) == 1
        assert compute_status(0.0) == 1
        assert compute_status(0.39) == 1
