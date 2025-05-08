import atexit
import logging
import sys
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, cast

from modern_pylogging.contextvars_helpers import get_log_extra
from modern_pylogging.helper_utils import resolve_handlers


class LoggingQueueListener(QueueListener):
    """Custom `QueueListener` that starts and stops the listening thread."""

    def __init__(
        self,
        queue: Queue[logging.LogRecord],
        *handlers: logging.Handler,
        respect_handler_level: bool = False,
    ) -> None:
        """
        Initialize a `LoggingQueueListener` instance.
        :param queue: The queue to send messages to
        :param handlers: A list of handlers whichj will handle entries placed on the queue
        :param respect_handler_level: If `respect_handler` is `True`
        a handler's level is respected (compared with the level for the message)
        when deciding whether to pass message to that handler.
        """
        super().__init__(queue, *handlers, respect_handler_level=respect_handler_level)
        self.start()
        atexit.register(self.stop)


class QueueListenerHandler(QueueHandler):
    """
    Configure queue listener and handler to support non-blocking logging configuration.

    !caution!
    This handler DOES NOT WORK with Python >= 3.12 and `logging.config.dictConfig`.
    Please use `QueueHandlerContextVarsHappyPy312`
    """

    def __init__(self, handlers: list[Any] | None = None, respect_handler_level: bool = False) -> None:  # noqa: FBT001, FBT002
        super().__init__(Queue(-1))
        handlers = resolve_handlers(handlers) if handlers else [logging.StreamHandler(stream=sys.stdout)]
        self.listener = LoggingQueueListener(
            self.queue,  # type:ignore[arg-type]
            *handlers,
            respect_handler_level=respect_handler_level,
        )


class QueueHandlerContextVarsHappyPy312(QueueHandler):
    """
    In python up to version 3.12 JsonFormatter was called in the same thread as logging
    and placed already formatted string directly into the queue.

    However, in python 3.12 this behavior was changed.
    Now, in the main thread, we simply enqueue LogRecords,
    and the queue processing is handled by QueueListener in a separate thread.
    Since ContextVars are not shared between threads, any data that was set using `update_log_extra` will be lost.
    To prevent this from happening, I created this handler and modified the JsonFormatter.
    """

    def prepare(self, record: logging.LogRecord) -> logging.LogRecord:
        record = super().prepare(record)
        record.binded_ctx_extra = get_log_extra()
        return cast('logging.LogRecord', record)
