import pytest

from migas import config


def test_setup_default(tmp_path):
    from uuid import UUID

    conf = config.Config
    assert conf.endpoint is None
    assert conf.user_id is None
    assert conf.session_id is None
    assert conf._is_setup is False

    config.setup()
    assert conf.endpoint == config.DEFAULT_ENDPOINT
    assert UUID(conf.user_id)
    assert conf.session_id is None
    assert conf._is_setup is True
    conf_file = conf._file
    user_id = conf.user_id

    # if setup is called again, overwrite existing
    new_endpoint = 'https://migas-staging.herokuapp.com/graphql'
    new_user = '00000000-0000-0000-0000-000000000000'
    config.setup(endpoint=new_endpoint, user_id=new_user)
    assert conf.endpoint == new_endpoint
    assert conf.user_id == new_user
    # but invalid UUIDs are not used
    config.setup(user_id='abc')
    assert conf.user_id != 'abc'

    # can be reset
    conf._reset()
    assert conf.endpoint is None
    assert conf.session_id is None
    # and loaded
    conf.load(conf_file)
    assert conf.endpoint == config.DEFAULT_ENDPOINT
    assert conf.user_id == user_id

    # user provided output file
    myfile = tmp_path / 'config.json'
    config.setup(filename=myfile)
    assert str(conf._file) == str(myfile)

    # system information is available
    assert conf.language
    assert conf.language_version
    assert conf.platform
    assert conf.container
    assert isinstance(conf.is_ci, bool)


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


def test_multiproc_config(tmp_path):
    import os
    import subprocess as sp

    this_pid = os.getpid()
    conf = config.Config
    config.setup(endpoint='abcdef')  # populate with custom endpoint

    code = """
import os
print(os.getppid())
"""
    proc = sp.run(['python'], input=code, capture_output=True, encoding='UTF-8')
    child_parent_pid = proc.stdout.strip()
    assert str(this_pid) == child_parent_pid

    code = """
import migas
migas.setup()
migas.print_config()
"""
    proc = sp.run(['python'], input=code, capture_output=True, encoding='UTF-8')
    child_config = proc.stdout.strip()
    print(child_config)
    assert 'abcdef' in child_config


def test_print_config(capsys):
    config.setup()
    config.print_config()
    captured = capsys.readouterr()
    for field in config.Config.__dataclass_fields__.keys():
        assert field in captured.out
        assert str(getattr(config.Config, field)) in captured.out


def test_logger(monkeypatch):
    logger = config.logger
    assert logger.name == 'migas-py'
    assert logger.level == 30
    monkeypatch.setenv("MIGAS_LOG_LEVEL", "INFO")
    config._init_logger()
    assert logger.level == 20
