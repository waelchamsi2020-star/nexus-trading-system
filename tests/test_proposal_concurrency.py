"""Conflicting reviewers use independent SQLite connections, never live policy."""
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from nexus.learning.proposals import ProposalStore


@pytest.mark.parametrize("reviews,expected", [
    ([True, False], ["COMMITTED", "TERMINAL_CONFLICT"]),
    ([True, True], ["COMMITTED", "COMMITTED"]),
])
def test_concurrent_reviews_only_one_terminal_audit_commits(tmp_path, reviews, expected):
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"fixture":"synthetic"}', encoding="utf-8")
    path = tmp_path / "proposals.db"
    initial = ProposalStore(path, "fixture-account")
    try:
        initial.create_proposal("threshold", 1, 2, evidence, "proposal")
        barrier = threading.Barrier(2)
        read_bytes = Path.read_bytes

        def synchronized_evidence_read(file):
            blob = read_bytes(file)
            # Both reviewers have read PENDING before either writes.
            barrier.wait(timeout=10)
            return blob

        def review(approve):
            store = ProposalStore(path, "fixture-account")
            try:
                try:
                    if approve:
                        store.approve_proposal("proposal", "review A")
                    else:
                        store.reject_proposal("proposal", "review B")
                    return "COMMITTED"
                except ValueError:
                    return "TERMINAL_CONFLICT"
            finally:
                store.close()

        with patch.object(Path, "read_bytes", synchronized_evidence_read), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(review, reviews))
        assert sorted(results) == expected
        audit = initial.db.execute(
            "SELECT status FROM proposal_audit ORDER BY id"
        ).fetchall()
        assert len(audit) == 2
        assert audit[0][0] == "PENDING"
        assert audit[1][0] == initial.list_proposals()[0]["status"]
    finally:
        initial.close()
