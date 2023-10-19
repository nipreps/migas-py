import pytest

import migas

TEST_ROOT = "http://localhost:8080/"
TEST_ENDPOINT = f"{TEST_ROOT}graphql"


@pytest.fixture(scope='session')
def endpoint() -> str:
    return TEST_ENDPOINT


@pytest.fixture(scope='session', autouse=True)
def setup_migas(endpoint):
    """Ensure migas is configured to communicate with the staging app."""
    migas.setup(endpoint=endpoint)

    assert migas.config.Config._is_setup
