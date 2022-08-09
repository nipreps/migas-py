import pytest

TEST_ROOT = "https://migas-staging.herokuapp.com/"
TEST_ENDPOINT = f"{TEST_ROOT}graphql"


def pytest_sessionstart(session) -> None:
    """
    If using a Free Hobby Heroku app, it may be asleep, which can cause timeout issues.
    This sends a ping to allow the server to wakeup.
    """
    import requests

    requests.get(TEST_ROOT)


@pytest.fixture(scope="session")
def endpoint() -> str:
    return TEST_ENDPOINT
