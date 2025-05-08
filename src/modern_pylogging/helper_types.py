"""
I grabbed some types straight from https://github.com/django/asgiref/blob/main/asgiref/typing.py


Copyright (c) Django Software Foundation and individual contributors.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

    1. Redistributions of source code must retain the above copyright notice,
       this list of conditions and the following disclaimer.

    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.

    3. Neither the name of Django nor the names of its contributors may be used
       to endorse or promote products derived from this software without
       specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
from collections.abc import Callable, Iterable
from typing import Any, Literal, Protocol, TypedDict

if sys.version_info >= (3, 11):
    from typing import NotRequired, TypeAlias
else:
    from typing import TypeAlias  # noqa: WPS474

    from typing_extensions import NotRequired

Method: TypeAlias = Literal['GET', 'POST', 'DELETE', 'PATCH', 'PUT', 'HEAD', 'TRACE', 'OPTIONS']


class Logger(Protocol):  # noqa: WPS214
    """Logger protocol."""

    def debug(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'DEBUG' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def info(self, event: str, *args: Any, **kwargs: Any) -> Any:  # noqa: WPS110
        """Output a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def warning(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'WARNING' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def warn(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'WARN' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def error(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'ERROR' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def fatal(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'FATAL' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def exception(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Log a message with level 'ERROR' on this logger. The arguments are interpreted as for debug(). Exception info
        is added to the logging message.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def critical(self, event: str, *args: Any, **kwargs: Any) -> Any:
        """Output a log message at 'INFO' level.

        Args:
             event: Log message.
             *args: Any args.
             **kwargs: Any kwargs.
        """

    def setLevel(self, level: int) -> None:  # noqa: N802
        """Set the log level

        Args:
            level: Log level to set as an integer

        Returns:
            None
        """


class ASGIVersions(TypedDict):
    spec_version: str
    version: Literal['2.0', '3.0']


class HTTPScope(TypedDict):
    type: Literal['http']
    asgi: ASGIVersions
    http_version: str
    method: str
    scheme: str
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Iterable[tuple[bytes, bytes]]
    client: tuple[str, int] | None
    server: tuple[str, int | None]
    state: NotRequired[dict[str, Any]]
    extensions: dict[str, dict[object, object]] | None


class WebSocketScope(TypedDict):
    type: Literal['websocket']
    asgi: ASGIVersions
    http_version: str
    scheme: str
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Iterable[tuple[bytes, bytes]]
    client: tuple[str, int] | None
    server: tuple[str, int | None] | None
    subprotocols: Iterable[str]
    state: NotRequired[dict[str, Any]]
    extensions: dict[str, dict[object, object]] | None


WWWScope: TypeAlias = HTTPScope | WebSocketScope
ExceptionLoggingHandler: TypeAlias = Callable[[Logger, WWWScope, list[str]], None]
GetLogger: TypeAlias = Callable[..., Logger]
