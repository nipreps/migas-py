import uuid

import pytest

from .. import config


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    home = tmp_path / 'config.json'
    monkeypatch.setattr(config, 'DEFAULT_CONFIG_FILE', home)


def test_setup_default():

    conf = config.Config
    assert conf.endpoint is None
    assert conf.user_id is None
    assert conf.session_id is None
    assert conf._is_setup is False

    config.setup()
    assert conf.endpoint == config.DEFAULT_ENDPOINT
    assert uuid.UUID(conf.user_id)
    assert conf.session_id is None
    assert conf._is_setup is True

    # after being set up, cannot be overriden
    new_endpoint = 'https://github.com'
    config.setup(endpoint=new_endpoint)
    assert conf.endpoint == config.DEFAULT_ENDPOINT

    # but fine if cleared
    conf._reset()
    assert conf.endpoint is None
    config.setup(endpoint=new_endpoint)
    assert conf.endpoint == new_endpoint
