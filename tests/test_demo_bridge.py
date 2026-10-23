import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from nexus.demo_bridge import DemoBridge
from tools.demo_control import Controls
from tools.demo_limits import initialize


@pytest.fixture
def directory(tmp_path):
    (tmp_path / 'config.json').write_text(json.dumps({
        'account_login': 12345678, 'account_server': 'test-demo-server',
        'expires_at': time.time() + 3600}))
    with sqlite3.connect(tmp_path / "trades.db") as db:
        db.executescript("CREATE TABLE audit(at REAL,event TEXT,payload TEXT);"
                         "CREATE TABLE state(key TEXT PRIMARY KEY,value TEXT);"
                         "CREATE TABLE signals(bar INTEGER,reason TEXT);")
        initialize(db, {"daily_profit_amount": 100, "daily_loss_amount": 100,
                            "max_exposure_amount": 100, "max_trade_risk_percent": 2})
        db.execute("INSERT INTO signals VALUES(100,'NO_TRIGGER')")
    (tmp_path / "status.json").write_text(json.dumps({
        "utc": datetime.now(UTC).isoformat(), "mode": "DEMO_LIVE",
        "account": 12345678, "error": None, "balance": 400, "equity": 400,
        "daily_loss_limit": 100, "daily_profit_target": 100}))
    return tmp_path


def test_pause_and_resume_same_executor_with_audit(directory):
    controls = Controls(directory)
    controls.action({"action": "pause"})
    assert controls.snapshot()["user_paused"]
    controls.action({"action": "resume"})
    assert not controls.snapshot()["user_paused"]
    with sqlite3.connect(directory / "trades.db") as db:
        assert db.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 2


@pytest.mark.parametrize("offset", [-60, 60])
def test_stale_or_future_status_cannot_resume(directory, offset):
    path = directory / "status.json"
    value = json.loads(path.read_text())
    value["utc"] = datetime.fromtimestamp(time.time() + offset, UTC).isoformat()
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        Controls(directory).action({"action": "resume"})


@pytest.mark.parametrize("action", ["start", "approve", "flatten", "cancel", "simulation"])
def test_legacy_sender_cannot_be_activated(directory, action):
    bridge = DemoBridge(SimpleNamespace(snapshot=dict), directory)
    with pytest.raises(ValueError):
        bridge.action({"action": action})


def test_desktop_displays_actual_sender_and_rejections(directory):
    bridge = DemoBridge(SimpleNamespace(snapshot=lambda: {"mode": "READ_ONLY"}), directory)
    view = bridge.snapshot()
    assert view["mode"] == "AUTO_DEMO"
    assert view["demo_live"]["last_reasons"] == {"NO_TRIGGER": 1}
    bridge.action({"action": "stop"})
    assert bridge.snapshot()["mode"] == "READ_ONLY"


def test_stopped_stale_sender_keeps_identity_matched_read_only_market_view(directory):
    status_path = directory / 'status.json'
    status = json.loads(status_path.read_text())
    status.update(utc=datetime.fromtimestamp(time.time() - 3600, UTC).isoformat(),
                  error='DEMO_ACCOUNT_TRADING_PERMISSION_DISABLED')
    status_path.write_text(json.dumps(status))
    live = {'mode': 'READ_ONLY', 'status': 'CONNECTED',
            'account': {'login': 12345678, 'trade_mode': 0, 'server': 'test-demo-server',
                        'type': 'Demo', 'balance': 400, 'equity': 398},
            'terminal': {'connected': True, 'trade_allowed': True},
            'positions': [{'ticket': 77, 'magic': 20261019, 'symbol': 'EURUSD', 'sl': 1.08}],
            'orders': [], 'performance': {'rows': [{'magic': 741903}]},
            'risk': {'daily_loss': 12}, 'execution': {'mode': 'READ_ONLY'}}
    result = DemoBridge(SimpleNamespace(snapshot=lambda: live), directory).snapshot()
    assert result['status'] == 'READ_ONLY'
    assert result['mode'] == 'READ_ONLY'
    assert result['error'] is None
    assert result['account']['login'] == 12345678
    assert result['positions'] == [{'ticket': 77, 'magic': 20261019, 'symbol': 'EURUSD',
                                    'sl': 1.08, 'owned': True, 'side': 'UNKNOWN'}]
    assert result['performance']['source'] == 'UNAVAILABLE_WHILE_DEMO_SENDER_STOPPED'
    assert result['risk'] == {}
    assert result['execution']['entries_paused'] is True
    assert result['demo_live']['running'] is False
    assert result['demo_live']['read_only_fallback'] is True
    assert result['demo_live']['fresh'] is False


def test_limits_edits_reach_shared_journal(directory):
    bridge = DemoBridge(SimpleNamespace(snapshot=dict), directory)
    values = bridge.controls.snapshot()["limits"]["values"]
    values["daily_profit_amount"] = 42
    bridge.action({"action": "demo_limits", "revision": 0, "values": values})
    assert Controls(directory).snapshot()["limits"]["values"]["daily_profit_amount"] == 42


@pytest.mark.parametrize('failure', ['read_only', 'stop', 'halt', 'expiry', 'identity', 'naive_time'])
def test_resume_refuses_unsafe_authoritative_state(directory, failure):
    status_path = directory / 'status.json'
    status = json.loads(status_path.read_text())
    if failure == 'read_only':
        status['mode'] = 'READ_ONLY'
    elif failure == 'stop':
        (directory / 'STOP').write_text('upgrade')
    elif failure == 'halt':
        with sqlite3.connect(directory / 'trades.db') as db:
            db.execute("INSERT INTO state VALUES ('halt',?)", (json.dumps('BROKER_TIMEOUT'),))
    elif failure == 'expiry':
        path = directory / 'config.json'
        config = json.loads(path.read_text())
        config['expires_at'] = time.time() - 1
        path.write_text(json.dumps(config))
    elif failure == 'identity':
        status['account'] = 999
    else:
        status['utc'] = datetime.now().isoformat()
    status_path.write_text(json.dumps(status))
    controls = Controls(directory)
    controls.action({'action': 'pause'})
    with pytest.raises(ValueError):
        controls.action({'action': 'resume'})
    assert controls.snapshot()['user_paused']
    assert not controls.snapshot()['running']
    with sqlite3.connect(directory / 'trades.db') as db:
        assert db.execute("SELECT COUNT(*) FROM audit WHERE event='USER_ENTRIES_RESUMED'").fetchone()[0] == 0


@pytest.mark.parametrize('invalid', ['[]', '{broken', '{"utc":null}', '{"balance":NaN}'])
def test_invalid_status_is_safe_json_and_limits_remain_editable(directory, invalid):
    (directory / 'status.json').write_text(invalid)
    legacy = {'account': {'login': 88, 'trade_mode': 2},
              'positions': [{'ticket': 99}], 'status': 'CONNECTED',
              'risk': {'remaining': 999}, 'execution': {'mode': 'AUTO_DEMO'}}
    bridge = DemoBridge(SimpleNamespace(snapshot=lambda: dict(legacy)), directory)
    result = json.loads(bridge.snapshot_json())
    assert result['account'] == {}
    assert result['positions'] == []
    assert result['risk'] == {}
    assert result['status'] == 'DATA_ERROR'
    assert result['mode'] == 'READ_ONLY'
    assert result['demo_live']['limits']['revision'] == 0
    bridge.action({'action': 'demo_pause'})
    assert bridge.controls.snapshot()['user_paused']


def test_missing_journal_is_not_created_by_reader(tmp_path):
    result = Controls(tmp_path).snapshot()
    assert result['error'] and not result['running']
    assert not (tmp_path / 'trades.db').exists()


def test_no_legacy_positions_when_service_did_not_publish_positions(directory):
    bridge = DemoBridge(SimpleNamespace(snapshot=lambda: {'positions': [{'ticket': 88}]}), directory)
    assert bridge.snapshot()['positions'] == []
    assert bridge.snapshot()['account']['server'] == 'test-demo-server'


def test_pause_rolls_back_when_audit_write_fails(directory):
    with sqlite3.connect(directory / 'trades.db') as db:
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(FAIL,'disk failure'); END")
    with pytest.raises(sqlite3.Error):
        Controls(directory).action({'action': 'pause'})
    with sqlite3.connect(directory / 'trades.db') as db:
        assert db.execute("SELECT value FROM state WHERE key='user_paused'").fetchone() is None


def test_sqlite_status_remains_authoritative_over_fresh_mirror(directory):
    status = json.loads((directory / 'status.json').read_text())
    status.update(mode='READ_ONLY', error='AUTHORITATIVE_HALT')
    with sqlite3.connect(directory / 'trades.db') as db:
        db.execute("INSERT INTO state VALUES ('published_status',?)", (json.dumps(status),))
    result = Controls(directory).snapshot()
    assert not result['running']
    assert result['stop_reason'] == 'AUTHORITATIVE_HALT'


def test_desktop_browser_recovers_from_invalid_status_and_superseded_edit(directory):
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[1]
    state = Controls(directory).snapshot()
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('http://demo.test/', lambda route: route.fulfill(body='''
          <meta name="nexus-token" content="test"><main id="view-overview"><div class="account-grid"></div></main>
          <span id="header-execution-mode"></span><span id="connection-pill"></span><span id="footer-state"></span>''',
          content_type='text/html'))
        submitted = []
        def capture_limits(route):
            submitted.append(route.request.post_data_json)
            route.fulfill(json={'ok': True, 'limits': {'revision': 1}})
        page.route('http://demo.test/api/action', capture_limits)
        page.goto('http://demo.test/')
        page.add_script_tag(path=str(root / 'ui/demo-panel.js'))
        page.evaluate('data => renderDemoPanel(data)', state)
        assert page.locator('#demo-toggle').is_enabled()
        assert page.locator('#demo-limits-form input[type=number]').count() == 4
        page.locator('[name="daily_profit_amount"]').fill('42')
        page.locator('#demo-limits-form [type="submit"]').click()
        page.wait_for_function("document.querySelector('#demo-feedback').textContent.includes('حُفظت')")
        assert submitted[0]['values']['daily_profit_amount'] == 42
        for hidden in ('max_exposure_amount', 'max_trade_risk_percent', 'kill_drawdown_percent'):
            assert submitted[0]['values'][hidden] == state['limits']['values'][hidden]
        state['limits']['revision'] = 2
        state['limits']['values']['daily_profit_amount'] = 80
        page.evaluate('data => renderDemoPanel(data)', state)
        assert page.locator('[name="daily_profit_amount"]').input_value() == '80'
        assert 'أحدث' in page.locator('#demo-feedback').inner_text()
        state.update(error='CORRUPT_STATUS', running=False, fresh=False, status={})
        page.evaluate('data => renderDemoPanel(data)', state)
        assert page.locator('#demo-toggle').is_disabled()
        assert page.locator('#demo-open').inner_text() == '—'
        assert 'غير متاحة' in page.locator('#header-execution-mode').inner_text()
        # Limits remain editable when the journal is valid but the sender is stopped.
        assert page.locator('#demo-limits-form [type="submit"]').is_enabled()
        assert errors == []
        browser.close()


def test_standalone_browser_future_status_and_missing_journal_are_not_active(directory):
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[1]
    status_path = directory / 'status.json'
    status = json.loads(status_path.read_text())
    status['utc'] = datetime.fromtimestamp(time.time() + 60, UTC).isoformat()
    status_path.write_text(json.dumps(status))
    response = Controls(directory).snapshot()
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.route('http://demo.test/', lambda route: route.fulfill(
            body=(root / 'tools/demo_control_ui/index.html').read_text(encoding='utf-8')
                 .replace('<script src="/app.js" defer></script>', ''), content_type='text/html'))
        page.route('http://demo.test/style.css', lambda route: route.fulfill(body='', content_type='text/css'))
        page.route('http://demo.test/api/state', lambda route: route.fulfill(json=response))
        page.goto('http://demo.test/')
        page.add_script_tag(path=str(root / 'tools/demo_control_ui/app.js'))
        page.wait_for_function("document.querySelector('#status').textContent.includes('متوقف')")
        assert 'المنفّذ يعمل' not in page.locator('#status').inner_text()
        response = {'error': 'JOURNAL_MISSING', 'limits': None, 'running': False, 'status': {}}
        page.evaluate('refresh()')
        page.wait_for_function("document.querySelector('#status').textContent==='JOURNAL_MISSING'")
        assert page.locator('[type="submit"]').is_disabled()
        assert errors == []
        browser.close()
