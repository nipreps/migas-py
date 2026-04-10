import getpass
import socket
import subprocess as sp
import uuid

import pytest

from migas import config


def test_setup_default(tmp_path):
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
    conf_file = conf._file
    user_id = conf.user_id

    # if setup is called again, overwrite existing
    new_endpoint = 'https://migas-staging.herokuapp.com'
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


def test_multiproc_config():
    config.setup(endpoint='abcdef')  # populate with custom endpoint

    code = """
import migas
migas.setup()
migas.print_config()
"""
    proc = sp.run(['python'], input=code, capture_output=True, encoding='UTF-8')
    child_config = proc.stdout.strip()
    print(child_config)
    assert 'abcdef' in child_config


def test_endpoint_stripping():
    conf = config.Config
    conf._reset()
    config.setup(endpoint='http://localhost:8080/graphql')
    assert conf.endpoint == 'http://localhost:8080'

    config.setup(endpoint='http://localhost:8080/')
    assert conf.endpoint == 'http://localhost:8080/'

    config.setup(endpoint='http://localhost:8080')
    assert conf.endpoint == 'http://localhost:8080'


@pytest.mark.parametrize(
    'fqdn,expected',
    [
        ('node042.cluster.edu', 'cluster.edu'),
        ('node.uni.ac.uk', 'uni.ac.uk'),
        ('node.corp.com', 'corp.com'),
        ('macbook.local', None),
        ('hostname.local', None),
        ('workstation', None),
        ('node.corp', None),
        ('localhost', None),
    ],
)
def test_extract_domain(fqdn, expected):
    assert config._extract_domain(fqdn) == expected


def test_safe_uuid_nodes(monkeypatch, tmp_path):
    """Same user on different nodes of same domain produces the same UUID."""
    monkeypatch.setattr(config, '_get_user_id_file', lambda: tmp_path / 'nodir' / 'user_id')
    monkeypatch.setattr(getpass, 'getuser', lambda: 'testuser')

    monkeypatch.setattr(socket, 'getfqdn', lambda: 'node001.cluster.edu')
    uid1 = config._safe_uuid_factory()

    monkeypatch.setattr(socket, 'getfqdn', lambda: 'node042.cluster.edu')
    uid2 = config._safe_uuid_factory()

    assert uid1 == uid2


def test_safe_uuid_fqdn_fallback(monkeypatch, tmp_path):
    """Test FQDN fallback when .local present."""
    monkeypatch.setattr(config, '_get_user_id_file', lambda: tmp_path / 'nodir' / 'user_id')
    monkeypatch.setattr(getpass, 'getuser', lambda: 'testuser')
    monkeypatch.setattr(socket, 'getfqdn', lambda: 'macbook.local')
    monkeypatch.setattr(socket, 'gethostname', lambda: 'macbook')

    uid = config._safe_uuid_factory()
    expected = str(uuid.uuid3(uuid.NAMESPACE_DNS, 'testuser@macbook'))
    assert uid == expected


def test_safe_uuid_loads(monkeypatch, tmp_path):
    """Test loading of user id from file."""
    persistent_id = str(uuid.uuid4())
    user_id_file = tmp_path / 'migas' / 'user_id'
    user_id_file.parent.mkdir()
    user_id_file.write_text(persistent_id)

    monkeypatch.setattr(config, '_get_user_id_file', lambda: user_id_file)
    result = config._safe_uuid_factory()
    assert result == persistent_id


def test_safe_uuid_saves(monkeypatch, tmp_path):
    """Generated UUID is saved to persistent file for future reuse."""
    user_id_file = tmp_path / 'migas' / 'user_id'
    monkeypatch.setattr(config, '_get_user_id_file', lambda: user_id_file)
    monkeypatch.setattr(getpass, 'getuser', lambda: 'testuser')
    monkeypatch.setattr(socket, 'getfqdn', lambda: 'node001.cluster.edu')

    result = config._safe_uuid_factory()

    assert user_id_file.exists()
    assert user_id_file.read_text() == result
