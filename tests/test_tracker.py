import pytest
import signal
from unittest.mock import patch
from migas.tracker import track, Tracker, _active_trackers

PROJ = 'nipreps/nipreps'
VER = '0.0.1'


def test_track_returns_tracker(mock_requests):
    tracker = track(PROJ, VER)
    try:
        assert isinstance(tracker, Tracker)
        assert mock_requests.add_breadcrumb.called
        assert mock_requests.add_breadcrumb.call_args[1]['status'] == 'R'
    finally:
        tracker.stop()


def test_tracker_context_manager(mock_requests):
    with track(PROJ, VER) as tracker:
        assert tracker.project == PROJ
        assert not tracker._stopped

    assert tracker._stopped
    assert mock_requests.request.called
    # Final breadcrumb should be sent on __exit__
    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'C'


def test_tracker_context_manager_exception(mock_requests):
    try:
        with track(PROJ, VER):
            raise ValueError('Context error')
    except ValueError:
        pass

    assert mock_requests.request.called
    # Final breadcrumb should be sent with error status
    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'F'
    assert mock_requests.request.call_args[1]['json_data']['proc']['error_type'] == 'ValueError'


def test_tracker_stop_idempotent(mock_requests):
    tracker = track(PROJ, VER)
    tracker.stop()
    assert mock_requests.request.call_count == 1
    tracker.stop()
    assert mock_requests.request.call_count == 1


def test_start_idempotency(mock_requests):
    t1 = track(PROJ, VER)
    assert f'{PROJ}@{VER}' in _active_trackers
    assert mock_requests.add_breadcrumb.call_count == 1

    t2 = track(PROJ, VER)
    try:
        assert t1 is t2
        # No extra pings sent
        assert mock_requests.add_breadcrumb.call_count == 1
    finally:
        t2.stop()
        t2.stop()


def test_signal_handling(mock_requests):
    # Only run this if we are in main thread
    import threading

    if threading.current_thread() is not threading.main_thread():
        pytest.skip('Signal test requires main thread')

    with patch('signal.signal') as mock_signal:
        tracker = track(PROJ, VER)
        try:
            assert mock_signal.called

            # Simulate signal
            tracker._on_signal(signal.SIGTERM, None)
            assert mock_requests.request.called
            assert tracker._stopped
        finally:
            tracker.stop()


def test_track_exit_deprecated(mock_requests):
    with pytest.warns(DeprecationWarning, match=r'track_exit\(\) is deprecated'):
        from migas.tracker import track_exit

        track_exit(PROJ, VER)
        # Cleanup
        key = f'{PROJ}@{VER}'
        if key in _active_trackers:
            _active_trackers[key].stop()


def test_track_nipype_preset(mock_requests):
    class NodeExecutionError(Exception):
        pass

    # Simulate a Nipype-style NodeExecutionError traceback
    traceback = "Exception raised while executing Node mynode\nTraceback: File '...', line 1, in <module>\nValueError: oops"
    with pytest.raises(NodeExecutionError):
        with track(PROJ, VER, error_handlers='nipype'):
            raise NodeExecutionError(traceback)

    assert mock_requests.request.called
    payload = mock_requests.request.call_args[1]['json_data']
    assert 'mynode' in payload['proc']['status_desc']
    assert 'ValueError: oops' in payload['proc']['error_desc']


def test_inheritance_dispatch(mock_requests):
    def base_handler(etype, evalue, etb):
        return {'status': 'F', 'status_desc': 'Caught by base'}

    # Use actual class as key
    with pytest.raises(ValueError):
        with track(PROJ, VER, error_handlers={Exception: base_handler}):
            raise ValueError('Specific error')

    assert mock_requests.request.called
    payload = mock_requests.request.call_args[1]['json_data']
    assert payload['proc']['status_desc'] == 'Caught by base'


def test_tracker_decorator(mock_requests):
    @track(PROJ, VER)
    def my_function():
        return True

    # At definition, track() was called, so 1 ping
    assert mock_requests.add_breadcrumb.called
    assert mock_requests.add_breadcrumb.call_args[1]['status'] == 'R'

    # Run function
    my_function()

    # After run, __exit__ should have sent final ping
    assert mock_requests.request.called
    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'C'

    @track(PROJ, VER)
    def failed():
        raise ValueError('Oops')

    with pytest.raises(ValueError):
        failed()

    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'F'
