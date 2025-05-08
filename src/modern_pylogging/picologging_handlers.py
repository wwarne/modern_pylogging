import atexit
import sys
from queue import Queue
from typing import IO, Any

from modern_pylogging.helper_utils import MissingDependencyError, resolve_handlers

try:
    import picologging
    from picologging.handlers import QueueHandler
except ImportError as err:
    raise MissingDependencyError('picologging') from err


class PicoStreamHandlerToStdout(picologging.StreamHandler):  # type:ignore[type-arg]
    """
    By default the class picologging.StreamHandler does not support 'stream' parameter.
    It puts all output straight in sys.stderr
    So I needed a little wrapper which can get 'stream' parameter and initialize StreamHandler
    """

    def __init__(self, stream: IO[bytes | str]) -> None:  # type:ignore[type-var] # noqa: WPS612
        super().__init__(stream)


class QueueListenerHandler(QueueHandler):
    """Configure queue listener and handler to support non-blocking logging configuration."""

    def __init__(
        self,
        handlers: list[Any] | None = None,
    ) -> None:
        # handlers are ConvertingList (from logging.config
        super().__init__(Queue(-1))
        """
        In the builtin logging setup, when configured through a DictConfig
        the ConvertingList entity is passed to the handlers.
        After going through the resolve_handlers process,
        it is converted into a handler object based on the configuration.
        For example, the default configuration includes a `console` handler like this
        ['console'] and it resolves into [<StreamHandler (NOTSET)>] (python object of StreamHandler).
        However, in picologging, for some inexplicable reason,
        the ConvertingList is illogically converted into a list of strings.
        So ['console'] becomes ['console'] instead of being converted to the appropriate handler object.
        That's why in picologging config I didn't use `handlers` parameter.
        """
        handlers = resolve_handlers(handlers) if handlers else [picologging.StreamHandler(sys.stdout)]
        self.listener = picologging.handlers.QueueListener(self.queue, *handlers)
        self.listener.start()
        atexit.register(self.listener.stop)
