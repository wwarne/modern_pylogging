"""
Sometimes you don't know your settings in import time

So you can't
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, cast

from modern_pylogging.helper_types import Logger

fallback_logger = logging.getLogger('modern_pylogging.fallback')


class LoggerProxy:
    """Lazy logger object that does nothing until logging is configured.

    So we can safely do logger = get_logger(__name__) and it's safe at import time.
    During call to setup_logging function the self.factory will be replaced
    by the real function
    (getLogger from logging module or getLogger from picologging module).
    After that every call is going to be proxied to the real logger object.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._real_logger: Logger | None = None
        self.factory: Callable[[str], Logger] | None = None
        self.lock = threading.Lock()
        self.fallback_logger = fallback_logger

    @property
    def real_logger(self) -> Logger:
        if self._real_logger is None:
            with self.lock:
                if self._real_logger is None and self.factory is None:  # type: ignore[redundant-expr]
                    err_msg = 'Logging is not set up yet. Please create LoggingConfig and call configure method first'
                    self.fallback_logger.error(err_msg)
                    return self.fallback_logger
                self._real_logger = self.factory(self.name)
        return self._real_logger

    def __getattr__(self, item: str) -> Any:  # noqa: WPS110
        # Forward all attribute access to the real logger
        return getattr(self.real_logger, item)


# Global registry
_proxy_loggers: dict[str, LoggerProxy] = {}
_logger_factory: Callable[[str], Logger] | None = None


def setup_proxy_loggers(real_get_logger_fn: Callable[..., Logger]) -> None:
    global _logger_factory  # noqa: PLW0603, WPS420
    _logger_factory = real_get_logger_fn  # noqa: WPS122
    # update all existing logger proxies
    for proxy in _proxy_loggers.values():
        proxy.factory = real_get_logger_fn


def get_logger(name: str) -> Logger:
    if name not in _proxy_loggers:
        proxy = LoggerProxy(name)
        if _logger_factory:
            proxy.factory = _logger_factory
        _proxy_loggers[name] = proxy
    return cast('Logger', _proxy_loggers[name])
