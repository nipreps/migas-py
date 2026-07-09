from unittest.mock import MagicMock

import pytest

from migas.request import _request

GET_URL = 'https://httpbin.org/get'
GET_COMPRESSED_URL = 'https://httpbingo.org/get'
POST_URL = 'https://httpbin.org/post'

pytestmark = pytest.mark.filterwarnings('ignore')


@pytest.mark.parametrize(
    'method,url,query',
    [('POST', POST_URL, 'mydata'), ('GET', GET_URL, None), ('GET', GET_COMPRESSED_URL, None)],
)
def test_request_get(method, url, query):
    status, res = _request(url, query=query, method=method)
    assert status == 200
    assert res


def test_timeout(monkeypatch):
    status, res = _request(GET_URL, timeout=0.00001, method='GET')
    assert status == 408
    assert res['errors']

    monkeypatch.setenv('MIGAS_TIMEOUT', '0.000001')
    status, res = _request(GET_URL, method='GET')
    assert status == 408
    assert res['errors']

    monkeypatch.delenv('MIGAS_TIMEOUT')
    status, res = _request(GET_URL, method='GET')
    assert status == 200
    assert res


@pytest.fixture
def captured_path(monkeypatch):
    response = MagicMock(status=200, headers={'X-Backend-Server': 'test'})
    response.read.return_value = b''

    conn = MagicMock()
    conn.getresponse.return_value = response

    mock_conn = MagicMock(return_value=conn)
    monkeypatch.setattr('migas.request.HTTPConnection', mock_conn)
    monkeypatch.setattr('migas.request.HTTPSConnection', mock_conn)

    return conn.request


@pytest.mark.parametrize(
    'base_url,expected_path',
    [
        ('http://localhost:8081', '/api/breadcrumb'),
        ('http://localhost:8081/', '/api/breadcrumb'),
        ('https://migas.nipreps.org', '/api/breadcrumb'),
        ('https://migas.nipreps.org/', '/api/breadcrumb'),
        ('https://customendpoint.co/migas/', '/migas/api/breadcrumb'),
    ],
)
def test_request_path_always_absolute(captured_path, base_url, expected_path):
    _request(base_url, path='/api/breadcrumb', json_data={'foo': 'bar'})
    request_path = captured_path.call_args.args[1]
    assert request_path == expected_path
