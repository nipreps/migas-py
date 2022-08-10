import json
import logging
import os
import typing
import uuid
from dataclasses import dataclass, fields
from functools import wraps
from pathlib import Path
from tempfile import gettempdir

from .utils import compile_info

DEFAULT_ENDPOINT = 'https://migas.herokuapp.com/graphql'
DEFAULT_CONFIG_FILE_FMT = str(Path(gettempdir()) / 'migas-{pid}.json').format

# TODO: 3.10 - Replace with | operator
File = typing.Union[str, Path]


def _init_logger(level: typing.Optional[str] = None) -> logging.Logger:
    if level is None:
        level = os.getenv("MIGAS_LOG_LEVEL", logging.WARNING)
    logger = logging.getLogger("migas-py")
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('<%(name)s> [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def suppress_errors(func: typing.Callable) -> typing.Callable:
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
        if os.getenv("MIGAS_OPTOUT"):
            # do not communicate with server
            return {
                "success": False,
                "errors": [{"message": "migas telemetry is disabled."}],
            }
        if not Config._is_setup:
            return {
                "success": False,
                "errors": [{"message": "migas setup incomplete - did you call `migas.setup()`?"}],
            }
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

    This class will not be initialized, instead usage depends on class attributes.
    """

    _file: File = None
    _pid: int = None
    _is_setup: bool = False
    _telemetry_attrs = (
        'user_id',
        'session_id',
        'language',
        'language_version',
        'platform',
        'container',
        'is_ci',
    )
    endpoint: str = None
    user_id: str = None
    session_id: str = None
    language: str = None
    language_version: str = None
    platform: str = None
    container: str = None
    is_ci: bool = None

    @classmethod
    def init(
        cls,
        *,
        endpoint: str = None,
        user_id: str = None,
        session_id: str = None,
        **kwargs,
    ) -> None:
        """
        Setup migas configuration.

        If class was already configured, existing configuration is used.
        """
        if cls._pid is None:
            cls._pid = os.getpid()
        cls.endpoint = endpoint or DEFAULT_ENDPOINT
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

        for param, val in kwargs.items():
            if hasattr(cls, param):
                setattr(cls, param, val)

    @classmethod
    @suppress_errors
    def load(cls, filename: File) -> bool:
        """Load existing configuration file, or create a new one."""
        config = json.loads(Path(filename).read_text())
        cls.init(**config)
        return True

    @classmethod
    @suppress_errors
    def save(cls, filename: File) -> None:
        """Save to a JSON file."""
        config = {
            field: getattr(cls, field)
            for field in cls.__annotations__.keys()
            if field not in ('_is_setup', '_file')
        }
        # TODO: Make safe when multiprocessing
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        Path(filename).write_text(json.dumps(config))
        cls._file = filename

    @classmethod
    def populate(cls) -> dict:
        return {f: getattr(cls, f) for f in cls._telemetry_attrs if getattr(cls, f) is not None}

    @classmethod
    def _reset(cls) -> None:
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
    filename: File = None,
    save_config: bool = True,
) -> None:
    """
    Prepare the client to communicate with a migas server.

    This method is required prior to calling the API.

    If `user_id` is not provided, one will be generated.
    """
    if filename is not None:
        _try_load(filename)
    else:
        # check for existing configuration files
        # first current PID, and if not then parent PID
        # if exists and loads, setup is complete
        (
            _try_load(DEFAULT_CONFIG_FILE_FMT(pid=os.getpid()))
            or _try_load(DEFAULT_CONFIG_FILE_FMT(pid=os.getppid()))
        )

    # if the PID loaded is this process's parent PID, just use the loaded config
    if Config._pid != os.getppid():
        # collect system information and initialize config
        info = compile_info()
        Config.init(
            endpoint=endpoint,
            user_id=user_id,
            session_id=session_id,
            language=info['language'],
            language_version=info['language_version'],
            platform=info['platform'],
            container=info['container'],
            is_ci=info['is_ci'],
        )
    if save_config:
        Config.save(filename or DEFAULT_CONFIG_FILE_FMT(pid=os.getpid()))

    Config._is_setup = True


def print_config() -> None:
    for field in fields(Config):
        print(f'{field.name}: {getattr(Config, field.name)}')


def _try_load(filename) -> bool:
    if Path(filename).exists():
        # load and use
        return Config.load(filename)
    return False


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

    try:
        user = getpass.getuser()
    except KeyError:
        # fails in cases of running docker containers as non-root
        user = f'user-{os.getuid()}'

    name = f"{user}@{os.getenv('HOSTNAME', socket.gethostname())}"
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, name))


logger = _init_logger()
