"""Stripped down, minimal import way to communicate with server"""

import json
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
import typing
from urllib.parse import urlparse

from . import __version__


ETResponse = typing.Tuple[int, typing.Union[dict, str]]  # status code, body


def request(url: str, query: str, *, timeout: int = 3, chunk_size: int = None) -> ETResponse:
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
        conn.request("POST", purl.path, body, headers)
        response = conn.getresponse()
        body = _read_response(response, chunk_size)
    except TimeoutError:
        return (
            408, {"success": False, "errors": [{"message": "Connection to server timed out."}]}
        )
    except ConnectionError:
        return (
            503, {"success": False, "errors": [{"message": "Server is not available."}]}
        )
    finally:
        conn.close()

    if not response.headers.get("X-Backend-Server"):
        # TODO: Implement logging
        print("migas server is incorrectly configured.")

    if response.headers.get("Content-Type").startswith("application/json"):
        body = json.loads(body)

    return response.status, body


def _read_response(response: HTTPResponse, chunk_size: int = None) -> str:
    """Read and aggregate the response body"""
    stream = b''
    # TODO: 3.8 - Replace with walrus
    # while chunk := response.read(chunk_size):
    chunk = 1
    while chunk:
        chunk = response.read(chunk_size)
        stream += chunk
    return stream.decode()
