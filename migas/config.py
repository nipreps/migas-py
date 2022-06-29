from dataclasses import dataclass
import json
import os
from pathlib import Path
import typing
import uuid


DEFAULT_ENDPOINT = "http://0.0.0.0:8000/graphql"  # localhost test
DEFAULT_CONFIG_FILE = Path.home() / '.cache' / 'migas' / 'config.json'

# TODO: 3.10 - Replace with | operator
File = typing.Union[str, Path]


@dataclass
class Config:
    """
    Class to store client-side configuration, facilitating communication with the server.

    The class stores the following components:
    - `endpoint`:
    The URL of the migas server
    - `user_id`:
    A string representation of a UUID (RFC 4122) assigned to the user.
    - `session_id`:
    A string representation of a UUID assigned to the lifespan of the migas invocation.
    """
    endpoint: str = None
    user_id: str = None
    session_id: str = None
    _is_setup = False

    @classmethod
    def init(
        cls,
        *,
        endpoint: str = None,
        user_id: str = None,
        session_id: str = None,
        final: bool = True,
    ) -> None:
        if cls._is_setup:
            return
        if endpoint is not None:
            cls.endpoint = endpoint
        elif cls.endpoint is None:
            cls.endpoint = DEFAULT_ENDPOINT
        if user_id is not None or cls.user_id is None:
            try:
                uuid.UUID(user_id)
                cls.user_id = user_id
            except Exception:
                cls.user_id = gen_uuid()
        # Do not set automatically, leave to developers
        if session_id is not None:
            try:
                uuid.UUID(session_id)
                cls.session_id = session_id
            except Exception:
                pass
        cls._is_setup = final


    @classmethod
    def load(cls, filename: File) -> bool:
        """Load existing configuration file, or create a new one."""
        config = json.loads(Path(filename).read_text())
        cls.init(final=False, **config)
        return True


    @classmethod
    def save(cls, filename: File) -> str:
        """Save to a JSON file."""
        config = {
            field: getattr(cls, field) for field in cls.__annotations__.keys()
        }
        # TODO: Make safe when multiprocessing
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text(json.dumps(config))
        return str(filename)


    @classmethod
    def _reset(cls):
        """Reset the config class attributes."""
        cls.endpoint = None
        cls.user_id = None
        cls.session_id = None
        cls._is_setup = False


def setup(
    *,
    endpoint: str = None,
    user_id: str = None,
    session_id: str = None,
    save_config: bool = True,
    filename: File = None,
) -> None:
    """
    Configure the client, and save configuration to an output file.

    This method is invoked before each API call, but can also be called by
    application developers for finer-grain control.
    """
    if Config._is_setup:
        return
    filename = filename or DEFAULT_CONFIG_FILE
    if Path(filename).exists():
        Config.load(filename)
    # if any parameters have been set, override the current attribute
    Config.init(endpoint=endpoint, user_id=user_id, session_id=session_id)
    if save_config:
        Config.save(filename)


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
