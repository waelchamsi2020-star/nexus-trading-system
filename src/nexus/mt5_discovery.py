"""Discover installed MetaTrader 5 terminals without connecting or logging in."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

_SKIP_DIRS = {"windowsapps", "packages", "temp", "cache", "caches", "node_modules"}


def _terminal_in(directory: Path) -> list[Path]:
    found = []
    for name in ("terminal64.exe", "terminal.exe"):
        candidate = directory / name
        if candidate.is_file():
            found.append(candidate.resolve())
    return found


def _registered_terminals() -> list[Path]:
    if os.name != "nt":
        return []
    import winreg

    found: list[Path] = []
    uninstall_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    views = (getattr(winreg, "KEY_WOW64_64KEY", 0), getattr(winreg, "KEY_WOW64_32KEY", 0))
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in views:
            try:
                root = winreg.OpenKey(hive, uninstall_path, 0, winreg.KEY_READ | view)
            except OSError:
                continue
            with root:
                for index in range(winreg.QueryInfoKey(root)[0]):
                    try:
                        subkey = winreg.OpenKey(root, winreg.EnumKey(root, index))
                    except OSError:
                        continue
                    with subkey:
                        try:
                            display_name = str(winreg.QueryValueEx(subkey, "DisplayName")[0])
                        except OSError:
                            continue
                        if not re.search(r"meta\s*trader\s*5|\bmt5\b", display_name, re.IGNORECASE):
                            continue
                        for field in ("InstallLocation", "DisplayIcon"):
                            try:
                                value = str(winreg.QueryValueEx(subkey, field)[0]).strip().strip('"')
                            except OSError:
                                continue
                            value = re.sub(r",\d+$", "", value).strip().strip('"')
                            candidate = Path(value)
                            if candidate.is_file() and candidate.name.lower() in {"terminal.exe", "terminal64.exe"}:
                                found.append(candidate.resolve())
                            elif candidate.is_dir():
                                found.extend(_terminal_in(candidate))
    return found


def discover_mt5_terminals(environ: dict[str, str] | None = None) -> list[dict[str, str]]:
    """List terminal executables in registry, PATH and common installation roots.

    Discovery does not initialize MT5, inspect accounts, or submit requests.
    The user chooses a path before the app connects.
    """
    env = os.environ if environ is None else environ
    found = set(_registered_terminals())
    path_candidate = shutil.which("terminal64.exe") or shutil.which("terminal.exe")
    if path_candidate:
        found.add(Path(path_candidate).resolve())

    roots = []
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        value = env.get(key)
        if value:
            root = Path(value)
            roots.append(root / "Programs" if key == "LOCALAPPDATA" else root)
    for root in roots:
        found.update(_terminal_in(root))
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or child.name.casefold() in _SKIP_DIRS:
                continue
            found.update(_terminal_in(child))

    return [
        {"path": str(path), "name": path.parent.name or path.stem}
        for path in sorted(found, key=lambda item: (item.parent.name.casefold(), str(item).casefold()))
        if path.is_file()
    ]
