from nexus.engine import Engine
from nexus.mt5_discovery import discover_mt5_terminals


def test_discovers_multiple_installations_under_program_roots(tmp_path):
    roots = {
        "ProgramFiles": tmp_path / "Program Files",
        "ProgramFiles(x86)": tmp_path / "Program Files (x86)",
        "LOCALAPPDATA": tmp_path / "Local App Data",
    }
    expected = [
        roots["ProgramFiles"] / "Capital MT5" / "terminal64.exe",
        roots["ProgramFiles(x86)"] / "Another Broker" / "terminal.exe",
        roots["LOCALAPPDATA"] / "Programs" / "MetaTrader" / "terminal64.exe",
    ]
    for path in expected:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"terminal placeholder")

    result = discover_mt5_terminals({key: str(value) for key, value in roots.items()})
    discovered = {item["path"] for item in result}
    assert {str(path.resolve()) for path in expected} <= discovered
    assert len(discovered) == len(result)
    assert all(item["name"] for item in result)


def test_engine_discovery_action_is_read_only_and_available_before_connect(monkeypatch):
    terminals = [{"name": "Capital MT5", "path": r"C:\Capital\terminal64.exe"}]
    monkeypatch.setattr("nexus.engine.discover_mt5_terminals", lambda: terminals)
    response = Engine._action(object.__new__(Engine), {"action": "discover_mt5_terminals"})
    assert response["ok"] is True
    assert response["terminals"] == terminals
    assert response["count"] == 1
