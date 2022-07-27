def pytest_sessionstart(session):
    """
    If using a Free Hobby Heroku app, it may be asleep, which can cause timeout issues.
    """
    import requests

    from migas.config import DEFAULT_ROOT

    requests.get(DEFAULT_ROOT)
