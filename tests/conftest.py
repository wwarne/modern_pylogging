import os
from collections.abc import Generator

import pytest

from tests.helpers import cleanup_logging_impl

TEMP_ENV_VARS = {
    'ENV': 'env-dev-test',
    'APP_NAME': 'system-test',
    'POD_NAME': 'pod-test',
}


@pytest.fixture(scope='session', autouse=True)
def _setup_temp_env_variables() -> Generator[None, None, None]:
    old_env = dict(os.environ)
    os.environ.update(TEMP_ENV_VARS)
    yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture(autouse=True)
def _cleanup_logging() -> Generator[None, None, None]:
    with cleanup_logging_impl():
        yield
