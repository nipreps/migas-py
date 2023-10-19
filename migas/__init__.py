try:
    from ._version import __version__
except ImportError:
    __version__ = "0+unknown"

from .config import print_config, setup
from .helpers import track_exit
from .operations import add_project, get_usage

__all__ = (
    "__version__",
    "add_project",
    "get_usage",
    "print_config",
    "setup",
    "track_exit",
)

