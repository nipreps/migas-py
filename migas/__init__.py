from . import _version

__version__ = _version.get_versions()['version']

from .config import print_config, setup
from .operations import add_project, get_usage

__all__ = (
    "__version__",
    "add_project",
    "get_usage",
    "print_config",
    "setup",
)
