import pytest

from migas.request import request

GET_URL = 'https://httpbin.org/get'
POST_URL = 'https://httpbin.org/post'


@pytest.mark.parametrize(
    'method,url,query', [('POST', POST_URL, 'mydata'), ('GET', GET_URL, None)]
)
def test_request_get(method, url, query):
    status, res = request(url, query=query, method=method)
    assert status == 200
    assert res


def test_timeout(monkeypatch):
    status, res = request(GET_URL, timeout=0.00001, method="GET")
    assert status == 408
    assert res['errors']

    monkeypatch.setenv('MIGAS_TIMEOUT', '0.000001')
    status, res = request(GET_URL, method="GET")
    assert status == 408
    assert res['errors']

    monkeypatch.delenv('MIGAS_TIMEOUT')
    status, res = request(GET_URL, method="GET")
    assert status == 200
    assert res
