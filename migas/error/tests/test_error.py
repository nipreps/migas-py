import sys

import pytest


class CustomException(Exception):
    ...


def sample_error_func(etype: type, evalue: str, etb: str):
    ename = etype.__name__
    if ename == "CustomException":
        return {
            'status': 'F',
            'status_desc': 'Custom Error!',
            'error_type': ename,
            'error_desc': 'Custom Error!',
        }


@pytest.mark.parametrize('error_funcs,error_type,status,error_desc', [
    (None, None, 'C', None),
    (None, KeyboardInterrupt, 'S', None),
    (None, FileNotFoundError, 'F', "i'm a teapot"),
    ({'CustomException': sample_error_func}, CustomException, 'F', 'Custom Error!'),
])
def test_inspect_error(monkeypatch, error_funcs, error_type, status, error_desc):

    # do not actually call the server
    if error_type:
        error = error_type(error_desc)
        monkeypatch.setattr(sys, 'last_type', error_type, raising=False)
        monkeypatch.setattr(sys, 'last_value', error, raising=False)
        monkeypatch.setattr(sys, 'last_traceback', 'Traceback...', raising=False)

    from migas.error import inspect_error
    res = inspect_error(error_funcs)

    assert res.get('status') == status
    if error_desc:
        assert res.get('error_desc') == error_desc
