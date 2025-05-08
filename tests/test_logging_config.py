import json
import logging
import sys
import time
from importlib.util import find_spec
from queue import Queue
from types import ModuleType
from typing import Any, cast

import picologging
import pytest
from _pytest.capture import CaptureFixture
from pytest_mock import MockerFixture

from modern_pylogging import logging_handlers, picologging_handlers
from modern_pylogging.config_api import (
    LoggingConfig,
    _get_default_handlers,
    _get_default_json_dumps_module,
    _get_default_logging_module,
    default_handlers,
    default_picologging_handlers,
)
from modern_pylogging.json_formatter import JsonFormatterLogging, JsonFormatterPicologging


def test_get_default_handlers() -> None:
    assert _get_default_handlers(logging_module='logging') == default_handlers
    assert _get_default_handlers(logging_module='picologging') == default_picologging_handlers


def test_get_default_logging_module(mocker: MockerFixture) -> None:
    assert find_spec('picologging')  # should be installed in the test env, simply checking
    assert _get_default_logging_module() == 'picologging'
    mock = mocker.patch('modern_pylogging.config_api.import_checker')
    mock.is_picologging_installed = False
    assert _get_default_logging_module() == 'logging'


def test_get_default_json_module(mocker: MockerFixture) -> None:
    assert find_spec('orjson')  # should be installed in the test env, simply checking
    assert _get_default_json_dumps_module() == 'orjson'
    mock = mocker.patch('modern_pylogging.config_api.import_checker')
    mock.is_orjson_installed = False
    assert _get_default_json_dumps_module() == 'json'


@pytest.mark.parametrize(
    ('logging_module', 'dict_config_callable', 'expected_called'),
    [
        ('logging', 'logging.config.dictConfig', True),
        ('logging', 'picologging.config.dictConfig', False),
        ('picologging', 'picologging.config.dictConfig', True),
        ('picologging', 'logging.config.dictConfig', False),
    ],
)
def test_correct_dict_config_called(
    logging_module: str,
    dict_config_callable: str,
    expected_called: bool,  # noqa: FBT001
    mocker: MockerFixture,
) -> None:
    dict_config_mock = mocker.patch(dict_config_callable)
    LoggingConfig(logging_module=logging_module).configure()  # type:ignore[arg-type]
    assert dict_config_mock.called is expected_called


@pytest.mark.parametrize(
    ('picologging_installed', 'expected_default_handlers'),
    [(True, default_picologging_handlers), (False, default_handlers)],
)
def test_correct_default_handlers_set(
    picologging_installed: bool,  # noqa: FBT001
    expected_default_handlers: dict[str, dict[str, Any]],
    mocker: MockerFixture,
) -> None:
    mock = mocker.patch('modern_pylogging.config_api.import_checker')
    mock.is_picologging_installed = picologging_installed
    log_config = LoggingConfig()._prepare_config_dict()
    assert log_config['handlers'] == expected_default_handlers


@pytest.mark.parametrize(('orjson_exists', 'json_module_name'), [(True, 'orjson'), (False, 'json')])
def test_correct_json_module_set(
    orjson_exists: bool,  # noqa: FBT001
    json_module_name: str,
    mocker: MockerFixture,
) -> None:
    mock = mocker.patch('modern_pylogging.config_api.import_checker')
    mock.is_orjson_installed = orjson_exists
    log_config = LoggingConfig()._prepare_config_dict()
    assert log_config['formatters']['json_fmt']['json_dumps_module'] == json_module_name


@pytest.mark.parametrize(
    ('logging_module', 'expected_handlers'),
    [('picologging', default_picologging_handlers), ('logging', default_handlers)],
)
def test_correct_handlers_set_by_param(
    logging_module: str,
    expected_handlers: dict[str, dict[str, Any]],
) -> None:
    log_config = LoggingConfig(logging_module=logging_module)._prepare_config_dict()  # type:ignore[arg-type]
    assert log_config['handlers'] == expected_handlers


@pytest.mark.parametrize(('json_module_name', 'expected_module_name'), [('orjson', 'orjson'), ('json', 'json')])
def test_correct_json_module_set_by_param(
    json_module_name: str,
    expected_module_name: dict[str, dict[str, Any]],
) -> None:
    log_config = LoggingConfig(json_dumps_module=json_module_name)._prepare_config_dict()  # type: ignore[arg-type]
    assert log_config['formatters']['json_fmt']['json_dumps_module'] == expected_module_name


def test_capture_extra_fields_cannot_be_used_with_picologging() -> None:  # noqa: WPS118
    log_config = LoggingConfig(logging_module='picologging', capture_extra_fields=True)._prepare_config_dict()
    assert log_config['formatters']['json_fmt']['capture_extra_fields'] is False


@pytest.mark.parametrize(
    ('logging_module', 'expected_handler_class', 'expected_listener_class'),
    [
        (
            logging,
            logging_handlers.QueueHandlerContextVarsHappyPy312
            if sys.version_info >= (3, 12, 0)
            else logging_handlers.QueueListenerHandler,
            logging_handlers.LoggingQueueListener,
        ),
        (
            picologging,
            picologging_handlers.QueueListenerHandler,
            picologging.handlers.QueueListener,
        ),
    ],
)
def test_default_queue_listener_handler(
    logging_module: ModuleType,
    expected_handler_class: Any,
    expected_listener_class: Any,
    capsys: CaptureFixture[str],
) -> None:
    get_logger = LoggingConfig(
        logging_module=logging_module.__name__,  # type:ignore[arg-type]
        formatters={'standard': {'format': '%(levelname)s :: %(name)s :: %(message)s'}},
        loggers={
            'test_logger': {
                'level': 'INFO',
                'handlers': ['queue_handler'],
                'propagate': False,
            },
        },
        override_formatters={
            'queue_handler': 'standard',
            'console': 'standard',
        },
    ).configure()

    logger = get_logger('test_logger')
    assert isinstance(logger, logging_module.Logger)

    handler = logger.handlers[0]
    assert isinstance(handler, expected_handler_class)
    assert isinstance(handler.queue, Queue)

    assert isinstance(handler.listener, expected_listener_class)
    assert isinstance(handler.listener.handlers[0], logging_module.StreamHandler)

    logger.info('Testing now!')
    assert_log(capsys, handler.queue, expected='INFO :: test_logger :: Testing now!', count=1)

    var = 'test_var'
    logger.info('%s', var)
    assert_log(capsys, handler.queue, expected='INFO :: test_logger :: test_var', count=1)


@pytest.mark.parametrize(
    ('logging_module', 'expected_handler_class'),
    [
        (
            logging,
            logging_handlers.QueueHandlerContextVarsHappyPy312
            if sys.version_info >= (3, 12, 0)
            else logging_handlers.QueueListenerHandler,
        ),
        (picologging, picologging_handlers.QueueListenerHandler),
    ],
)
def test_default_logger_and_handler(logging_module: ModuleType, expected_handler_class: Any) -> None:
    get_logger = LoggingConfig(logging_module=logging_module.__name__).configure()  # type:ignore[arg-type]

    root_logger = get_logger()

    assert isinstance(root_logger, logging_module.Logger)
    assert root_logger.name == 'root'
    assert isinstance(root_logger.handlers[0], expected_handler_class)
    assert root_logger.handlers[0].name == 'queue_handler'


@pytest.mark.parametrize('logging_module', [logging, picologging, None])
def test_default_handlers_formatters(logging_module: ModuleType | None) -> None:
    if logging_module is None:
        config = LoggingConfig(
            formatters={},
            handlers={},
            loggers={},
        )._prepare_config_dict()
        expected_default_handlers = _get_default_handlers(_get_default_logging_module())
    else:
        config = LoggingConfig(
            logging_module=logging_module.__name__,  # type:ignore[arg-type]
            formatters={},
            handlers={},
            loggers={},
        )._prepare_config_dict()
        expected_default_handlers = _get_default_handlers(logging_module.__name__)

    assert config['formatters']['json_fmt']
    assert len(config['formatters']) == 2
    assert config['handlers']['queue_handler'] == expected_default_handlers['queue_handler']
    assert config['handlers']['console'] == expected_default_handlers['console']
    assert len(config['handlers']) == 2


@pytest.mark.parametrize(
    ('logging_module', 'expected_handler_class'),
    [
        (
            logging,
            logging_handlers.QueueHandlerContextVarsHappyPy312
            if sys.version_info >= (3, 12, 0)
            else logging_handlers.QueueListenerHandler,
        ),
        (picologging, picologging_handlers.QueueListenerHandler),
    ],
)
def test_customizing_handler(
    logging_module: ModuleType,
    expected_handler_class: Any,
    capsys: CaptureFixture[str],
) -> None:
    log_format = '%(levelname)s :: %(name)s :: %(message)s'
    # picologging seems to be broken, cannot make it log on stdout?
    # https://github.com/microsoft/picologging/issues/205
    if logging_module == picologging:
        console_stdout_class = 'modern_pylogging.picologging_handlers.PicoStreamHandlerToStdout'
    else:
        console_stdout_class = f'{logging_module.__name__}.StreamHandler'
    get_logger = LoggingConfig(
        logging_module=logging_module.__name__,  # type:ignore[arg-type]
        formatters={'standard': {'format': log_format}},
        handlers={
            'console_stdout': {
                'class': console_stdout_class,
                'stream': 'ext://sys.stdout',
                'level': 'DEBUG',
                'formatter': 'standard',
            }
        },
        loggers={
            'test_logger': {
                'level': 'DEBUG',
                'handlers': ['console_stdout'],
                'propagate': False,
            }
        },
    ).configure()

    root_logger = get_logger()
    assert isinstance(root_logger, logging_module.Logger)
    assert root_logger.level == logging_module.INFO

    root_handler = root_logger.handlers[0]
    assert root_handler.name == 'queue_handler'
    assert isinstance(root_handler, expected_handler_class)

    if isinstance(root_handler, logging_handlers.QueueHandlerContextVarsHappyPy312):
        root_formatter = root_handler.listener.handlers[0].formatter  # type:ignore[union-attr,unused-ignore,attr-defined]
    else:
        root_formatter = root_handler.formatter
    assert isinstance(root_formatter, (JsonFormatterLogging, JsonFormatterPicologging))

    t_logger = get_logger('test_logger')
    assert isinstance(t_logger, logging_module.Logger)
    assert t_logger.level == logging_module.DEBUG
    assert len(t_logger.handlers) == 1
    if logging_module == picologging:
        assert isinstance(t_logger.handlers[0], picologging_handlers.PicoStreamHandlerToStdout)
    else:
        assert isinstance(t_logger.handlers[0], logging_module.StreamHandler)

    assert t_logger.handlers[0].name == 'console_stdout'
    assert t_logger.handlers[0].formatter._fmt == log_format

    t_logger.info("Hello from '%s'", logging_module.__name__)
    log_output = capsys.readouterr().out.strip()
    assert log_output == f"INFO :: {t_logger.name} :: Hello from '{logging_module.__name__}'"


@pytest.mark.parametrize('logging_module', [logging, picologging])
def test_excluded_fields(logging_module: ModuleType, mocker: MockerFixture) -> None:
    # according to https://docs.python.org/3/library/logging.config.html#dictionary-schema-details
    allowed_fields = {
        'version',
        'formatters',
        'filters',
        'handlers',
        'loggers',
        'root',
        'incremental',
        'disable_existing_loggers',
        # 'level',
        # plus our custom
        # 'json_dumps_module'
    }
    mocked = mocker.patch(f'{logging_module.__name__}.config.dictConfig')
    LoggingConfig(logging_module=logging_module.__name__).configure()  # type:ignore[arg-type]
    assert mocked.called
    for key in mocked.call_args.args[0]:
        assert key in allowed_fields


@pytest.mark.parametrize(
    ('json_module', 'expected_json_func'),
    [
        ('json', 'modern_pylogging.json_helper.json_dumps'),
        ('orjson', 'modern_pylogging.orjson_helper.json_dumps'),
    ],
)
def test_json_formatter_uses_json_func(
    json_module: str,
    expected_json_func: str,
    mocker: MockerFixture,
) -> None:
    mocked = mocker.patch(expected_json_func)
    mocked.return_value = '{"msg": "ok"}'
    get_logger = LoggingConfig(
        logging_module='logging',
        json_dumps_module=json_module,  # type:ignore[arg-type]
        root={'handlers': ['console']},
    ).configure()
    logger = get_logger('test_logger')
    logger.info('Hello from %s', json_module)

    assert mocked.called
    assert mocked.call_args.args[0]['message'] == f'Hello from {json_module}'


def test_default_queue_listener_handler_json_fmt_extra(capsys: CaptureFixture[str]) -> None:  # noqa: WPS118
    """
    Test that we can do logger.info('msg', extra={'hehe': 'pepe'})
    and if configure logging with `capture_extra_fields` option
    these extra parameters will be passed to the logging formatter
    and will be present in json log (but only for logrecord in which they were provided)
    """
    get_logger = LoggingConfig(
        capture_extra_fields=True,
        logging_module='logging',
        loggers={'test_logger': {'level': 'INFO', 'handlers': ['queue_handler'], 'propagate': False}},
        # propagate=False will save us from doubled logs
        override_formatters={'queue_handler': 'json_fmt'},
    ).configure()
    logger = get_logger('test_logger')
    handler = logger.handlers[0]  # type:ignore[attr-defined]
    logger.info(
        'Testing one!',
        extra={'simple': 'some text', 'nested.id': 'n_id', 'nested.msg': 'n_msg', 'params.additional': 'something'},
    )
    log_entry = capture_json_log(capsys, handler.queue)

    assert log_entry['simple'] == 'some text'
    assert log_entry['nested'] == {
        'id': 'n_id',
        'msg': 'n_msg',
    }
    assert log_entry['params']['additional'] == 'something'
    assert log_entry['params']['logger_name'] == 'test_logger'  # update_log_extra does not delete existing keys

    # logging with extra={} does not affect the following log records
    logger.info('Testing two!')
    log_entry = capture_json_log(capsys, handler.queue)
    assert 'simple' not in log_entry
    assert 'nested' not in log_entry
    assert 'additional' not in log_entry['params']


def wait_log_queue(queue: Any, sleep_time: float = 0.1, max_retries: int = 5) -> None:
    retry = 0
    while queue.qsize() > 0 and retry < max_retries:
        retry += 1
        time.sleep(sleep_time)


def capture_json_log(capsys: CaptureFixture[str], queue: Any) -> dict[str, Any]:
    wait_log_queue(queue)
    log_output = (
        capsys.readouterr().out.strip()
    )  # we log to stdout by default instead of stderr (even with picologging)
    return cast('dict[str, Any]', json.loads(log_output))


def assert_log(capsys: CaptureFixture[str], queue: Any, expected: str, count: int | None = None) -> None:
    wait_log_queue(queue)
    log_output = capsys.readouterr().out.strip()  # we log to stdout by default instead of stderr
    if count is not None:
        assert len(log_output.split('\n')) == count
    assert log_output == expected
