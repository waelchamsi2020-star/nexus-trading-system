import json
from unittest.mock import Mock

import pytest

from nexus.broker import BrokerError, MT5Broker


@pytest.mark.parametrize("payload", ["[]", '"bridge"', "null", "42"])
def test_non_object_bridge_fails_closed(tmp_path, payload):
    bridge_path = tmp_path / "NEXUS_bridge.json"
    bridge_path.write_text(payload, encoding="utf-8")
    broker = MT5Broker.__new__(MT5Broker)
    broker.bridge_path = bridge_path
    broker.account = Mock(side_effect=AssertionError("invalid bridge must be rejected before account lookup"))

    with pytest.raises(BrokerError, match="الجسر غير صالح"):
        broker._bridge()

    broker.account.assert_not_called()


def test_non_object_bridge_returns_safe_unavailable_session_and_calendar(tmp_path):
    bridge_path = tmp_path / "NEXUS_bridge.json"
    bridge_path.write_text(json.dumps([]), encoding="utf-8")
    broker = MT5Broker.__new__(MT5Broker)
    broker.bridge_path = bridge_path

    session = broker.session("EURUSD")
    calendar = broker.calendar()

    assert session["known"] is False
    assert session["open"] is False
    assert "bridge root must be an object" in session["reason"]
    assert calendar["ok"] is False
    assert calendar["events"] == []
    assert "bridge root must be an object" in calendar["reason"]
