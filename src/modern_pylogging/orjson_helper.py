from typing import Any

from modern_pylogging import import_checker
from modern_pylogging.helper_utils import MissingDependencyError

if import_checker.is_orjson_installed:
    import orjson
else:
    raise MissingDependencyError('orjson')


def default(obj_to_serialize: Any) -> Any:
    """See https://github.com/ijl/orjson#default for information."""
    if isinstance(obj_to_serialize, set):
        return list(obj_to_serialize)
    raise TypeError


def json_dumps(obj_to_serialize: Any) -> str:
    # orjson.dumps returns bytes, to match standart json.dumps we need to decode
    return orjson.dumps(obj_to_serialize, default=default).decode()
