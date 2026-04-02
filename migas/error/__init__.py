from migas.error.base import (
    inspect_error,
    status_from_exception,
    status_from_signal,
    strip_filenames,
)
from migas.error.nipype import node_execution_error

from types import MappingProxyType

ERROR_PRESETS = MappingProxyType({'nipype': {'NodeExecutionError': node_execution_error}})


def resolve_error_handlers(handlers: str | dict | list | None) -> dict:
    """Resolve error presets and custom dictionaries into a set of handler functions."""
    if handlers is None:
        return {}
    if isinstance(handlers, dict):
        return {**handlers}
    if isinstance(handlers, str):
        return {**ERROR_PRESETS.get(handlers, {})}
    if isinstance(handlers, list):
        resolved = {}
        for item in handlers:
            resolved.update(resolve_error_handlers(item))
        return resolved
    return {}


__all__ = [
    'inspect_error',
    'status_from_exception',
    'status_from_signal',
    'strip_filenames',
    'resolve_error_handlers',
    'ERROR_PRESETS',
]
