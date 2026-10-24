"""Explicit source distribution selection; runtime data never belongs in archives."""
from pathlib import Path

SOURCE_FOLDERS = {'src', 'tools', 'tests', 'ui', 'bridge', 'docs', 'config', '.github', 'licenses'}
SOURCE_FILES = {'launch.py', 'pyproject.toml', '.ruff.toml', '.gitignore',
                'README.md', 'CHANGELOG.md', 'THIRD-PARTY-NOTICES.md',
                'requirements.txt', 'requirements-dev.txt', 'requirements-build.txt',
                'build.ps1', 'setup.ps1', 'run.bat', 'run.sh'}


def distribution_safe(relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        return False
    parts = {part.lower() for part in path.parts}
    if parts & {'__pycache__', '.git', '.venv', 'node_modules', 'reports', 'data',
                '.pytest_cache', '.mypy_cache', '.ruff_cache'}:
        return False
    name = path.name.lower()
    return not (name.startswith('.env') or path.suffix.lower() in
                {'.db', '.sqlite', '.sqlite3', '.pyc', '.pem', '.key'} or
                name.endswith(('-wal', '-shm', '-journal')))


def source_files(root):
    root = Path(root)
    for name in sorted(SOURCE_FILES):
        file = root / name
        if file.is_file() and not file.is_symlink():
            yield file
    for name in sorted(SOURCE_FOLDERS):
        folder = root / name
        if not folder.is_dir() or folder.is_symlink():
            continue
        for file in sorted(folder.rglob('*')):
            relative = file.relative_to(root)
            if (file.is_file() and distribution_safe(relative) and
                    not any(parent.is_symlink() for parent in (file, *file.parents) if parent != root.parent) and
                    file.resolve().is_relative_to(root.resolve())):
                yield file
