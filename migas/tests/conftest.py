import pytest

import migas

TEST_ROOT = "http://localhost:8080/"
TEST_ENDPOINT = f"{TEST_ROOT}graphql"



@pytest.fixture(scope='module')
def setup_migas():
    """Ensure migas is configured to communicate with the staging app."""
    migas.setup(endpoint=TEST_ENDPOINT)

    assert migas.config.Config._is_setup
