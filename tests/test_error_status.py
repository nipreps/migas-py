from migas.error import status_from_exception, status_from_signal, inspect_error


def test_status_from_exception_none():
    assert status_from_exception(None) == {'status': 'C', 'status_desc': 'Completed'}


def test_status_from_exception():
    exc = ValueError('Test error')
    status = status_from_exception(exc)
    assert status['status'] == 'F'
    assert status['status_desc'] == 'Errored'
    assert status['error_type'] == 'ValueError'
    assert status['error_desc'] == 'Test error'


def test_status_from_exception_keyboard_interrupt():
    exc = KeyboardInterrupt()
    status = status_from_exception(exc)
    assert status['status'] == 'S'
    assert status['status_desc'] == 'Suspended'


def test_status_from_exception_custom_handler():
    def custom_handler(etype, evalue, etb):
        return {'status': 'R', 'status_desc': f'Custom: {evalue}'}

    exc = ValueError('Custom error')
    status = status_from_exception(exc, error_funcs={'ValueError': custom_handler})
    assert status['status'] == 'R'
    assert status['status_desc'] == 'Custom: Custom error'


def test_status_from_signal():
    import signal

    status = status_from_signal(signal.SIGTERM)
    assert status['status'] == 'S'
    assert 'SIGTERM' in status['status_desc']


def test_inspect_error_fallback(monkeypatch):
    import sys

    # Clear sys.last_exc if it exists to test last_type fallback
    if hasattr(sys, 'last_exc'):
        monkeypatch.delattr(sys, 'last_exc', raising=False)

    monkeypatch.setattr(sys, 'last_type', ValueError, raising=False)
    monkeypatch.setattr(sys, 'last_value', ValueError('Last error'), raising=False)
    monkeypatch.setattr(sys, 'last_traceback', None, raising=False)

    status = inspect_error()
    assert status['status'] == 'F'
    assert status['error_desc'] == 'Last error'


def test_inspect_error_last_exc(monkeypatch):
    import sys

    exc = ValueError('Last exc')
    monkeypatch.setattr(sys, 'last_exc', exc, raising=False)

    status = inspect_error()
    assert status['status'] == 'F'
    assert status['error_desc'] == 'Last exc'
