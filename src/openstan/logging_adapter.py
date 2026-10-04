"""Logger adapter for injecting contextual information into log messages.

Provides a custom LoggerAdapter subclass that prepends context information
(batch_id, project_id, session_id) to log messages for better traceability.
"""

import logging
from collections.abc import MutableMapping
from typing import Any


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
