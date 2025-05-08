import copy
import sys
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

from modern_pylogging import import_checker
from modern_pylogging.helper_types import GetLogger
from modern_pylogging.helper_utils import MissingDependencyError, get_logging_level

if TYPE_CHECKING:
    from collections.abc import Callable

    from modern_pylogging.helper_types import Logger

default_handlers: dict[str, dict[str, Any]] = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'json_fmt',
        'stream': 'ext://sys.stdout',
    },
    'queue_handler': {
        'class': 'modern_pylogging.logging_handlers.QueueListenerHandler',
        'formatter': 'json_fmt',
        'respect_handler_level': True,
    },
}
if sys.version_info >= (3, 12, 0):  # pragma: no cover
    default_handlers['queue_handler'].update({
        'class': 'modern_pylogging.logging_handlers.QueueHandlerContextVarsHappyPy312',
        'queue': {
            '()': 'queue.Queue',
            'maxsize': -1,
        },
        'listener': 'modern_pylogging.logging_handlers.LoggingQueueListener',
        'handlers': ['console'],
        'respect_handler_level': True,
    })
    # do not format twice, the console handler will do the job
    default_handlers['queue_handler'].pop('formatter')

# There's no 'handlers' parameter in queue_handler
# read about it in `picologging_handlers.QueueListenerHandler`
default_picologging_handlers: dict[str, dict[str, Any]] = {
    'console': {
        # by default the class picologging.StreamHandler does not support 'stream' parameter.
        # It puts all output straight in sys.stderr
        # So I needed a little wrapper which can get 'stream' parameter and initialize StreamHandler
        'class': 'modern_pylogging.picologging_handlers.PicoStreamHandlerToStdout',
        'formatter': 'json_fmt',
        'stream': 'ext://sys.stdout',
    },
    'queue_handler': {'class': 'modern_pylogging.picologging_handlers.QueueListenerHandler', 'formatter': 'json_fmt'},
}


def _get_default_formatters() -> dict[str, dict[str, Any]]:
    return {
        'standard': {
            '()': 'modern_pylogging.console_formatter.ConsoleFormatterLogging',
            'format': '%(asctime)s | %(levelname)s | %(name)s:%(module)s:%(lineno)s | %(message)s | %(extra_data_str)s',
        },
        'json_fmt': {
            '()': 'modern_pylogging.json_formatter.JsonFormatterLogging',
            'json_dumps_module': 'json',
        },
    }


def _get_default_logging_module() -> Literal['logging', 'picologging']:
    if import_checker.is_picologging_installed:
        return 'picologging'
    return 'logging'


def _get_default_json_dumps_module() -> Literal['json', 'orjson']:
    if import_checker.is_orjson_installed:
        return 'orjson'
    return 'json'


def _get_default_handlers(logging_module: str) -> dict[str, dict[str, Any]]:
    if logging_module == 'picologging':
        return default_picologging_handlers
    return default_handlers


@dataclass
class LoggingConfig:
    """
    Configuration class for setting default python logging system.

    Attributes:
        logging_module (Literal['logging', 'picologging']):
            Specifies the backend logging module to use. 'logging' is the standard library,
            while 'picologging' is a faster, drop-in replacement.
            'picologging' will be used by default if installed.

        json_dumps_module (Literal['json', 'orjson']):
            Module used to serialize log records to JSON format. 'orjson' provides better
            performance and type handling. 'orjson' will be used by default if installed.

        version (Literal[1]):
            Schema version for the logging configuration.
            The only valid value at present is 1

        disable_existing_loggers (bool):
            Whether to disable loggers that were previously configured before applying this config.

        filters (dict[str, dict[str, Any]] | None):
            A dict in which each key is a filter id and each value is a dict describing how to configure the
            corresponding Filter_ instance.
            https://docs.python.org/3/library/logging.html#filter-objects.

        formatters (dict[str, dict[str, Any]] | None):
            A dict in which each key is a formatter and each value is a dict describing how to configure the
            corresponding Formatter_ instance. A 'standard' and 'json_fmt' formatter is provided.
            standard - write everything as strings, good for development.
            json_fmt - write output as json, good for production.
            https://docs.python.org/3/library/logging.html#formatter-objects

        handlers (dict[str, dict[str, Any]] | None):
            A dict in which each key is a handler id and each value is a dict describing how to configure the
            corresponding Handler_ instance. Two handlers are provided, 'console' and 'queue_handler'.
            https://docs.python.org/3/library/logging.html#handler-objects

        loggers (dict[str, dict[str, Any]] | None):
            A dict in which each key is a logger name and each value is a dict describing how to configure the
            corresponding Logger_ instance.
            https://docs.python.org/3/library/logging.html#logger-objects

        root (dict[str, dict[str, Any] | list[Any] | str] | None):
            This will be the configuration for the root logger.
            Processing of the configuration will be as for any logger,
            except that the propagate setting will not be applicable.

        override_formatters (dict[HandlerName, FormatterName] | None):
            Sometimes you want just use default settings but change formatters
            (e.g. to write to console as text instead of json)
            You could provide a dict like {'console': 'default', 'queue_handler': 'default'}

        level (int | str | None):
            Optional default logging level to be applied globally (e.g., 'DEBUG', 10).

        capture_extra_fields (bool):
            Whether to capture additional fields from log records' `extra` parameter
            into the structured output (especially relevant for JSON loggers).
            This does not work for 'picologging'.
            It's where you use like this - logger.info('abc', extra={'key': 'value'})
    """

    logging_module: Literal['logging', 'picologging'] = field(default_factory=_get_default_logging_module)
    json_dumps_module: Literal['json', 'orjson'] = field(default_factory=_get_default_json_dumps_module)
    version: Literal[1] = 1
    disable_existing_loggers: bool = False
    filters: dict[str, dict[str, Any]] = field(default_factory=dict)
    formatters: dict[str, dict[str, Any]] = field(default_factory=_get_default_formatters)
    handlers: dict[str, dict[str, Any]] = field(default_factory=dict)
    loggers: dict[str, dict[str, Any]] = field(default_factory=dict)
    root: dict[str, dict[str, Any] | list[Any] | str] = field(default_factory=lambda: {'handlers': ['queue_handler']})
    override_formatters: dict[str, str] = field(default_factory=dict)
    level: int | str = field(default_factory=get_logging_level)
    capture_extra_fields: bool = False

    def __post_init__(self) -> None:  # noqa: C901, WPS231
        if self.logging_module == 'picologging' and import_checker.is_picologging_installed is False:
            raise MissingDependencyError('picologging')
        if self.json_dumps_module == 'orjson' and import_checker.is_orjson_installed is False:
            raise MissingDependencyError('orjson')
        if 'standard' not in self.formatters:
            self.formatters['standard'] = _get_default_formatters()['standard']
        if 'json_fmt' not in self.formatters:
            self.formatters['json_fmt'] = _get_default_formatters()['json_fmt']
        if 'console' not in self.handlers:
            self.handlers['console'] = _get_default_handlers(self.logging_module)['console']
        if 'queue_handler' not in self.handlers:
            self.handlers['queue_handler'] = _get_default_handlers(self.logging_module)['queue_handler']
        if self.logging_module == 'picologging':
            if self.formatters['json_fmt'].get('()', '') == 'modern_pylogging.json_formatter.JsonFormatterLogging':
                self.formatters['json_fmt']['()'] = 'modern_pylogging.json_formatter.JsonFormatterPicologging'
            if (
                self.formatters['standard'].get('()', '')
                == 'modern_pylogging.console_formatter.ConsoleFormatterLogging'
            ):
                self.formatters['standard']['()'] = 'modern_pylogging.console_formatter.ConsoleFormatterPicologging'

    def configure(self) -> GetLogger:
        config_dict = self._prepare_config_dict()
        if self.logging_module == 'picologging':
            try:
                from picologging import config, getLogger
            except ImportError as exc:
                raise MissingDependencyError('picologging') from exc
        else:
            from logging import config, getLogger  # type:ignore[assignment,no-redef]
        config.dictConfig(config_dict)
        return cast('Callable[[str], Logger]', getLogger)

    def replace_formatters(self, override_formatters: dict[str, str], source: dict[str, Any]) -> dict[str, Any]:
        if override_formatters:
            source = copy.deepcopy(source)
            # If we simply change the `source` variable, then new parameters
            # will remain in the 'default_handlers' dictionary at the module level.
            # This is generally not an issue because configuring logging multiple times
            # in a single application is unnecessary.
            #
            # However, this becomes problematic during tests
            # If I use `override_formatters` in one test, those values are automatically carried over to other tests.
            # Interestingly, this behavior only affects tests located in the same .py file.
            # It's possible that pytest loads modules from scratch for tests in different files.
            # For example, the first test sets the standard format globally using `override_formatters`
            # and verifies the console output.
            # In the same file, another tests checks if the JsonFormatter correctly calls
            # the function to dump data in JSON.
            # Since `override_formatters` is not used during the second test
            # (as json_fmt is the default formatter everythere),
            # the previous formatter settings from the first test remains, causing the second test to fail.
            # The occurrence of this failure is unpredictable
            # depending on the execution order of the tests and whether they are in the same file.
            # Debugging this issue was quite time-consumig for me.
            for handler_name, formatter_name in override_formatters.items():
                if source['handlers'][handler_name].get('formatter') is not None:
                    # if 'formatter' in values['handlers'][handler_name]:
                    source['handlers'][handler_name]['formatter'] = formatter_name
        return source

    def _prepare_config_dict(self) -> dict[str, Any]:
        config_base = {
            'version': self.version,
            'disable_existing_loggers': self.disable_existing_loggers,
            'filters': self.filters,
            'formatters': self.formatters,
            'handlers': self.handlers,
            'loggers': self.loggers,
            'root': self.root,
        }
        config_dict = {name: value for name, value in config_base.items() if value}  # noqa: WPS110
        config_dict['formatters']['json_fmt']['json_dumps_module'] = self.json_dumps_module  # type:ignore[index] # noqa: WPS204
        config_dict['formatters']['json_fmt']['capture_extra_fields'] = self.capture_extra_fields  # type:ignore[index]
        config_dict['root']['level'] = self.level  # type:ignore[index]
        if self.logging_module == 'picologging' and 'datefmt' not in config_dict['formatters']['standard']:  # type:ignore[index]
            # There is a problem in picologging with time formatting with single formatter
            # https://github.com/microsoft/picologging/issues/203
            # https://github.com/microsoft/picologging/pull/208
            config_dict['formatters']['standard']['datefmt'] = '%F %T'  # type: ignore[index]

        config_dict = self.replace_formatters(self.override_formatters, config_dict)
        _python_3_12_4_fix(config_dict)
        if self.logging_module == 'picologging' and self.capture_extra_fields:
            _picologging_and_capture_extra_fields_warning()
            config_dict['formatters']['json_fmt']['capture_extra_fields'] = False
        return config_dict


def _python_3_12_4_fix(config_dict: dict[str, Any]) -> None:  # noqa: WPS114
    if sys.version_info[:3] == (3, 12, 4):
        if 'queue' in config_dict['handlers']['queue_handler']:
            warnings.warn(
                'Python 3.12.4 has a regression bug '
                'and it fails to configure `queue` parameter for QueueHandler '
                'https://github.com/python/cpython/issues/119818',
                stacklevel=2,
            )
            config_dict['handlers']['queue_handler'].pop('queue')


def _picologging_and_capture_extra_fields_warning() -> None:
    warnings.warn(
        'log `extra` param does not work with picologging '
        'so parameter `capture_extra_fields` is disabled '
        'https://github.com/microsoft/picologging/issues/195',
        stacklevel=2,
    )
