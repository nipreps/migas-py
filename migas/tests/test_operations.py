from datetime import datetime as dt
from datetime import timedelta
from datetime import timezone as tz
import time

import pytest

from migas import __version__
from migas.operations import add_project, get_usage

from .utils import do_server_tests

# skip all tests in module if server is not available
pytestmark = pytest.mark.skipif(not do_server_tests, reason="Local server not found")

test_project = 'nipreps/migas-py'
today = dt.now(tz.utc)
future = (today + timedelta(days=2)).strftime('%Y-%m-%d')
today = today.strftime('%Y-%m-%d')


def test_operations(setup_migas):
    _test_add_project()
    # add delay to ensure server has updated
    time.sleep(2)
    _test_get_usage()

def _test_add_project(setup_migas):
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

def _test_get_usage(setup_migas):
    """This test requires `_test_add_project()` to be run before."""
    res = get_usage(test_project, start=today)
    assert res['success'] is True
    all_usage = res['hits']
    assert all_usage > 0

    res = get_usage(test_project, start=today, unique=True)
    assert res['success'] is True
    assert all_usage >= res['hits'] > 0

    res = get_usage(test_project, start=future)
    assert res['success'] is True
    assert res['hits'] == 0

    # checking a project that is not tracked will lead to a failure
    res = get_usage('my/madeup-project', start=today)
    assert res['success'] is False
    assert res['hits'] == 0
