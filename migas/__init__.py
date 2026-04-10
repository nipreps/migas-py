try:
    from ._version import __version__
except ImportError:
    __version__ = '0+unknown'

from .config import clear_user_id, print_config, setup
from .tracker import track, track_exit
from .api import add_breadcrumb, check_project, get_usage

__all__ = (
    '__version__',
    'add_breadcrumb',
    'check_project',
    'clear_user_id',
    'get_usage',
    'print_config',
    'setup',
    'track',
    'track_exit',
)
