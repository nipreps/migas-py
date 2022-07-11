"""Stripped down, minimal import way to communicate with server"""

import json
import typing
from http.client import HTTPConnection, HTTPResponse, HTTPSConnection
from urllib.parse import urlparse

from . import __version__

ETResponse = typing.Tuple[int, typing.Union[dict, str]]  # status code, body

TIMEOUT_RESPONSE = (
    408,
    {"data": None, "errors": [{"message": "Connection to server timed out."}]},
)
UNAVAIL_RESPONSE = (503, {"data": None, "errors": [{"message": "Could not connect to server."}]})


def request(
    url: str, query: str, *, timeout: float = 3, method: str = "POST", chunk_size: int = None
) -> ETResponse:
    purl = urlparse(url)
    # TODO: 3.10 - Replace with match/case
    if purl.scheme == 'https':
        Connection = HTTPSConnection
    elif purl.scheme == 'http':
        Connection = HTTPConnection
    else:
        raise ValueError("URL scheme not supported")

    body = json.dumps({"query": query}).encode("utf-8")
    conn = Connection(purl.netloc, timeout=timeout)
    headers = {
        'User-Agent': f'migas-client/{__version__}',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': '*/*',
        'Content-Length': len(body),
        'Content-Type': 'application/json',
    }

    try:
        conn.request(method, purl.path, body, headers)
        response = conn.getresponse()
        body = _read_response(response, chunk_size)
    except TimeoutError:
        return TIMEOUT_RESPONSE
    except ConnectionError:
        return UNAVAIL_RESPONSE
    except OSError as e:
        # Python < 3.10, this could be socket.timeout or socket.gaierror
        import socket

        if isinstance(e, socket.timeout):
            return TIMEOUT_RESPONSE
        else:
            return UNAVAIL_RESPONSE
    finally:
        conn.close()

    if not response.headers.get("X-Backend-Server"):
        # TODO: Implement logging
        print("migas server is incorrectly configured.")

    if response.headers.get("Content-Type").startswith("application/json"):
        body = json.loads(body)

    return response.status, body


def _read_response(response: HTTPResponse, chunk_size: int = None) -> str:
    """
    Read and aggregate the response body.

    If `chunk_size` is `None`, the entire response is read at once.
    """
    stream = b''
    # TODO: 3.8 - Replace with walrus
    # while chunk := response.read(chunk_size):
    chunk = 1
    while chunk:
        chunk = response.read(chunk_size)
        stream += chunk
    return stream.decode()
