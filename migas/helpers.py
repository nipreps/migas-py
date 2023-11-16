from __future__ import annotations

import atexit

from migas.operations import add_project
from migas.error import inspect_error


def track_exit(project: str, version: str, error_funcs: dict | None = None, **kwargs) -> None:
    """
    Registers a final breadcrumb to be sent upon process termination.

    This supplements `migas.operations.add_breadcrumb` by inferring the final process status
    on whether exception information is available. If so, rough exception information is relayed
    to the server.

    Additional customization is supported by using the `error_funcs` parameters, which accepts
    a dictionary consisting of <error-name, function-to-handle-error> key/value pairs. Note that
    expected outputs of the function are keyword arguments for `migas.operations.add_breadcrumb`.
    """
    atexit.register(_final_breadcrumb, project, version, error_funcs, **kwargs)

def _final_breadcrumb(
    project: str,
    version: str,
    error_funcs: dict | None = None,
    **ping_kwargs,
) -> dict:
    status_kwargs = inspect_error(error_funcs)
    kwargs = {**ping_kwargs, **status_kwargs}
    return add_project(project, version, **kwargs)
