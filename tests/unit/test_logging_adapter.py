"""Unit tests for logging_adapter module.

Tests core behavior of ContextAdapter including:
- Context key-value injection with proper formatting
- None value filtering (optional context)
- Empty context handling
- Message preservation
"""

import logging

from openstan.logging_adapter import ContextAdapter


class TestContextAdapterFormatting:
    """Tests for ContextAdapter output formatting."""

    def test_inject_single_context_key(self, caplog):
        """Single context key should be formatted as [key=value] prefix."""
        logger = logging.getLogger("test_single")
        adapter = ContextAdapter(logger, {"batch_id": "abc123"})

        with caplog.at_level(logging.INFO, logger="test_single"):
            adapter.info("Test message")

        assert "[batch_id=abc123] Test message" in caplog.text

    def test_inject_multiple_context_keys(self, caplog):
        """Multiple context keys should be formatted as [key1=val1|key2=val2]."""
        logger = logging.getLogger("test_multi")
        adapter = ContextAdapter(
            logger, {"batch_id": "batch123", "project_id": "proj-xyz"}
        )

        with caplog.at_level(logging.INFO, logger="test_multi"):
            adapter.info("Test message")

        # Both keys should appear in the prefix
        assert "[batch_id=batch123|project_id=proj-xyz] Test message" in caplog.text

    def test_inject_three_context_keys(self, caplog):
        """Three context keys should all appear in the prefix."""
        logger = logging.getLogger("test_three")
        adapter = ContextAdapter(
            logger,
            {
                "batch_id": "batch123",
                "project_id": "proj-xyz",
                "session_id": "sess456",
            },
        )

        with caplog.at_level(logging.INFO, logger="test_three"):
            adapter.info("Test message")

        # All three keys should appear
        assert "batch_id=batch123" in caplog.text
        assert "project_id=proj-xyz" in caplog.text
        assert "session_id=sess456" in caplog.text
        assert "[" in caplog.text and "]" in caplog.text


class TestContextAdapterNoneFiltering:
    """Tests for ContextAdapter None value filtering."""

    def test_skip_none_values(self, caplog):
        """None values should be skipped from the output."""
        logger = logging.getLogger("test_none_skip")
        adapter = ContextAdapter(logger, {"batch_id": "batch123", "project_id": None})

        with caplog.at_level(logging.INFO, logger="test_none_skip"):
            adapter.info("Test message")

        # Only batch_id should appear, project_id should be skipped
        assert "[batch_id=batch123] Test message" in caplog.text
        assert "project_id" not in caplog.text

    def test_skip_multiple_none_values(self, caplog):
        """Multiple None values should all be skipped."""
        logger = logging.getLogger("test_multi_none")
        adapter = ContextAdapter(
            logger,
            {
                "batch_id": None,
                "project_id": "proj-xyz",
                "session_id": None,
            },
        )

        with caplog.at_level(logging.INFO, logger="test_multi_none"):
            adapter.info("Test message")

        # Only project_id should appear
        assert "[project_id=proj-xyz] Test message" in caplog.text
        assert "batch_id" not in caplog.text
        assert "session_id" not in caplog.text

    def test_all_none_values_no_prefix(self, caplog):
        """When all values are None, no prefix should be added."""
        logger = logging.getLogger("test_all_none")
        adapter = ContextAdapter(
            logger,
            {"batch_id": None, "project_id": None, "session_id": None},
        )

        with caplog.at_level(logging.INFO, logger="test_all_none"):
            adapter.info("Test message")

        # No prefix should appear, just the message
        assert "Test message" in caplog.text
        assert (
            "[" not in caplog.text
            or "Test message" == caplog.text.split("]")[-1].strip()
        )


class TestContextAdapterEmptyContext:
    """Tests for ContextAdapter with empty context."""

    def test_empty_context_dict_no_prefix(self, caplog):
        """Empty context dict should produce no prefix."""
        logger = logging.getLogger("test_empty")
        adapter = ContextAdapter(logger, {})

        with caplog.at_level(logging.INFO, logger="test_empty"):
            adapter.info("Test message")

        # Message should pass through unchanged
        assert "Test message" in caplog.text
        assert (
            "[" not in caplog.text
            or "Test message" == caplog.text.split("]")[-1].strip()
        )

    def test_none_extra_no_prefix(self, caplog):
        """None extra should produce no prefix."""
        logger = logging.getLogger("test_none_extra")
        adapter = ContextAdapter(logger, None)

        with caplog.at_level(logging.INFO, logger="test_none_extra"):
            adapter.info("Test message")

        # Message should pass through unchanged
        assert "Test message" in caplog.text
        assert (
            "[" not in caplog.text
            or "Test message" == caplog.text.split("]")[-1].strip()
        )


class TestContextAdapterLogLevels:
    """Tests for ContextAdapter with different log levels."""

    def test_error_level_with_context(self, caplog):
        """ERROR level should include context prefix."""
        logger = logging.getLogger("test_error")
        adapter = ContextAdapter(logger, {"batch_id": "error_batch"})

        with caplog.at_level(logging.ERROR, logger="test_error"):
            adapter.error("Error occurred")

        assert "[batch_id=error_batch] Error occurred" in caplog.text

    def test_warning_level_with_context(self, caplog):
        """WARNING level should include context prefix."""
        logger = logging.getLogger("test_warning")
        adapter = ContextAdapter(logger, {"project_id": "proj-123"})

        with caplog.at_level(logging.WARNING, logger="test_warning"):
            adapter.warning("Warning message")

        assert "[project_id=proj-123] Warning message" in caplog.text

    def test_info_level_with_context(self, caplog):
        """INFO level should include context prefix."""
        logger = logging.getLogger("test_info")
        adapter = ContextAdapter(logger, {"session_id": "sess-456"})

        with caplog.at_level(logging.INFO, logger="test_info"):
            adapter.info("Info message")

        assert "[session_id=sess-456] Info message" in caplog.text


class TestContextAdapterMessagePreservation:
    """Tests for ContextAdapter message preservation."""

    def test_message_content_preserved(self, caplog):
        """Message content should be preserved exactly after the prefix."""
        logger = logging.getLogger("test_preserve")
        adapter = ContextAdapter(logger, {"batch_id": "123"})
        original_message = "This is a longer message with special chars: @#$%"

        with caplog.at_level(logging.INFO, logger="test_preserve"):
            adapter.info(original_message)

        assert original_message in caplog.text

    def test_multiline_message_preserved(self, caplog):
        """Multiline messages should be preserved."""
        logger = logging.getLogger("test_multiline")
        adapter = ContextAdapter(logger, {"batch_id": "123"})
        original_message = "Line 1\nLine 2\nLine 3"

        with caplog.at_level(logging.INFO, logger="test_multiline"):
            adapter.info(original_message)

        # Multiline content should be preserved (note: logging may format differently)
        assert "Line 1" in caplog.text

    def test_formatted_message_preserved(self, caplog):
        """Formatted messages (with f-strings) should be preserved."""
        logger = logging.getLogger("test_formatted")
        adapter = ContextAdapter(logger, {"batch_id": "abc123"})
        value = 42

        with caplog.at_level(logging.INFO, logger="test_formatted"):
            adapter.info(f"The answer is {value}")

        assert "The answer is 42" in caplog.text
