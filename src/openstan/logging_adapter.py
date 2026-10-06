"""Logger adapter for injecting contextual information into log messages.

Provides:
1. ContextAdapter: Custom LoggerAdapter for batch/project/session context
2. WorkflowStepTracker: Multi-step workflow logging with progress tracking
"""

import logging
from collections.abc import MutableMapping
from typing import Any

__all__ = ["ContextAdapter", "WorkflowStepTracker"]


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter for injecting batch/project/session context into log messages.

    Automatically prepends context key-value pairs to all log messages in the
    format: [key1=value1|key2=value2] message

    None values are skipped (not included in output), allowing optional context.

    Example:
        >>> _logger = ContextAdapter(
        ...     logging.getLogger(__name__),
        ...     {'batch_id': '12345', 'project_id': 'proj-xyz'}
        ... )
        >>> _logger.error("Failed to process")
        # Output: [batch_id=12345|project_id=proj-xyz] Failed to process

        >>> _logger = ContextAdapter(
        ...     logging.getLogger(__name__),
        ...     {'batch_id': None, 'project_id': 'proj-xyz'}
        ... )
        >>> _logger.error("Failed to process")
        # Output: [project_id=proj-xyz] Failed to process
    """

    def process(
        self, msg: Any, kwargs: MutableMapping[str, Any]
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Inject context into log message.

        Args:
            msg: The log message
            kwargs: Additional keyword arguments for the logger

        Returns:
            Tuple of (modified_message, kwargs) for logging framework
        """
        extras = []
        extra = self.extra if self.extra else {}
        for key, value in extra.items():
            if value is not None:
                extras.append(f"{key}={value}")

        if extras:
            prefix = "[" + "|".join(extras) + "] "
            return f"{prefix}{msg}", kwargs
        return msg, kwargs


class WorkflowStepTracker:
    """Tracks multi-step workflows with explicit step-by-step logging.

    Provides visual progress tracking with step counters and completion markers
    for any multi-step operation (batch cleanup, imports, exports, anonymisation, etc.).

    Example output:
        [batch_id=abc123|project_id=proj-xyz] Export Data [Step 1/5] Fetching records...
        [batch_id=abc123|project_id=proj-xyz] Export Data [✓ Step 1/5]
        [batch_id=abc123|project_id=proj-xyz] Export Data [Step 2/5] Formatting output...
        [batch_id=abc123|project_id=proj-xyz] Export Data [✓ Step 2/5]
        [batch_id=abc123|project_id=proj-xyz] Export Data [Step 3/5] Writing file...
        [batch_id=abc123|project_id=proj-xyz] Export Data [✗ Step 3/5] Disk full error

    Attributes:
        workflow_name: Human-readable workflow name (e.g., "Export Data", "Anonymise PDF")
        total_steps: Total number of steps in the workflow
        current_step: Current step number (incremented by start_step)
        ctx_logger: ContextAdapter with project_id and optional batch_id for traceability
    """

    def __init__(
        self,
        workflow_name: str,
        total_steps: int,
        project_id: str,
        batch_id: str | None = None,
    ) -> None:
        """Initialize the workflow step tracker.

        Args:
            workflow_name: Human-readable name (e.g., "Export Data", "Anonymise Batch")
            total_steps: Total number of sequential steps in this workflow
            project_id: Project identifier for context (always included in logs)
            batch_id: Optional batch identifier (only included if not None)

        Example:
            >>> tracker = WorkflowStepTracker("Export Data", 3, project_id="proj-xyz")
            >>> tracker.start_step("Fetching records from database")
            >>> # ... do work ...
            >>> tracker.complete_step()
            >>> tracker.start_step("Formatting CSV output")
            >>> # ... do work ...
            >>> tracker.complete_step()
        """
        self.workflow_name = workflow_name
        self.total_steps = total_steps
        self.project_id = project_id
        self.batch_id = batch_id
        self.current_step = 0

        # Get base logger and create context adapter with optional batch_id
        base_logger = logging.getLogger(__name__)
        self.ctx_logger = ContextAdapter(
            base_logger,
            {"batch_id": batch_id, "project_id": project_id},
        )

    def start_step(self, description: str) -> None:
        """Log the start of a step.

        Increments the step counter and logs the step description.

        Args:
            description: What this step does (e.g., "Fetching records from database")

        Example:
            >>> tracker.start_step("Writing output file")
            # Logs: Export Data [Step 1/3] Writing output file
        """
        self.current_step += 1
        msg = f"{self.workflow_name} [Step {self.current_step}/{self.total_steps}] {description}"
        self.ctx_logger.info(msg)

    def complete_step(self) -> None:
        """Log successful completion of the current step.

        Example:
            >>> tracker.complete_step()
            # Logs: Export Data [✓ Step 1/3]
        """
        msg = f"{self.workflow_name} [✓ Step {self.current_step}/{self.total_steps}]"
        self.ctx_logger.info(msg)

    def error_step(self, error_message: str) -> None:
        """Log an error in the current step.

        Args:
            error_message: Error description (e.g., "Disk full", "Database connection lost")

        Example:
            >>> tracker.error_step("Connection timeout after 30s")
            # Logs: Export Data [✗ Step 1/3] Connection timeout after 30s
        """
        msg = f"{self.workflow_name} [✗ Step {self.current_step}/{self.total_steps}] {error_message}"
        self.ctx_logger.error(msg)
