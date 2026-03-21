"""Tests for the Telegram webhook endpoint."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import date

from app.telegram import telegram_webhook


class MockRequest:
    def __init__(self, data):
        self._data = data

    async def json(self):
        return self._data


@pytest.mark.asyncio
class TestWebhookEndpoint:

    async def test_ignores_non_report_message(self):
        request = MockRequest({
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": -100, "type": "group"},
                "date": 1711065600,
                "text": "hello world"
            }
        })
        result = await telegram_webhook(request)
        assert result == {"ok": True}

    async def test_ignores_empty_message(self):
        request = MockRequest({
            "update_id": 2,
            "message": {
                "message_id": 2,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": -100, "type": "group"},
                "date": 1711065600,
            }
        })
        result = await telegram_webhook(request)
        assert result == {"ok": True}

    async def test_ignores_update_without_message(self):
        request = MockRequest({"update_id": 3})
        result = await telegram_webhook(request)
        assert result == {"ok": True}

    @patch("app.telegram.SessionLocal")
    @patch("app.telegram.score_report")
    @patch("app.telegram.get_yesterday_plan", return_value=None)
    @patch("app.telegram.upsert_report")
    async def test_processes_report(self, mock_upsert, mock_yesterday, mock_score, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_score.return_value = {
            "format_score": 0.8,
            "clarity_score": 0.7,
            "execution_score": 0.6,
            "discipline_score": 1.0,
            "total_score": 0.75,
            "comment": "Good"
        }
        mock_upsert.return_value = MagicMock()

        request = MockRequest({
            "update_id": 4,
            "message": {
                "message_id": 4,
                "from": {"id": 456, "is_bot": False, "first_name": "John", "username": "john"},
                "chat": {"id": -200, "type": "group"},
                "date": 1711065600,
                "text": "/report\n\ndone:\n- task 1\n\nplan:\n- task 2"
            }
        })

        result = await telegram_webhook(request)
        assert result == {"ok": True}

        # Verify upsert was called
        mock_upsert.assert_called_once()
        call_args = mock_upsert.call_args
        report_data = call_args[0][1]  # second arg is the data dict
        assert report_data["telegram_id"] == 456
        assert report_data["user_name"] == "john"
        assert report_data["has_report"] == 1
        assert report_data["has_plan"] == 1
        assert report_data["format_valid"] == 1
        assert report_data["total_score"] == 0.75
        assert report_data["status"] == 3

    async def test_tracks_chat_id(self):
        from app.telegram import active_chat_ids
        active_chat_ids.clear()

        request = MockRequest({
            "update_id": 5,
            "message": {
                "message_id": 5,
                "from": {"id": 123, "is_bot": False, "first_name": "Test"},
                "chat": {"id": -999, "type": "group"},
                "date": 1711065600,
                "text": "random message"
            }
        })
        await telegram_webhook(request)
        assert -999 in active_chat_ids
