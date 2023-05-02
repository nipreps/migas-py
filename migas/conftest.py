import pytest

TEST_ROOT = "http://localhost:8080/"
TEST_ENDPOINT = f"{TEST_ROOT}graphql"


@pytest.fixture(scope="session")
def endpoint() -> str:
    return TEST_ENDPOINT
