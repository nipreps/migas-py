import pytest

from migas.config import DEFAULT_ENDPOINT
from migas.request import request

ROOT = 'https://migas.herokuapp.com/'
POST_QUERY = 'query{get_usage{project:"git/hub",start:"2022-07-01"}}'


@pytest.mark.parametrize(
    'endpoint,query,method', [(DEFAULT_ENDPOINT, POST_QUERY, "POST"), (ROOT, None, "GET")]
)
def test_request(endpoint, query, method):
    status, res = request(endpoint, query=query, method=method, timeout=5)
    assert status == 200
    assert res


def test_timeout(monkeypatch):
    status, res = request(ROOT, timeout=0.00001, method="GET")
    assert status == 408
    assert res['errors']

    monkeypatch.setenv('MIGAS_TIMEOUT', '0.000001')
    status, res = request(ROOT, method="GET")
    assert status == 408
    assert res['errors']
