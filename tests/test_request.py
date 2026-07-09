import gzip
from unittest.mock import MagicMock

import pytest

from migas.request import _request

pytestmark = pytest.mark.filterwarnings('ignore')


def _response(body=b'{"ok": true}', **headers):
    headers = {'X-Backend-Server': 'test', 'content-type': 'application/json', **headers}
    response = MagicMock(status=200, headers=headers)
    response.read.side_effect = [body, b'']
    return response


def _mock_connection(monkeypatch, response_factory, *, raise_timeout_below=None):

    def connection_factory(*args, timeout=None, **kwargs):
        conn = MagicMock()
        if (
            raise_timeout_below is not None
            and timeout is not None
            and timeout < raise_timeout_below
        ):
            conn.request.side_effect = TimeoutError
        else:
            conn.getresponse.return_value = response_factory()
        return conn

    monkeypatch.setattr('migas.request.HTTPConnection', connection_factory)
    monkeypatch.setattr('migas.request.HTTPSConnection', connection_factory)


@pytest.fixture
def mock_get(monkeypatch):
    _mock_connection(monkeypatch, _response)


@pytest.fixture
def mock_post(monkeypatch):
    _mock_connection(monkeypatch, _response)


@pytest.fixture
def mock_get_compressed(monkeypatch):
    _mock_connection(
        monkeypatch,
        lambda: _response(
            gzip.compress(b'ok'), **{'content-type': 'text/plain', 'content-encoding': 'gzip'}
        ),
    )


@pytest.fixture
def mock_timeout(monkeypatch):
    # Anything under 1s will synthetically timeout
    _mock_connection(monkeypatch, _response, raise_timeout_below=1)


def test_request_get(mock_get):
    status, res = _request('https://example.com/get', method='GET')
    assert status == 200
    assert res


def test_request_post(mock_post):
    status, res = _request('https://example.com/post', query='mydata', method='POST')
    assert status == 200
    assert res


def test_request_get_compressed(mock_get_compressed):
    status, res = _request('https://example.com/get', method='GET')
    assert status == 200
    assert res


def test_timeout(mock_timeout, monkeypatch):
    status, res = _request('https://example.com/get', timeout=0.00001, method='GET')
    assert status == 408
    assert res['errors']

    monkeypatch.setenv('MIGAS_TIMEOUT', '0.00001')
    status, res = _request('https://example.com/get', method='GET')
    assert status == 408
    assert res['errors']

    monkeypatch.delenv('MIGAS_TIMEOUT')
    status, res = _request('https://example.com/get', method='GET')
    assert status == 200
    assert res


@pytest.fixture
def captured_path(monkeypatch):
    conn = MagicMock()
    conn.getresponse.return_value = _response(body=b'')

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
