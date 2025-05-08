import os

from modern_pylogging.helper_utils import get_logging_level
from modern_pylogging.json_formatter import get_logging_defaults


def test_get_logging_data_without_optional_envs() -> None:
    assert get_logging_defaults() == {
        'env': 'env-dev-test',
        'system': 'system-test',
        'inst': 'pod-test',
    }


def test_get_logging_level_str() -> None:
    os.environ['LOGGING_LEVEL'] = 'DEBUG'
    assert get_logging_level() == 'DEBUG'
    os.environ['LOGGING_LEVEL'] = '1'
    assert get_logging_level() == 1
    os.environ.pop('LOGGING_LEVEL', None)
