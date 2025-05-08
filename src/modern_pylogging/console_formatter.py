import logging
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from modern_pylogging import import_checker
from modern_pylogging.contextvars_helpers import get_log_extra

if import_checker.is_picologging_installed:
    import picologging


if TYPE_CHECKING:
    LogRecord: TypeAlias = logging.LogRecord | picologging.LogRecord  # type:ignore[possibly-undefined]


class ConsoleFormatterMixin:
    def format(self, record: 'LogRecord') -> str:
        extra_data = self._prepare_log_extra(record)
        # Build key=value string
        k_v_strings = (f'{k} = {v}' for k, v in extra_data.items())  # noqa: WPS111
        extra_data_str = ', '.join(k_v_strings)
        record.extra_data_str = f'{{{extra_data_str}}}' if extra_data_str else ''  # type:ignore[union-attr]
        return cast('str', super().format(record))  # type:ignore[misc]

    def _prepare_log_extra(self, record: 'LogRecord') -> dict[str, Any]:
        extra = get_log_extra()
        if extra:
            return extra
        if hasattr(record, 'binded_ctx_extra'):
            return cast('dict[str, Any]', record.binded_ctx_extra)
        return {}


class ConsoleFormatterLogging(ConsoleFormatterMixin, logging.Formatter):
    """Class to use with stdlib logging"""


if import_checker.is_picologging_installed:

    class ConsoleFormatterPicologging(ConsoleFormatterMixin, picologging.Formatter):
        """Class to use with picologging library"""
