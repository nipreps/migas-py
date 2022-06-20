"""Stripped down, minimal import way to communicate with server"""

import json
from http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from urllib.parse import urlparse

from . import __version__


ETResponse = tuple[int, str, str]  # status code, content-type, body


def request(url: str, query: str, *, timeout: int = 5, chunk_size: int = None) -> ETResponse:
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
        'User-Agent': f'etelemetry-client/{__version__}',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': '*/*',
        'Content-Length': len(body),
        'Content-Type': 'application/json',
    }

    try:
        conn.request("POST", purl.path, body, headers)
        response = conn.getresponse()
        body = _read_response(response, chunk_size)
    finally:
        conn.close()

    # TODO: Check reponse headers for server integrity, content type
    return response.status, response.headers.get('Content-Type'), body


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
