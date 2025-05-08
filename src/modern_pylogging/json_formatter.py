import datetime as dt
import logging
import socket
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from traceback import format_tb
from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias, cast

from modern_pylogging import import_checker
from modern_pylogging.config_api import _get_default_json_dumps_module
from modern_pylogging.contextvars_helpers import get_log_extra
from modern_pylogging.helper_utils import get_env

if import_checker.is_picologging_installed:
    import picologging

if TYPE_CHECKING:
    LogRecord: TypeAlias = logging.LogRecord | picologging.LogRecord  # type:ignore[possibly-undefined]


# skip default LogRecord attributes
RESERVED_ATTRS: Final[set[str]] = {  # noqa: WPS407
    'args',
    'asctime',
    'created',
    'exc_info',
    'filename',
    'funcName',
    'levelname',
    'levelno',
    'lineno',
    'message',
    'module',
    'msecs',
    'msg',
    'name',
    'pathname',
    'process',
    'processName',
    'relativeCreated',
    'stack_info',
    'thread',
    'threadName',
    'taskName',
    'binded_ctx_extra',  # from QueueHandlerContextVarsHappyPy312
}


def grab_record_extra_fields(record: 'LogRecord', reserved: set[str]) -> dict[str, Any]:
    """Extracts extra attributes from LogRecord object."""
    extra_fields = {}
    for key, value in record.__dict__.items():  # noqa: WPS110
        if key in reserved:
            continue
        # this allows to have numeric keys
        if hasattr(key, 'startswith') and key.startswith('_'):
            continue
        extra_fields[key] = value
    return extra_fields


def provide_json_dumps_func(json_dumps_module: Literal['json', 'orjson']) -> Callable[[Any], str]:
    if json_dumps_module == 'orjson':
        from modern_pylogging.orjson_helper import json_dumps

        return json_dumps
    from modern_pylogging.json_helper import json_dumps

    return json_dumps


class JsonFormatterMixin:
    def __init__(
        self,
        *args: Any,
        json_dumps_module: Literal['json', 'orjson'] | None = None,
        capture_extra_fields: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        json_dumps_module = json_dumps_module or _get_default_json_dumps_module()
        self.json_dumps = provide_json_dumps_func(json_dumps_module)
        self.capture_extra_fields = capture_extra_fields

    def format(self, record: 'LogRecord') -> str:
        message = self._prepare_log_dict(record)
        return self.json_dumps(message)

    def _prepare_log_extra(self, record: 'LogRecord') -> dict[str, Any]:
        extra = get_log_extra()
        if extra:
            return extra
        if hasattr(record, 'binded_ctx_extra'):
            return cast('dict[str, Any]', record.binded_ctx_extra)
        return {}

    def _prepare_log_dict(self, record: 'LogRecord') -> dict[str, Any]:  # noqa: WPS210
        log_record: dict[str, Any] = {}
        log_record['timestamp'] = timestamp_to_iso(record.created)
        log_record['level'] = record.levelname
        log_record['message'] = record.getMessage()
        log_record['params'] = {
            'call_filepath': f'{record.pathname}:{record.lineno}',
            'logger_name': record.name,
        }
        if record.exc_info:
            exc_type, exc_value, tb = record.exc_info
            log_record['error'] = {
                'code': exc_type.__class__.__name__,
                'message': repr(exc_value),
                'stack': format_tb(tb),
                'params': {},
            }
        default_data = get_logging_defaults()
        extra_request_data = self._prepare_log_extra(record)
        update_fields_with_nested(log_record, default_data)
        update_fields_with_nested(log_record, extra_request_data)
        if self.capture_extra_fields:
            local_extra_fields = grab_record_extra_fields(record, reserved=RESERVED_ATTRS | set(default_data))
            update_fields_with_nested(log_record, local_extra_fields)
        return log_record


class JsonFormatterLogging(JsonFormatterMixin, logging.Formatter):
    """Formatter to use with stdin logging library"""


if import_checker.is_picologging_installed:

    class JsonFormatterPicologging(JsonFormatterMixin, picologging.Formatter):
        """Formatter for use with picologging library"""


def timestamp_to_iso(timestamp: float) -> str:
    return (
        dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
        .isoformat(timespec='milliseconds')
        .replace('+00:00', 'Z')
    )


@lru_cache(maxsize=1)
def get_logging_defaults() -> dict[str, Any]:
    """Reads default env variables. This vars stays the same between restarts."""
    return {
        'env': get_env(['ENV', 'LOGGING_ENV'], 'dev'),
        'system': get_env(['LOGGING_SYSTEM', 'APP_NAME'], Path.cwd().name),
        'inst': get_env(['POD_NAME', 'LOGGING_INST'], socket.gethostname()),
    }


def update_fields_with_nested(
    source_data: dict[str, Any],
    updated_fields: dict[str, Any],
) -> dict[str, Any]:
    """
    Update a keys in a dictionary.
    If patch to the key contains dots it means nested dictionary.
    Creates new nested dictionaries if necessary.
    'a.b.c': 'hello' -> {'a': {'b': {'c': 'hello'}}}
    """
    for field_name, field_value in updated_fields.items():
        here = source_data
        keys = field_name.split('.')
        for key in keys[:-1]:
            here = here.setdefault(key, {})
        here[keys[-1]] = field_value
    return source_data
