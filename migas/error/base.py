from __future__ import annotations

import re
import sys


def inspect_error(error_funcs: dict | None = None) -> dict:
    # Catch handled errors as well
    etype, err, etb = sys.exc_info()

    if (etype, err, etb) == (None, None, None):
        # Python 3.12, new method
        # MG: Cannot reproduce behavior while testing with 3.12.0
        # if hasattr(sys, 'last_exc'):
        #     etype, evalue, etb = sys.last_exc

        # < 3.11
        if hasattr(sys, 'last_type'):
            etype = sys.last_type
            err = sys.last_value
            etb = sys.last_traceback

    if err and etype:
        evalue = err.args[0]
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


def strip_filenames(text: str) -> str:
    paths = set(re.findall(r'(?:/[^/]+)[/\w\.-]*', text))
    for path in paths:
        text = text.replace(path, '<redacted>')
    return text
