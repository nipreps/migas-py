from __future__ import annotations

import re
import sys

from bdb import BdbQuit


def inspect_error(error_funcs: dict | None = None) -> dict:
    # Catch handled errors as well
    etype, err, etb = sys.exc_info()

    if (etype, err, etb) == (None, None, None):
        # Python 3.12+
        if hasattr(sys, 'last_exc'):
            err = sys.last_exc

        # < 3.12 fallback
        elif hasattr(sys, 'last_type'):
            etype = sys.last_type
            err = sys.last_value
            etb = sys.last_traceback

    if err:
        return status_from_exception(err, error_funcs)

    return {'status': 'C', 'status_desc': 'Completed'}


def status_from_exception(exc: BaseException | None, error_funcs: dict | None = None) -> dict:
    """
    Derive status kwargs from an explicit exception object.

    Note: This is only useful if calling `migas.track()` as a context manager,
    since errors may otherwise be out of scope.
    """
    if exc is None:
        return {'status': 'C', 'status_desc': 'Completed'}

    ename = type(exc).__name__
    evalue = exc.args[0] if exc.args else str(exc)
    etb = exc.__traceback__

    if isinstance(error_funcs, dict):
        # 1. Try class-based matches (preferred)
        for key, func in error_funcs.items():
            if isinstance(key, type) and issubclass(key, BaseException) and isinstance(exc, key):
                return func(type(exc), evalue, etb)

        # 2. Fallback to string-based matches
        if ename in error_funcs:
            func = error_funcs[ename]
            return func(type(exc), evalue, etb)

    if isinstance(exc, (KeyboardInterrupt, BdbQuit)):
        return {'status': 'S', 'status_desc': 'Suspended'}

    return {'status': 'F', 'status_desc': 'Errored', 'error_type': ename, 'error_desc': evalue}


def status_from_signal(signum: int) -> dict:
    """Derive status kwargs from a signal number."""
    import signal as _signal

    try:
        name = _signal.Signals(signum).name
    except (ValueError, AttributeError):
        name = f'signal {signum}'
    return {'status': 'S', 'status_desc': f'Terminated ({name})'}


def strip_filenames(text: str) -> str:
    paths = set(re.findall(r'(?:/[^/]+)[/\w\.-]*', text))
    for path in paths:
        text = text.replace(path, '<redacted>')
    return text
