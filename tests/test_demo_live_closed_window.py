from tools.demo_live import completed_window


def test_sdk_roll_before_local_boundary_excludes_unfinished_bar():
    rows = [{'time': i * 60} for i in range(302)]
    selected = completed_window(rows, 301 * 60 - .37)
    assert len(selected) == 300
    assert selected[-1]['time'] == 299 * 60
    assert all(row['time'] + 60 <= 301 * 60 - .37 for row in selected)


def test_exact_boundary_accepts_only_completed_bar():
    rows = [{'time': i * 60} for i in range(302)]
    assert completed_window(rows, 301 * 60)[-1]['time'] == 300 * 60


def test_stale_or_short_history_cannot_produce_signal():
    assert completed_window([{'time': i * 60} for i in range(299)], 300 * 60) is None
    assert completed_window([{'time': i * 60} for i in range(300)], 302 * 60) is None
