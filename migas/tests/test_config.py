import json
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

    # after being set up, will not be changed unless forcing
    new_endpoint = 'https://github.com'
    config.setup(endpoint=new_endpoint)
    assert conf.endpoint == config.DEFAULT_ENDPOINT
    config.setup(force=True, endpoint=new_endpoint)
    assert conf.endpoint == new_endpoint

    # ensure loading is working
    nuid = '00000000-0000-0000-0000-000000000000'
    config_dict = json.loads(config.DEFAULT_CONFIG_FILE.read_text())
    config_dict['session_id'] = nuid
    config.DEFAULT_CONFIG_FILE.write_text(json.dumps(config_dict))
    assert conf.session_id is None
    # again, forcing is required to overwrite
    conf.load(config.DEFAULT_CONFIG_FILE, force=True)
    assert conf.session_id == nuid

    # can be reset altogether
    conf._reset()
    assert conf.endpoint is None
    assert conf.session_id is None


def test_safe_uuid_factory(monkeypatch):
    import getpass

    uid0 = config._safe_uuid_factory()
    assert uid0

    def none():
        users = {}
        return users['none']

    # simulate unknown user
    monkeypatch.setattr(getpass, 'getuser', none)
    with pytest.raises(KeyError):
        getpass.getuser()

    uid1 = config._safe_uuid_factory()
    assert uid1

    assert uid0 != uid1
