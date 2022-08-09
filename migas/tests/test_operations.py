import pytest

from migas import __version__, setup
from migas.operations import add_project, get_usage

test_project = 'mgxd/migas-py'


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
    y2k = '2000-01-01'
    res = get_usage(test_project, start=y2k)
    assert res['success'] is True
    all_usage = res['hits']
    assert res['hits'] > 0

    res = get_usage(test_project, start=y2k, unique=True)
    assert res['success'] is True
    assert all_usage >= res['hits'] > 0

    res = get_usage(test_project, start=future())
    assert res['success'] is False
    assert res['hits'] == 0
