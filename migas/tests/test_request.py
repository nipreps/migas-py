import pytest

from migas.config import DEFAULT_ENDPOINT
from migas.request import request

ROOT = 'https://migas.herokuapp.com/'
POST_QUERY = 'query{get_usage{project:"git/hub",start:"2022-07-01"}}'


@pytest.mark.parametrize(
    'endpoint,body,method', [(DEFAULT_ENDPOINT, POST_QUERY, "POST"), (ROOT, '', "GET")]
)
def test_request(endpoint, body, method):
    status, res = request(endpoint, body, method=method)
    assert status == 200
    assert res


def test_timeout():
    status, res = request(ROOT, '', timeout=0.00001, method="GET")
    assert status == 408
    assert res['errors']
