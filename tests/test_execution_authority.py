import subprocess
import sys

import pytest

from nexus.execution import Executor
from nexus.execution_authority import ExecutionAuthorityBusy, ExecutionAuthorityLease


def test_execution_lease_excludes_a_second_process_and_releases_on_exit(tmp_path):
    lock_path = tmp_path / "execution-authority.lock"
    lease = ExecutionAuthorityLease(lock_path, owner="test-parent").acquire()
    script = (
        "import sys; from nexus.execution_authority import ExecutionAuthorityLease, "
        "ExecutionAuthorityBusy; "
        "lease=ExecutionAuthorityLease(sys.argv[1], owner='test-child'); "
        "\ntry: lease.acquire()\n"
        "except ExecutionAuthorityBusy: print('BUSY'); raise SystemExit(0)\n"
        "print('ACQUIRED'); lease.release()"
    )
    try:
        blocked = subprocess.run([sys.executable, "-c", script, str(lock_path)],
                                 capture_output=True, text=True, check=False)
        assert blocked.returncode == 0
        assert blocked.stdout.strip() == "BUSY"
    finally:
        lease.release()

    available = subprocess.run([sys.executable, "-c", script, str(lock_path)],
                               capture_output=True, text=True, check=False)
    assert available.returncode == 0
    assert available.stdout.strip() == "ACQUIRED"


def test_execution_lease_rejects_duplicate_local_acquisition(tmp_path):
    path = tmp_path / "execution-authority.lock"
    first = ExecutionAuthorityLease(path, owner="first").acquire()
    second = ExecutionAuthorityLease(path, owner="second")
    try:
        with pytest.raises(ExecutionAuthorityBusy):
            second.acquire()
    finally:
        first.release()


def test_executor_refuses_prepared_intent_while_demo_service_owns_authority(tmp_path):
    path = tmp_path / "execution-authority.lock"
    demo_lease = ExecutionAuthorityLease(path, owner="demo_live").acquire()

    class IntentStore:
        def __init__(self):
            self.intent_state = "PREPARED"
            self.reason = None

        def intent(self, _intent_id):
            return {"state": self.intent_state}

        def set_intent_state(self, _intent_id, state, *, reason):
            self.intent_state, self.reason = state, reason

    executor = Executor.__new__(Executor)
    executor._execution_lease_path = path
    executor.store = IntentStore()
    executor._send_with_authority_lease = lambda *_args: pytest.fail(
        "Broker send path must not be reached when the Demo service owns the lock")
    try:
        result = executor._send("prepared-intent", entry=True)
        assert result["state"] == "REFUSED"
        assert executor.store.intent_state == "REJECTED"
        assert "Execution authority unavailable" in executor.store.reason
    finally:
        demo_lease.release()

