from datetime import datetime as dt
from datetime import timedelta
from datetime import timezone as tz
import time

from looseversion import LooseVersion
import pytest

from migas import __version__
from migas.operations import (
    add_breadcrumb,
    check_project,
    get_usage,
)

from .utils import do_server_tests

# skip all tests in module if server is not available
pytestmark = pytest.mark.skipif(not do_server_tests, reason="Local server not found")

test_project = 'nipreps/migas-py'
today = dt.now(tz.utc)
future = (today + timedelta(days=2)).strftime('%Y-%m-%d')
today = today.strftime('%Y-%m-%d')


def test_migas_add_get(setup_migas):
    res = add_breadcrumb(test_project, __version__)
    # ensure kwargs can be submitted
    res = add_breadcrumb(test_project, __version__, wait=True, language='cpython', platform='win32')
    assert res['success'] is True
    # this breadcrumb is not valid
    res = add_breadcrumb(test_project, __version__, wait=True, status='wtf')
    assert res['success'] is False

    res = get_usage(test_project, start=today)
    assert res['success'] is True
    all_usage = res['hits']
    assert all_usage == 2

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


def test_check_project(setup_migas):
    res = check_project(test_project, __version__)
    assert res['success'] is True
    assert res['latest']
    v = LooseVersion(__version__)
    latest = LooseVersion(res['latest'])
    assert v >= latest
    assert res['flagged'] is False
    assert res['message'] == ''
