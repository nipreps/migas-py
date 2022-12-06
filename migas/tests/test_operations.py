import pytest

from migas import __version__, setup
from migas.operations import add_project, get_usage

test_project = 'nipreps/migas-py'


def _local_server_up() -> bool:
    """Checks if the server is locally available."""
    import requests

    try:
        res = requests.get('http://localhost:8000/', timeout=0.5)
        assert res.headers.get('x-backend-server') == 'migas'
    except Exception:
        return False
    return True

pytestmark = pytest.mark.skipif(not _local_server_up(), reason="Local server not found")


def future() -> str:
    from datetime import datetime, timedelta

    return (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d')


@pytest.fixture(scope='module', autouse=True)
def setup_migas(endpoint):
    """Ensure migas is configured to communicate with the staging app."""
    setup(endpoint=endpoint)


def test_add_project():
    res = add_project(test_project, __version__)
    assert res['success'] is True
    latest = res['latest_version']
    assert latest

    # ensure kwargs can be submitted
    res = add_project(test_project, __version__, language='cpython', platform='win32')
    assert res['success'] is True
    assert res['latest_version'] == latest
    # should be cached since we just checked the version
    assert res['cached'] is True

    # illegal queries should fail
    res = add_project(test_project, __version__, status='wtf')
    assert res['success'] is False
    assert res['latest_version'] is None


def test_get_usage():
    res = get_usage(test_project)
    assert res['success'] is True
    all_usage = res['hits']
    assert res['hits'] > 0

    res = get_usage(test_project, unique=True)
    assert res['success'] is True
    assert all_usage >= res['hits'] > 0

    res = get_usage(test_project, start=future())
    assert res['success'] is False
    assert res['hits'] == 0
