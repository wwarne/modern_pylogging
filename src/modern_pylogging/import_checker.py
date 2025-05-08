from importlib.util import find_spec

is_structlog_installed = find_spec('structlog')
is_picologging_installed = find_spec('picologging')
is_orjson_installed = find_spec('orjson')
