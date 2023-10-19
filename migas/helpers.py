from __future__ import annotations

import atexit
import sys

from migas.operations import add_project


def track_exit(project: str, version: str, error_funcs: dict | None = None) -> None:
    atexit.register(_final_breadcrumb, project, version, error_funcs)

def _final_breadcrumb(project: str, version: str, error_funcs: dict | None = None) -> dict:
    kwargs = _inspect_error(error_funcs)
    return add_project(project, version, **kwargs)


def _inspect_error(error_funcs: dict | None) -> dict:
    etype, evalue, etb = None, None, None

    # Python 3.12, new method
    # MG: Cannot reproduce behavior while testing with 3.12.0
    # if hasattr(sys, 'last_exc'):
    #     etype, evalue, etb = sys.last_exc

    # < 3.11
    if hasattr(sys, 'last_type'):
        etype = sys.last_type
        evalue = sys.last_value
        etb = sys.last_traceback

    if etype:
        ename = etype.__name__

        if isinstance(error_funcs, dict) and ename in error_funcs:
            func = error_funcs[ename]
            kwargs = func(etype, evalue, etb)

        elif ename in ('KeyboardInterrupt', 'BdbQuit'):
            kwargs = {
                'status': 'S',
                'status_desc': 'Suspended',
            }

        else:
            kwargs = {
                'status': 'F',
                'status_desc': 'Errored',
                'error_type': ename,
                'error_desc': evalue,
            }
    else:
        kwargs = {
            'status': 'C',
            'status_desc': 'Completed',
        }

    return kwargs