"""Stripped down, minimal import way to communicate with server"""

from __future__ import annotations

import json
import os
import ssl
import warnings
from http.client import HTTPConnection, HTTPResponse, HTTPSConnection
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

from . import __version__

MigasResponse = tuple[int, dict | str]  # status code, body

DEFAULT_TIMEOUT = 3
TIMEOUT_RESPONSE = (
    408,
    {'data': None, 'errors': [{'message': 'Connection to server timed out.'}]},
)
UNAVAIL_RESPONSE = (503, {'data': None, 'errors': [{'message': 'Could not connect to server.'}]})


def request(
    url: str,
    *,
    query: str | None = None,
    path: str | None = None,
    json_data: dict | None = None,
    timeout: float | None = None,
    method: str = 'POST',
    chunk_size: int | None = None,
    wait: bool = False,
) -> MigasResponse | None:
    """
    Send a non-blocking call to the server.

    This will never check the future, and no assumptions can be made about server receptivity.
    """
    with ThreadPoolExecutor() as executor:
        future = executor.submit(
            _request,
            url,
            query=query,
            path=path,
            json_data=json_data,
            timeout=timeout,
            method=method,
            chunk_size=chunk_size,
            wait=wait,
        )

        if wait is True:
            return future.result()


def _request(
    url: str,
    *,
    query: str | None = None,
    path: str | None = None,
    json_data: dict | None = None,
    timeout: float | None = None,
    method: str = 'POST',
    chunk_size: int | None = None,
    wait: bool = False,
) -> MigasResponse:

    purl = urlparse(url)
    timeout = timeout or float(os.getenv('MIGAS_TIMEOUT', DEFAULT_TIMEOUT))
    match purl.scheme:
        case 'https':
            conn = HTTPSConnection(
                purl.netloc, timeout=timeout, context=ssl.create_default_context()
            )
        case 'http':
            conn = HTTPConnection(purl.netloc, timeout=timeout)
        case _:
            raise ValueError('URL scheme not supported')

    headers = {
        'User-Agent': f'migas-client/{__version__}',
        'Accept-Encoding': 'gzip, deflate',
        'Accept': '*/*',
        'Content-Type': 'application/json; charset=utf-8',
    }
    body = None
    if query:
        body = json.dumps({'query': query}).encode('utf-8')
    elif json_data:
        body = json.dumps(json_data).encode('utf-8')

    if body:
        headers['Content-Length'] = len(body)

    request_path = purl.path
    if path:
        request_path = os.path.join(request_path, path.lstrip('/'))

    if wait and not query:
        sep = '&' if '?' in request_path else '?'
        request_path += f'{sep}wait=true'

    try:
        conn.request(method, request_path, body=body, headers=headers)
        response = conn.getresponse()
        encoding = response.headers.get('content-encoding')
        body = _read_response(response, encoding, chunk_size)
    except TimeoutError:
        return TIMEOUT_RESPONSE
    except (ConnectionError, OSError):
        return UNAVAIL_RESPONSE
    finally:
        conn.close()

    if body and response.headers.get('content-type', '').startswith('application/json'):
        body = json.loads(body)

    if not response.headers.get('X-Backend-Server'):
        warnings.warn('migas server is incorrectly configured.', UserWarning, stacklevel=1)
    return response.status, body


def _read_response(
    response: HTTPResponse, encoding: str | None = None, chunk_size: int | None = None
) -> str:
    """
    Read and aggregate the response body.

    If `chunk_size` is `None`, the entire response is read at once.
    """
    stream = b''
    while chunk := response.read(chunk_size):
        stream += chunk

    if encoding:
        stream = _decompress_stream(stream, encoding)
    return stream.decode()


def _decompress_stream(stream: bytes, encoding: str) -> bytes:
    """Decompress the compressed response byte stream."""
    match encoding:
        case 'gzip':
            import gzip

            return gzip.decompress(stream)
        case 'deflate':
            import zlib

            return zlib.decompress(stream)
        case _:
            raise NotImplementedError(f'Cannot decode response with encoding "{encoding}"')
