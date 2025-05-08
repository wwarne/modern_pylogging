import os
from typing import Any, TypeVar

T = TypeVar('T')  # noqa: WPS111


def get_env(envs: list[str], default: T) -> str | T:
    """
    Tries to get a value from any env variable from the list.
    If there's no value, return default.
    :param envs: list of env variable names
    :param default: default value if all env variables is not set
    """
    env_value = None
    for env in envs:
        env_value = os.getenv(env, None)
        if env_value is not None:
            break
    if env_value is None:
        return default
    return env_value


def get_logging_level() -> str | int:
    level = get_env(['LOGGING_LEVEL'], 'INFO')
    if level.isdigit():
        return int(level)
    return level


class MissingDependencyError(ImportError):
    """
    Missing optional dependency.
    This exception is raised only when a module depends on a dependency that has not been installed.
    """

    def __init__(self, package: str, install_package: str | None = None) -> None:
        err_msg = (
            f'Package {package!r} is not installed but required. You can install it by running '  # noqa: WPS237
            f'pip install {install_package or package}'
        )
        super().__init__(err_msg)


def resolve_handlers(handlers: list[Any]) -> list[Any]:
    """
    Converts list of string of handlers to the list of object of respective handlers.

    The logging.config module uses three internal data structures to hold items
    that may need to be converted to a handler or other object.
    ConvertingList, ConvertingTuple, and ConvertingDict.

    These three objects provide interfaces to get converted items using the __getitem__ methods.

    So indexing the list performs the evaluation of the objects

    Due to missing typing in 'typeshed' we cannot type this as ConvertingList for now.
    :param handlers: An instance if 'ConvertingList'
    :return: A list of resolved handlers
    """
    return list(handlers)
