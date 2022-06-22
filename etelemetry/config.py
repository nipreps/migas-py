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
class ETConfig:
    endpoint: str = None
    user_id: uuid.UUID = None
    _is_setup = False


def load(filename: File = CONFIG_FILENAME) -> bool:
    """Load existing configuration file, or create a new one."""
    config = json.loads(Path(filename).read_text())
    ETConfig.endpoint = config.get("endpoint")
    user_id = config.get("user_id")
    if user_id:
        ETConfig.user_id = uuid.UUID(user_id)
    ETConfig._is_setup = True
    return True


def save(filename: File = CONFIG_FILENAME) -> str:
    """Save to a file."""
    config = {
        field: getattr(ETConfig, field) for field in ETConfig.__annotations__.keys()
    }
    # TODO: Make safe when multiprocessing
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    Path(filename).write_text(json.dumps(config))
    return str(filename)


def setup(et_endpoint: str = None, user_id: uuid.UUID = None, filename: File = CONFIG_FILENAME):
    """Configure the client, and save configuration to an output file."""
    if ETConfig._is_setup:
        return
    if Path(filename).exists():
        return load(filename)
    ETConfig.endpoint = et_endpoint or DEFAULT_ENDPOINT
    ETConfig.user_id = user_id or gen_user_uuid()
    ETConfig._is_setup = True
    save(filename)


def gen_user_uuid(uuid_factory: str = "safe") -> uuid.UUID:
    """
    Generate a user ID in UUID format.

    Depending on what `uuid_factory` is provided, the user ID will be generated differently:
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
    if uuid_factory == "random":
        return uuid.uuid4()
    raise NotImplementedError


def _safe_uuid_factory() -> uuid.UUID:
    import getpass
    import socket

    name = f"{getpass.getuser()}@{os.getenv('HOSTNAME', socket.gethostname())}"
    return str(uuid.uuid3(uuid.NAMESPACE_DNS, name))
