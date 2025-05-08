"""
Functions to set context for async task and its children.
Article about it - https://habr.com/ru/companies/yandex/articles/526322/
"""

import copy
from contextvars import ContextVar
from typing import Any

_log_extra_data: ContextVar[dict[str, Any]] = ContextVar('_log_extra_data')


def set_log_extra(log_extra: dict[str, Any]) -> None:
    _log_extra_data.set(log_extra)


def get_log_extra(should_copy: bool = False) -> dict[str, Any]:  # noqa: FBT001,FBT002
    try:
        extra = _log_extra_data.get()
    except LookupError:
        # sometimes we log from background tasks, etc...
        # so contextvar wouldn't be set before
        # to avoid explicit checks I decided just to use try-except here
        extra = {}
    if should_copy:
        return copy.deepcopy(extra)
    return extra


def update_log_extra(updates: dict[str, Any]) -> None:
    # Our _log_extra contextvar contains mutable nested object (dict)
    # We need that any updates would propagate to child tasks,
    # but not to the parents - because of that we use get with copying
    current_extra = get_log_extra(should_copy=True)
    set_log_extra(current_extra | updates)
