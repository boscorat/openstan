"""Unit tests for logging_adapter module.

Tests core behavior of ContextAdapter including:
- Context key-value injection with proper formatting
- None value filtering (optional context)
- Empty context handling
- Message preservation

Also tests WorkflowStepTracker:
- Step counter increment
- Message formatting for start/complete/error steps
- Context injection with and without batch_id
"""

import logging

from openstan.logging_adapter import ContextAdapter, WorkflowStepTracker


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


class TestWorkflowStepTrackerBasic:
    """Tests for WorkflowStepTracker basic functionality."""

    def test_step_counter_increments(self, caplog):
        """Step counter should increment from 1 to N."""
        tracker = WorkflowStepTracker(
            workflow_name="Test Workflow",
            total_steps=3,
            project_id="proj-123",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Step 1 description")
            assert tracker.current_step == 1
            tracker.start_step("Step 2 description")
            assert tracker.current_step == 2
            tracker.start_step("Step 3 description")
            assert tracker.current_step == 3

    def test_start_step_message_format(self, caplog):
        """start_step should log '[Step n/total] description'."""
        tracker = WorkflowStepTracker(
            workflow_name="Export Data",
            total_steps=2,
            project_id="proj-xyz",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Fetching records")

        assert "Export Data [Step 1/2] Fetching records" in caplog.text

    def test_complete_step_message_format(self, caplog):
        """complete_step should log '[✓ Step n/total]'."""
        tracker = WorkflowStepTracker(
            workflow_name="Export Data",
            total_steps=2,
            project_id="proj-xyz",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Fetching records")
            tracker.complete_step()

        assert "Export Data [✓ Step 1/2]" in caplog.text

    def test_error_step_message_format(self, caplog):
        """error_step should log '[✗ Step n/total] error_message'."""
        tracker = WorkflowStepTracker(
            workflow_name="Export Data",
            total_steps=2,
            project_id="proj-xyz",
        )

        with caplog.at_level(logging.ERROR):
            tracker.start_step("Fetching records")
            tracker.error_step("Disk full")

        assert "Export Data [✗ Step 1/2] Disk full" in caplog.text


class TestWorkflowStepTrackerContext:
    """Tests for WorkflowStepTracker context injection."""

    def test_project_id_context_included(self, caplog):
        """Project ID should be included in context prefix."""
        tracker = WorkflowStepTracker(
            workflow_name="Test",
            total_steps=1,
            project_id="proj-abc",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Step description")

        assert "[project_id=proj-abc]" in caplog.text

    def test_batch_id_included_when_provided(self, caplog):
        """Batch ID should be included in context when provided."""
        tracker = WorkflowStepTracker(
            workflow_name="Test",
            total_steps=1,
            project_id="proj-xyz",
            batch_id="batch-123",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Step description")

        assert "[batch_id=batch-123|project_id=proj-xyz]" in caplog.text

    def test_batch_id_omitted_when_none(self, caplog):
        """Batch ID should be omitted from context when None."""
        tracker = WorkflowStepTracker(
            workflow_name="Test",
            total_steps=1,
            project_id="proj-xyz",
            batch_id=None,
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Step description")

        # Should only have project_id, no batch_id in the output
        assert "[project_id=proj-xyz]" in caplog.text
        assert "batch_id" not in caplog.text


class TestWorkflowStepTrackerMultipleSteps:
    """Tests for WorkflowStepTracker with multiple steps."""

    def test_full_workflow_sequence(self, caplog):
        """Full workflow: start, complete, start, complete, start, error."""
        tracker = WorkflowStepTracker(
            workflow_name="Anonymise Batch",
            total_steps=3,
            project_id="proj-123",
            batch_id="batch-456",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Loading config")
            tracker.complete_step()

            tracker.start_step("Processing files")
            tracker.complete_step()

            tracker.start_step("Saving results")

        # Verify step counter progressed correctly
        assert tracker.current_step == 3
        assert "Anonymise Batch [Step 1/3] Loading config" in caplog.text
        assert "Anonymise Batch [✓ Step 1/3]" in caplog.text
        assert "Anonymise Batch [Step 2/3] Processing files" in caplog.text
        assert "Anonymise Batch [✓ Step 2/3]" in caplog.text
        assert "Anonymise Batch [Step 3/3] Saving results" in caplog.text

    def test_error_recovery_possible(self, caplog):
        """After error_step, tracker can still continue to next step."""
        tracker = WorkflowStepTracker(
            workflow_name="Import",
            total_steps=3,
            project_id="proj-xyz",
        )

        with caplog.at_level(logging.INFO):
            tracker.start_step("Step 1")
            tracker.error_step("Retrying...")
            tracker.start_step("Step 2 (retry)")
            tracker.complete_step()

        # Should be able to progress to step 2 after error
        assert tracker.current_step == 2
        assert "Import [✗ Step 1/3] Retrying..." in caplog.text
        assert "Import [Step 2/3] Step 2 (retry)" in caplog.text

    def test_different_workflow_names(self, caplog):
        """Different workflow names should be preserved in messages."""
        workflows = [
            ("Export Data", 2),
            ("Anonymise PDF", 3),
            ("Load Reports", 2),
        ]

        with caplog.at_level(logging.INFO):
            for name, steps in workflows:
                tracker = WorkflowStepTracker(
                    workflow_name=name,
                    total_steps=steps,
                    project_id="proj-test",
                )
                tracker.start_step("Step 1")

        for name, _ in workflows:
            assert f"{name} [Step 1/" in caplog.text
