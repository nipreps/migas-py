import pytest
from collections import namedtuple
from unittest.mock import MagicMock
import migas
from migas.tracker import _active_trackers

TEST_ROOT = 'http://localhost:8080/'
Mocks = namedtuple('Mocks', ['add_breadcrumb', 'request'])


@pytest.fixture(scope='session')
def endpoint() -> str:
    """Assume tests are run with a local server - revisit if this changes"""
    return TEST_ROOT


@pytest.fixture(scope='module')
def setup_migas(endpoint):
    """Ensure migas is configured to communicate with the staging app."""
    migas.setup(endpoint=endpoint)
    assert migas.config.Config._is_setup
    return migas.config.Config._is_setup


@pytest.fixture
def mock_requests(monkeypatch):
    mock_add = MagicMock()
    mock_req = MagicMock()
    monkeypatch.setattr('migas.api.add_breadcrumb', mock_add)
    monkeypatch.setattr('migas.request._request', mock_req)
    _active_trackers.clear()
    yield Mocks(mock_add, mock_req)
    _active_trackers.clear()
