import json
import logging
from types import ModuleType

import picologging
import pytest

import modern_pylogging
from modern_pylogging.json_formatter import JsonFormatterLogging, JsonFormatterPicologging


@pytest.mark.parametrize('json_module', ['json', 'orjson', None])
@pytest.mark.parametrize('logging_module', [logging, picologging])
def test_formatter(json_module: str, logging_module: ModuleType) -> None:
    if logging_module.__name__ == 'picologging':
        formatter = JsonFormatterPicologging(json_dumps_module=json_module)  # type:ignore[arg-type]
    else:
        formatter = JsonFormatterLogging(json_dumps_module=json_module)  # type:ignore[arg-type,assignment]

    test_record = logging_module.LogRecord(
        'name', logging_module.INFO, 'path', lineno=1, msg='Log message %s', args=('123',), exc_info=None
    )
    expected_json = {
        'env': 'env-dev-test',
        'inst': 'pod-test',
        'system': 'system-test',
        'level': 'INFO',
        'message': 'Log message 123',
        'params': {'call_filepath': 'path:1', 'logger_name': 'name'},
    }
    decoded_json = json.loads(formatter.format(test_record))
    decoded_json.pop('timestamp')
    assert decoded_json == expected_json


@pytest.mark.parametrize('logging_module', [logging, picologging])
def test_extra_param_can_be_ignored(logging_module: ModuleType) -> None:
    """
    Test that JsonFormatter ignores parameters passed via extra={} if capture_extra_fields is disabled
    """
    formatter = JsonFormatterPicologging() if logging_module.__name__ == 'picologging' else JsonFormatterLogging()
    test_record = logging_module.LogRecord(
        'name', logging_module.INFO, 'path', lineno=1, msg='Log message %s', args=('123',), exc_info=None
    )
    # when we log like logger.info('bla bla', extra={'test_param': 'test_value'})
    # logging just adds  those parameters to LogRecord's __dict__
    test_record.__dict__['test_param'] = 'test_value'
    test_record.__dict__['request.id'] = 'some request id'

    decoded_json = json.loads(formatter.format(test_record))

    assert 'test_param' not in decoded_json
    assert 'request' not in decoded_json


@pytest.mark.parametrize('logging_module', [logging, picologging])
@pytest.mark.asyncio
async def test_extra_param_override_contextvars_params(logging_module: ModuleType) -> None:  # noqa: RUF029
    """
    Test that if capture_extra_fields is enabled them extra={} params have priority over
    modern_pylogging.update_log_extra fields stored in contextvars
    """
    modern_pylogging.update_log_extra({'test_param': 'test param from ctx_var'})
    if logging_module.__name__ == 'picologging':
        formatter = JsonFormatterPicologging(capture_extra_fields=True)
    else:
        formatter = JsonFormatterLogging(capture_extra_fields=True)  # type:ignore[assignment]
    test_record = logging_module.LogRecord(
        'name', logging_module.INFO, 'path', lineno=1, msg='Log message %s', args=('123',), exc_info=None
    )
    # when we log like logger.info('bla bla', extra={'test_param': 'test_value'})
    # logging just adds  those parameters to LogRecord's __dict__
    test_record.__dict__['test_param'] = 'test_value from extra='

    decoded_json = json.loads(formatter.format(test_record))

    assert decoded_json['test_param'] == 'test_value from extra='
