import sys

import pytest

import migas
from migas.tests.utils import patched_add_project


class CustomException(Exception):
    ...


def sample_error_func(etype: Exception, evalue: str, etb: str):
    ename = etype.__name__
    if ename == "CustomException":
        return {
            'status': 'F',
            'status_desc': 'Custom Error!',
            'error_type': ename,
            'error_desc': 'Custom Error!',
        }


@pytest.mark.parametrize('error_funcs,error,status,error_desc', [
    (None, None, 'C', None),
    (None, KeyboardInterrupt, 'S', None),
    (None, KeyError, 'F', 'KeyError: \'foo\''),
    ({'CustomException': sample_error_func}, CustomException, 'F', 'Custom Error!'),
])
def test_final_breadcrumb(setup_migas, monkeypatch, error_funcs, error, status, error_desc):

    # do not actually call the server
    monkeypatch.setattr(migas.operations, 'add_project', patched_add_project)
    if error is not None:
        monkeypatch.setattr(sys, 'last_type', error, raising=False)
        monkeypatch.setattr(sys, 'last_value', error_desc, raising=False)
        monkeypatch.setattr(sys, 'last_traceback', 'Traceback...', raising=False)

    from migas.helpers import _final_breadcrumb
    res = _final_breadcrumb('nipreps/migas-py', '0.0.1', error_funcs)

    assert res.get('status') == status
    if error_desc is not None:
        assert res.get('error_desc') == error_desc
