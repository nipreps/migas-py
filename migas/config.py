import getpass
import contextlib
import json
import logging
import os
import socket
import typing
import uuid
from dataclasses import dataclass, fields
from functools import wraps
from pathlib import Path
from tempfile import gettempdir

from .utils import compile_info

DEFAULT_ENDPOINT = 'https://migas.nipreps.org'
DEFAULT_CONFIG_FILE_FMT = str(Path(gettempdir()) / 'migas-{pid}.json').format

# TODO: 3.10 - Replace with | operator
File = typing.Union[str, Path]


def _init_logger(level: typing.Optional[str] = None) -> logging.Logger:
    if level is None:
        level = os.getenv('MIGAS_LOG_LEVEL', logging.WARNING)
    logger = logging.getLogger('migas-py')
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


def _chmod600(filename: File) -> None:
    """Enforce restricted permissions (0o600) on a file."""
    with contextlib.suppress(OSError):
        if (os.stat(filename).st_mode & 0o777) != 0o600:
            os.chmod(filename, 0o600)


def _secure_write(filename: File, content: str) -> None:
    """Write content to a file with restricted permissions (0o600)."""
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    flags |= getattr(os, 'O_NOFOLLOW', 0)

    fd = os.open(filename, flags, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    os.chmod(filename, 0o600)


def telemetry_enabled(func: typing.Callable) -> typing.Callable:
    """Decorator function to verify telemetry collection is enabled."""

    @wraps(func)
    def can_send(*args, **kwargs):
        if os.getenv('MIGAS_OPTOUT'):
            # do not communicate with server
            return {'success': False, 'errors': [{'message': 'migas telemetry is disabled.'}]}
        if not Config._is_setup:
            return {
                'success': False,
                'errors': [{'message': 'migas setup incomplete - did you call `migas.setup()`?'}],
            }
        return func(*args, **kwargs)

    return can_send


@dataclass(init=False, repr=False, eq=False)
class Config:
    """
    Class to store client-side configuration, facilitating communication with the server.

    The class stores the following components:
    - `endpoint`:
    Base URL of the migas server.
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
        'user_type',
    )
    endpoint: str = None
    user_id: str = None
    session_id: str = None
    language: str = None
    language_version: str = None
    platform: str = None
    container: str = None
    is_ci: bool = None
    user_type: str = None

    @classmethod
    def init(
        cls, *, endpoint: str = None, user_id: str = None, session_id: str = None, **kwargs
    ) -> None:
        """
        Setup migas configuration.

        If class was already configured, existing configuration is used.
        """
        if cls._pid is None:
            cls._pid = os.getpid()
        endpoint = endpoint if isinstance(endpoint, str) and endpoint else DEFAULT_ENDPOINT
        if endpoint.endswith('/graphql'):
            endpoint = endpoint.removesuffix('/graphql')
        cls.endpoint = endpoint
        # initialize kwargs first
        for param, val in kwargs.items():
            if hasattr(cls, param):
                setattr(cls, param, val)

        if user_id is not None or cls.user_id is None:
            if user_id is not None:
                try:
                    uuid.UUID(user_id)
                except ValueError:
                    user_id = None
            cls.user_id = user_id or gen_uuid(container=cls.container)

        # Do not set automatically, leave to developers
        if session_id is not None:
            try:
                uuid.UUID(session_id)
                cls.session_id = session_id
            except (ValueError, AttributeError):
                pass

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
            if field not in ('_is_setup', '_file', '_pid')
        }
        # TODO: Make safe when multiprocessing
        _secure_write(filename, json.dumps(config))
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


@suppress_errors
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


def clear_user_id() -> None:
    """
    Remove persistent user identity and reset the in-memory user ID.

    After calling this, the next setup() will generate a new user ID (or an ephemeral
    one if MIGAS_OPTOUT is set).
    """
    user_id_file = _get_user_id_file()
    if user_id_file is not None:
        try:
            user_id_file.unlink(missing_ok=True)
        except OSError:
            pass
    Config.user_id = None


def _try_load(filename) -> bool:
    """Attempt to load a configuration file. Returns True if successful."""
    try:
        return Config.load(filename) is True
    except (FileNotFoundError, IsADirectoryError):
        return False


def gen_uuid(uuid_factory: str = 'safe', container: str | None = None) -> str | None:
    """
    Generate a RFC 4122 UUID.

    Depending on what `uuid_factory` is provided, the UUID will be generated differently:
    - `safe`: Stable across processes; prefers persistent file, then FQDN domain, then hostname.
    - `random`: Random UUID; may collide across multiprocessing setups.
    """
    if uuid_factory == 'safe':
        return _safe_uuid_factory()
    elif uuid_factory == 'random':
        return str(uuid.uuid4())
    raise NotImplementedError


def _get_user_id_file() -> Path | None:
    """Return XDG-aware path for the persistent user identity file, or None if unavailable."""
    try:
        xdg = os.getenv('XDG_CONFIG_HOME')
        config_home = Path(xdg) if xdg else (Path.home() / '.config')
        return config_home / 'migas' / 'user_id'
    except Exception:
        return None


def _extract_domain(fqdn: str) -> str | None:
    """
    Extract a stable domain from a Fully Qualified Domain Name, stripping the node/host prefix.

    Returns None for single-label names, mDNS .local addresses, and two-part
    names (ambiguous — could be a Windows workgroup name).
    """
    parts = fqdn.split('.')
    if len(parts) < 3:
        return None
    if parts[-1] == 'local':
        return None
    return '.'.join(parts[1:])


def _safe_uuid_factory() -> str | None:
    """
    Generate or retrieve a stable user UUID.

    When MIGAS_OPTOUT is set, returns an ephemeral random UUID — no persistent file
    is read or written, and no identifying information (user@hostname) is used.

    Otherwise, priority is:
    1. Load from persistent file (~/.config/migas/user_id or $XDG_CONFIG_HOME/migas/user_id)
    2. Derive from user@domain using FQDN (stable across HPC nodes on the same cluster)
    3. Fall back to user@hostname (current behaviour, works for local/laptop use)

    The generated UUID is saved to the persistent file for future reuse when possible.
    """
    if os.getenv('MIGAS_OPTOUT'):
        return None

    user_id_file = _get_user_id_file()

    # 1. Try loading config file
    if user_id_file and user_id_file.is_file():
        with contextlib.suppress(OSError, ValueError):
            _chmod600(user_id_file)
            user_id = user_id_file.read_text().strip()
            uuid.UUID(user_id)  # validate
            return user_id

    # 2. Otherwise generate
    user_id = _generate_stable_uuid()

    # 3. Try to preserve user id
    if user_id_file:
        with contextlib.suppress(OSError):
            _secure_write(user_id_file, user_id)

    return user_id


def _get_username() -> str:
    """Get the current username, with fallback to UID-based name."""
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        return f'user-{os.getuid()}'


def _generate_stable_uuid() -> str:
    """Generate a stable UUID based on user and system information, or random if it fails."""
    try:
        user = _get_username()
        fqdn = socket.getfqdn()
        domain = _extract_domain(fqdn)
        hostname = os.getenv('HOSTNAME') or socket.gethostname()

        name = f'{user}@{domain or hostname}'
        return str(uuid.uuid3(uuid.NAMESPACE_DNS, name))
    except OSError:
        return str(uuid.uuid4())


logger = _init_logger()
