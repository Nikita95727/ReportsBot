"""Tests for app/parser.py — report text parsing."""

from app.parser import parse_report


class TestParseReportValid:
    """Test valid report formats."""

    def test_full_report(self):
        text = (
            "/report\n\n"
            "done:\n"
            "- finished auth module\n"
            "- fixed bug #123\n\n"
            "problems:\n"
            "- deployment issues\n\n"
            "plan:\n"
            "- start payment module\n"
            "- code review"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is True
        assert result["format_valid"] is True
        assert result["done"] is not None
        assert "finished auth module" in result["done"]
        assert result["problems"] is not None
        assert "deployment issues" in result["problems"]
        assert result["plan"] is not None
        assert "start payment module" in result["plan"]
        assert result["raw_text"] == text

    def test_report_without_problems(self):
        text = (
            "/report\n\n"
            "done:\n"
            "- task 1\n\n"
            "plan:\n"
            "- task 2"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is True
        assert result["format_valid"] is True
        assert result["problems"] is None

    def test_report_with_multiline_items(self):
        text = (
            "/report\n\n"
            "done:\n"
            "- long task that spans\n"
            "  multiple lines\n"
            "- another task\n\n"
            "plan:\n"
            "- next task"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is True
        assert result["format_valid"] is True


class TestParseReportInvalid:
    """Test invalid / partial report formats."""

    def test_no_done_section(self):
        text = (
            "/report\n\n"
            "plan:\n"
            "- task 1"
        )
        result = parse_report(text)

        assert result["has_report"] is False
        assert result["has_plan"] is True
        assert result["format_valid"] is False

    def test_no_plan_section(self):
        text = (
            "/report\n\n"
            "done:\n"
            "- task 1"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is False
        assert result["format_valid"] is False

    def test_empty_report(self):
        text = "/report"
        result = parse_report(text)

        assert result["has_report"] is False
        assert result["has_plan"] is False
        assert result["format_valid"] is False

    def test_garbage_text(self):
        text = "/report hello world random stuff"
        result = parse_report(text)

        assert result["has_report"] is False
        assert result["has_plan"] is False
        assert result["format_valid"] is False

    def test_raw_text_always_preserved(self):
        text = "/report broken format but still saved"
        result = parse_report(text)

        assert result["raw_text"] == text


class TestParseReportEdgeCases:
    """Test edge cases."""

    def test_case_insensitive_sections(self):
        text = (
            "/report\n\n"
            "Done:\n"
            "- task 1\n\n"
            "Plan:\n"
            "- task 2"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is True
        assert result["format_valid"] is True

    def test_extra_whitespace(self):
        text = (
            "/report  \n\n"
            "  done:  \n"
            "- task 1\n\n"
            "  plan:  \n"
            "- task 2"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["has_plan"] is True

    def test_report_command_variations(self):
        text = (
            "/Report\n\n"
            "done:\n"
            "- task 1\n\n"
            "plan:\n"
            "- task 2"
        )
        result = parse_report(text)

        assert result["has_report"] is True
        assert result["format_valid"] is True
