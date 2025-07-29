import logging
from typing import Any

from _pytest.logging import LogCaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from modern_pylogging.logging_manager import (
    fallback_logger,
    get_logger,
    setup_proxy_loggers,
)


class DummyLogger:
    """Logger that records method calls."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, str]] = []

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa:ARG002
        self.calls.append(('info', msg))

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa:ARG002
        self.calls.append(('debug', msg))

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa:ARG002
        self.calls.append(('error', msg))

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:  # noqa:ARG002
        self.calls.append(('error', msg))


def dummy_factory(name: str) -> DummyLogger:
    return DummyLogger(name)


def test_logger_returns_fallback_before_setup(monkeypatch: MonkeyPatch) -> None:
    # Capture fallback logs
    buffer = []
    monkeypatch.setattr(
        fallback_logger,
        'error',
        lambda msg, *a, **kw: buffer.append(msg),  # noqa:ARG005,WPS111
    )

    logger = get_logger('fallback_test')
    logger.info('Should go to fallback')

    # Ensure error was logged to fallback
    assert any('Logging is not set up yet' in msg for msg in buffer)


def test_logger_returns_dummy_after_setup() -> None:
    setup_proxy_loggers(dummy_factory)  # type:ignore[arg-type]
    logger = get_logger('dummy_test')

    logger.debug('Debug Message')
    logger.info('Info Message')

    # we know real_logger attribute exists here
    real_logger = logger.real_logger  # type:ignore[attr-defined]
    assert isinstance(real_logger, DummyLogger)
    assert real_logger.calls == [
        ('debug', 'Debug Message'),
        ('info', 'Info Message'),
    ]


def test_existing_proxy_updated_on_setup() -> None:
    # Create logger before setup
    logger = get_logger('pre_setup_update_test')
    # Should fallback here + # we know real_logger attribute exists here
    assert isinstance(logger.real_logger, logging.Logger)  # type:ignore[attr-defined]

    # Now setup with dummy
    setup_proxy_loggers(dummy_factory)  # type:ignore[arg-type]

    logger.info('Now it uses dummy')

    real = logger.real_logger  # type:ignore[attr-defined]
    assert isinstance(real, DummyLogger)
    assert real.calls[-1] == ('info', 'Now it uses dummy')


def test_logger_registry_reuse() -> None:
    setup_proxy_loggers(dummy_factory)  # type:ignore[arg-type]
    l1 = get_logger('shared_test')
    l2 = get_logger('shared_test')

    assert l1 is l2
    assert isinstance(l1.real_logger, DummyLogger)  # type:ignore[attr-defined]


def test_fallback_logs_visible_to_stdout(caplog: LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        logger = get_logger('fallback_visible_test')
        logger.warning('Before setup')  # proxy triggers fallback
        assert 'Logging is not set up yet' in caplog.text
