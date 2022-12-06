def _check_server_available() -> bool:
    """Checks if the server is locally available."""
    import requests

    try:
        res = requests.get('http://localhost:8000/', timeout=0.5)
        assert res.headers.get('x-backend-server') == 'migas'
    except Exception:
        return False
    return True


do_server_tests = _check_server_available()
