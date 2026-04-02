import pytest
import signal
from unittest.mock import patch
from migas.tracker import track, Tracker, _active_trackers


def test_track_returns_tracker(mock_requests):
    tracker = track('test/project', '1.0.0')
    try:
        assert isinstance(tracker, Tracker)
        assert mock_requests.add_breadcrumb.called
        assert mock_requests.add_breadcrumb.call_args[1]['status'] == 'R'
    finally:
        tracker.stop()


def test_tracker_context_manager(mock_requests):
    with track('test/project', '1.0.0') as tracker:
        assert tracker.project == 'test/project'
        assert not tracker._stopped

    assert tracker._stopped
    assert mock_requests.request.called
    # Final breadcrumb should be sent on __exit__
    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'C'


def test_tracker_context_manager_exception(mock_requests):
    try:
        with track('test/project', '1.0.0'):
            raise ValueError('Context error')
    except ValueError:
        pass

    assert mock_requests.request.called
    # Final breadcrumb should be sent with error status
    assert mock_requests.request.call_args[1]['json_data']['proc']['status'] == 'F'
    assert mock_requests.request.call_args[1]['json_data']['proc']['error_type'] == 'ValueError'


def test_tracker_stop_idempotent(mock_requests):
    tracker = track('test/project', '1.0.0')
    tracker.stop()
    assert mock_requests.request.call_count == 1
    tracker.stop()
    assert mock_requests.request.call_count == 1


def test_start_idempotency(mock_requests):
    track('test/project', '1.0.0')
    assert 'test/project@1.0.0' in _active_trackers

    t2 = track('test/project', '1.0.0')
    try:
        assert mock_requests.request.call_count == 1  # t1 was stopped
        assert _active_trackers['test/project@1.0.0'] is t2
    finally:
        t2.stop()


def test_signal_handling(mock_requests):
    # Only run this if we are in main thread
    import threading

    if threading.current_thread() is not threading.main_thread():
        pytest.skip('Signal test requires main thread')

    with patch('signal.signal') as mock_signal:
        tracker = track('test/project', '1.0.0')
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

        track_exit('test/project', '1.0.0')
        # Cleanup
        key = 'test/project@1.0.0'
        if key in _active_trackers:
            _active_trackers[key].stop()
