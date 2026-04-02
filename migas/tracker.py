from __future__ import annotations

import atexit
import logging
import signal
import threading
from contextlib import ContextDecorator
from dataclasses import dataclass, field
from typing import Any

from migas.error import (
    inspect_error,
    resolve_error_handlers,
    status_from_exception,
    status_from_signal,
)

logger = logging.getLogger('migas-py')

# Module-level registry for idempotency
_active_trackers: dict[str, Tracker] = {}


@dataclass
class Tracker(ContextDecorator):
    project: str
    version: str
    error_handlers: str | dict | list | None = None
    signals: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM)
    init_ping: bool = True
    crumb_kwargs: dict = field(default_factory=dict)

    # Propagate existing handlers
    _previous_handlers: dict[int, Any] = field(default_factory=dict, repr=False)
    _started: bool = field(default=False, init=False, repr=False)
    _stopped: bool = field(default=False, repr=False)

    def __post_init__(self):
        self.error_handlers = resolve_error_handlers(self.error_handlers)
        self._install_atexit()
        self._install_signals()

    def start(self):
        """Send the initial breadcrumb and register tracker to avoid repeats."""
        if self._started or self._stopped:
            return

        from migas.api import add_breadcrumb

        if self.init_ping:
            add_breadcrumb(
                self.project, self.version, status='R', status_desc='Started', **self.crumb_kwargs
            )

        key = f'{self.project}@{self.version}'
        _active_trackers[key] = self
        self._started = True

    def _install_atexit(self):
        atexit.register(self._on_exit)

    def _install_signals(self):
        if threading.current_thread() is not threading.main_thread():
            logger.debug('Cannot install signal handlers from non-main thread')
            return
        for sig in self.signals:
            try:
                prev = signal.signal(sig, self._on_signal)
                self._previous_handlers[sig] = prev
            except ValueError:
                # This can happen if not in the main thread of the main interpreter
                logger.debug(f'Failed to install signal handler for {sig}')

    def _on_exit(self):
        """atexit callback — uses inspect_error() as best-effort fallback."""
        if self._stopped:
            return
        status_kwargs = inspect_error(self.error_handlers)
        self._send_final(**self.crumb_kwargs, **status_kwargs)

    def _on_signal(self, signum, frame):
        """Signal handler — synthesizes status from signal number."""
        if not self._stopped:
            status_kwargs = status_from_signal(signum)
            self._send_final(**self.crumb_kwargs, **status_kwargs)

        # Chain to previous handler
        prev = self._previous_handlers.get(signum, signal.SIG_DFL)
        if callable(prev):
            prev(signum, frame)
        elif prev == signal.SIG_DFL:
            # Re-raise the signal to allow default behavior (e.g. exit)
            signal.signal(signum, signal.SIG_DFL)
            signal.raise_signal(signum)

    def _send_final(self, **kwargs):
        """Send the final breadcrumb synchronously."""
        self._stopped = True
        from migas.api.rest import Breadcrumb
        from migas.config import Config
        from migas.request import _request

        payload = Breadcrumb.from_config(self.project, self.version, **kwargs).to_dict()
        # Use _request directly — no ThreadPoolExecutor during shutdown
        _request(Config.endpoint, path=Breadcrumb._route, json_data=payload)

    def stop(self, exc: BaseException | None = None):
        """Manually send final breadcrumb and deregister. Idempotent."""
        if self._stopped:
            return
        status_kwargs = status_from_exception(exc, self.error_handlers)
        self._send_final(**self.crumb_kwargs, **status_kwargs)
        self._cleanup()

    def _cleanup(self):
        """Restore signal handlers and unregister atexit."""
        atexit.unregister(self._on_exit)
        if threading.current_thread() is threading.main_thread():
            for sig, prev in self._previous_handlers.items():
                try:
                    signal.signal(sig, prev)
                except ValueError:
                    pass
            self._previous_handlers.clear()
        key = f'{self.project}@{self.version}'
        _active_trackers.pop(key, None)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop(exc_val)
        return False


def track(
    project: str,
    version: str,
    error_handlers: str | dict | list | None = None,
    signals: tuple[signal.Signals, ...] = (signal.SIGINT, signal.SIGTERM),
    init_ping: bool = True,
    **kwargs,
) -> Tracker:
    """
    Begin tracking a process. Returns a Tracker that works as a context manager,
    decorator, or standalone (atexit + signal handlers).

    If a tracker for the specified project and version is already active, that
    instance is returned.
    """
    key = f'{project}@{version}'
    if key in _active_trackers:
        return _active_trackers[key]

    tracker = Tracker(
        project=project,
        version=version,
        error_handlers=error_handlers,
        signals=signals,
        init_ping=init_ping,
        crumb_kwargs=kwargs,
    )
    tracker.start()
    return tracker


def track_exit(
    project: str, version: str, error_handlers: str | dict | list | None = None, **kwargs
) -> None:
    """
    Registers a final breadcrumb to be sent upon process termination.

    .. deprecated:: 0.4.0
        Use :func:`migas.track` instead.
    """
    import warnings

    warnings.warn(
        'track_exit() is deprecated, use migas.track() instead', DeprecationWarning, stacklevel=2
    )
    if kwargs.get('error_funcs') and error_handlers is None:
        # Old API compatiblity
        warnings.warn(
            'error_funcs is deprecated, use error_handlers instead',
            DeprecationWarning,
            stacklevel=2,
        )
        error_handlers = kwargs.pop('error_funcs')
    track(project, version, error_handlers, **kwargs)
