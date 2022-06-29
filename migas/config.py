import json
import os
import typing
import uuid
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

DEFAULT_ENDPOINT = 'https://migas.herokuapp.com/graphql'
DEFAULT_CONFIG_FILE = Path.home() / '.cache' / 'migas' / 'config.json'

# TODO: 3.10 - Replace with | operator
File = typing.Union[str, Path]


def suppress_errors(func):
    """Decorator to silently fail the wrapped function"""

    @wraps(func)
    def safe(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            pass

    return safe


def telemetry_enabled(func: typing.Callable) -> typing.Callable:
    """Decorator function to verify telemetry collection is enabled."""

    @wraps(func)
    def can_send(*args, **kwargs):
        if not os.getenv("ENABLE_MIGAS", "0").lower() in ("1", "true", "y", "yes"):
            # do not communicate with server
            return {
                "success": False,
                "errors": [
                    {"message": "migas is not enabled - set ENABLE_MIGAS environment variable."}
                ],
            }
        # otherwise, ensure config is set up
        setup()
        return func(*args, **kwargs)

    return can_send


@dataclass(init=False, repr=False, eq=False)
class Config:
    """
    Class to store client-side configuration, facilitating communication with the server.

    The class stores the following components:
    - `endpoint`:
    URL of the graphql endpoint of the migas server.
    - `user_id`:
    A string representation of a UUID (RFC 4122) assigned to the user.
    - `session_id`:
    A string representation of a UUID assigned to the lifespan of the migas invocation.

    This class is not meant to be initialized, instead usage depends on class attributes.
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
        """
        Setup migas configuration.

        If class was already configured, existing configuration is used.
        """
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
    @suppress_errors
    def load(cls, filename: File) -> bool:
        """Load existing configuration file, or create a new one."""
        config = json.loads(Path(filename).read_text())
        cls.init(final=False, **config)
        return True

    @classmethod
    @suppress_errors
    def save(cls, filename: File) -> str:
        """Save to a JSON file."""
        config = {field: getattr(cls, field) for field in cls.__annotations__.keys()}
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
