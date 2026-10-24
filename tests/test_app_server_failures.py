"""Regression checks for isolated desktop startup and failed UI snapshots."""
import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import Mock

import pytest

from nexus import app
from nexus.server import LocalServer


@pytest.mark.parametrize('integrated', [True, False])
def test_desktop_connects_only_one_execution_owner(tmp_path, monkeypatch, integrated):
    if integrated:
        marker = tmp_path / 'demo-live-20261019' / 'user-controls-enabled'
        marker.parent.mkdir()
        marker.touch()
    engine = Mock(running=False)
    server = Mock()
    server.start.return_value = 'http://127.0.0.1:1234'
    monkeypatch.setattr(app, 'Engine', Mock(return_value=engine))
    monkeypatch.setattr(app, 'DemoBridge', Mock())
    monkeypatch.setattr(app, 'LocalServer', Mock(return_value=server))
    monkeypatch.setattr(app, 'InstanceLock', Mock())
    monkeypatch.setattr(app.sys, 'argv', ['app', '--headless', '--data-dir', str(tmp_path)])
    assert app.main() == 0
    engine.start_worker.assert_called_once_with(auto_connect=True)
    engine.stop_worker.assert_called_once()


@pytest.mark.parametrize('route', ['/api/state', '/api/action-result?id=fixture'])
def test_snapshot_failure_returns_actionable_503_without_private_detail(route):
    engine = Mock()
    engine.snapshot_json.side_effect = OSError('private-database-path')
    engine.action_result.side_effect = OSError('private-database-path')
    server = LocalServer(engine, Path(__file__).parents[1] / 'ui')
    server.start()
    try:
        request = urllib.request.Request(server.origin + route,
                                         headers={'X-Nexus-Token': server.token})
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        assert caught.value.code == 503
        body = json.load(caught.value)
        assert body['ok'] is False
        assert 'private-database-path' not in body['error']
    finally:
        server.stop()


def test_action_array_rejected_before_dispatch():
    engine = Mock()
    server = LocalServer(engine, Path(__file__).parents[1] / 'ui')
    server.start()
    try:
        request = urllib.request.Request(server.origin + '/api/action', data=b'[]',
            headers={'X-Nexus-Token': server.token, 'Content-Type': 'application/json'})
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        assert caught.value.code == 400
        engine.action.assert_not_called()
    finally:
        server.stop()
