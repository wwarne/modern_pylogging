import atexit
import contextlib
import logging
import sys
from collections.abc import Generator
from typing import Any

import picologging
from _pytest.logging import LogCaptureHandler, _LiveLoggingNullHandler

if sys.version_info >= (3, 12):
    getHandlerByName = logging.getHandlerByName  # noqa: N816
else:

    def getHandlerByName(name: str) -> Any:  # noqa: N802
        return logging._handlers.get(name)  # type:ignore[attr-defined]


@contextlib.contextmanager
def cleanup_logging_impl() -> Generator[None, None, None]:
    # Reset logging settings (`logging` module)
    # - delete non-standart loggers created by logging.getLogger in tests
    # - remove all handlers except pytest's ones
    # - stop queue_handler listener
    # so tests could configure logging without affecting each other
    std_root_logger: logging.Logger = logging.getLogger()
    name_of_loggers_exist_on_start = set(std_root_logger.manager.loggerDict)
    for std_handler in std_root_logger.handlers:
        # Do not interfere with pytest handler config
        if not isinstance(std_handler, (_LiveLoggingNullHandler, LogCaptureHandler)):
            std_root_logger.removeHandler(std_handler)

    # reset root logger (`picologging` module)
    pico_root_logger: picologging.Logger = picologging.getLogger()
    for pico_handler in pico_root_logger.handlers:
        pico_root_logger.removeHandler(pico_handler)

    yield

    # Stop queue_handler's listener (mandatory for the 'logging' module with Python 3.12,
    # else the test suite would hand on at the end of the tests and some tests would fail)
    queue_listener_handler = getHandlerByName('queue_handler')
    if queue_listener_handler and hasattr(queue_listener_handler, 'listener'):
        atexit.unregister(queue_listener_handler.listener.stop)
        queue_listener_handler.listener.stop()
        queue_listener_handler.close()
        del queue_listener_handler  # noqa: WPS420

    name_of_loggers_exist_on_end = set(std_root_logger.manager.loggerDict)
    for name in name_of_loggers_exist_on_end - name_of_loggers_exist_on_start:
        std_root_logger.manager.loggerDict.pop(name)
