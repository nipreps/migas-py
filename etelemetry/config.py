from dataclasses import dataclass
import json
import os
from pathlib import Path
import typing
import uuid


DEFAULT_ENDPOINT = "http://0.0.0.0:8000/graphql"  # localhost test
CONFIG_FILENAME = Path.home() / '.cache' / 'etelemetry' / 'config.json'

# TODO: 3.10 - Replace with | operator
File = typing.Union[str, Path]


@dataclass
class Config:
    """
    Class to store client-side configuration, facilitating communication with the server.

    The class stores the following components:
    - `endpoint`:
    The URL of the etelemetry server
    - `user_id`:
    A string representation of a UUID (RFC 4122) assigned to the user.
    - `session_id`:
    A string representation of a UUID assigned to the lifespan of the etelemetry invocation.
    """
    endpoint: str = None
    user_id: str = None
    session_id: str = None
    _is_setup = False

    @classmethod
    def _setup(cls, *, endpoint: str = None, user_id: str = None, session_id: str = None) -> None:
        if cls._is_setup:
            return
        if endpoint is not None or cls.endpoint is None:
            cls.endpoint = endpoint or DEFAULT_ENDPOINT
        if user_id is not None or cls.user_id is None:
            try:
                uuid.UUID(user_id)
                cls.user_id = user_id
            except Exception:
                cls.user_id = gen_uuid()
        if session_id is not None or cls.session_id is None:
            try:
                uuid.UUID(session_id)
                cls.session_id = session_id
            except Exception:
                cls.session_id = gen_uuid()
        cls._is_setup = True


def load(filename: File = CONFIG_FILENAME) -> bool:
    """Load existing configuration file, or create a new one."""
    config = json.loads(Path(filename).read_text())
    Config._setup(**config)
    return True


def save(filename: File = CONFIG_FILENAME) -> str:
    """Save to a file."""
    config = {
        field: getattr(Config, field) for field in Config.__annotations__.keys()
    }
    # TODO: Make safe when multiprocessing
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    Path(filename).write_text(json.dumps(config))
    return str(filename)


def setup(
    *,
    endpoint: str = None,
    user_id: str = None,
    session_id: str = None,
    save_config: bool = True,
    filename: File = CONFIG_FILENAME,
) -> None:
    """
    Configure the client, and save configuration to an output file.

    This method is invoked before each API call, but can also be called by
    application developers for finer-grain control.
    """
    if Config._is_setup:
        return
    if Path(filename).exists():
        load(filename)
    # if any parameters have been set, override the current attribute
    Config._setup(endpoint, user_id, session_id)
    if save_config:
        save(filename)


def gen_uuid(uuid_factory: str = "safe") -> str:
    """
    Generate a RFC 4122 UUID.

    Depending on what `uuid_factory` is provided, the UUID will be generated differently:
    - `safe`: This is multiprocessing safe, and uses system information.
    - `random`: This is random, and may run into problems if setup is called across multiple
    processes.

    Hard cases to think about:
    - HPCs where HOSTNAME envvar is not set
    - Docker images where previous config is unavailable
    """
    # TODO: 3.10 - Replace with match/case
    if uuid_factory == "safe":
        return _safe_uuid_factory()
    elif uuid_factory == "random":
        return str(uuid.uuid4())
    raise NotImplementedError


def _safe_uuid_factory() -> str:
    import getpass
    import socket

    name = f"{getpass.getuser()}@{os.getenv('HOSTNAME', socket.gethostname())}"
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, name))
