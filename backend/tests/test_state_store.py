from app.state_store import StateStore


def test_connection_status_unconfigured_when_no_dsn():
    store = StateStore(dsn=None)
    status = store.connection_status()
    assert status["configured"] is False
    assert status["connected"] is False


def test_connection_status_reports_failure_for_unreachable_dsn():
    # A syntactically-plausible but unroutable DSN should fail fast and be reported as such,
    # not silently swallowed — this is the exact case that hid a real production bug.
    store = StateStore(dsn="postgresql://user:pass@127.0.0.1:1/doesnotexist")
    status = store.connection_status()
    assert status["configured"] is True
    assert status["connected"] is False
    assert "connection failed" in status["detail"]


def test_in_memory_store_round_trips_without_a_dsn():
    store = StateStore(dsn=None)
    store.save("key", {"a": 1})
    assert store.load("key", {}) == {"a": 1}
