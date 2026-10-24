"""Packaging must not ship account ledgers, backups or build trees."""
import pytest

from tools.release_files import distribution_safe, source_files


@pytest.mark.parametrize('name', ['data/demo/trades.db', 'src/trades.db-wal',
    'src/live.sqlite3', 'src/live.sqlite3-shm', 'tools/.env', 'reports/status.json',
    '.git/config', 'src/__pycache__/app.pyc', '../secret', 'tools/key.pem'])
def test_private_runtime_file_rejected(name):
    assert not distribution_safe(name)


def test_source_archive_allowlist_retains_rebuild_inputs_only(tmp_path):
    expected = {'src/nexus/app.py', 'tools/demo_live.py', 'ui/app.js',
                'requirements.txt', '.github/workflows/ci.yml'}
    denied = {'Windows-repair/app.exe', 'build-repair/cache', 'data/demo/trades.db',
              'reports/account.json', '.git/config', 'src/local.db', 'tools/.env'}
    for name in expected | denied:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('fixture', encoding='utf-8')
    assert {p.relative_to(tmp_path).as_posix() for p in source_files(tmp_path)} == expected
