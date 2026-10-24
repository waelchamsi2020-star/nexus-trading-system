import sys
from unittest.mock import patch

from nexus.external_research import (
    ExternalResearchManager,
    _certificate_bundle,
    _verified_tls_context,
)


def test_certificate_bundle_uses_packaged_onedir_fallback(tmp_path):
    bundle_root = tmp_path / "_internal"
    cert_dir = bundle_root / "certifi"
    cert_dir.mkdir(parents=True)
    expected = cert_dir / "cacert.pem"
    expected.write_bytes(b"x" * 100_001)
    with patch("nexus.external_research.certifi.where", side_effect=FileNotFoundError("resource is archived")), \
         patch.object(sys, "_MEIPASS", str(bundle_root), create=True):
        assert _certificate_bundle() == expected


def test_tls_context_enforces_hostname_and_certificate_verification():
    context = _verified_tls_context()
    assert context.check_hostname is True
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.minimum_version.name == "TLSv1_2"


def test_frankfurter_parses_reference_rate_without_promoting_it_to_quote(tmp_path):
    manager = ExternalResearchManager(tmp_path / "external.json", clock=lambda: 1000, environ={})
    with patch("nexus.external_research._read_json", return_value={"rate": 1.08, "date": "2026-10-21"}):
        provider, items = manager._frankfurter(1000)
    assert provider["status"] == "OK"
    assert items[0]["rate"] == 1.08
    assert items[0]["kind"] == "reference_fx_rate"
    assert "ليس Bid/Ask" in provider["reason"]


def test_bls_and_world_bank_reject_empty_or_malformed_responses_independently(tmp_path):
    manager = ExternalResearchManager(tmp_path / "external.json", clock=lambda: 1000, environ={})
    with patch("nexus.external_research._read_json", return_value={"Results": {"series": [{"data": []}]}}):
        bls, bls_items = manager._bls(1000)
    with patch("nexus.external_research._read_json", return_value=[{}, []]):
        world_bank, wb_items = manager._world_bank(1000)
    assert bls["status"] == "ERROR" and not bls_items
    assert world_bank["status"] == "ERROR" and not wb_items


def test_massive_does_not_connect_or_claim_availability_without_key(tmp_path):
    manager = ExternalResearchManager(tmp_path / "external.json", clock=lambda: 1000, environ={})
    with patch("nexus.external_research._read_json") as read:
        provider, items = manager._massive(1000)
    assert provider["status"] == "CONFIG_REQUIRED"
    assert not items
    read.assert_not_called()


def test_public_source_network_error_is_reported_without_crashing_other_source(tmp_path):
    manager = ExternalResearchManager(tmp_path / "external.json", clock=lambda: 1000, environ={})
    with patch("nexus.external_research._read_json", side_effect=TimeoutError("fixture")):
        failed, items = manager._frankfurter(1000)
    assert failed["status"] == "ERROR"
    assert not items
    assert "TimeoutError" in failed["reason"]


def test_cached_external_research_is_versioned_and_staleness_is_recomputed(tmp_path):
    path = tmp_path / "external.json"
    manager = ExternalResearchManager(path, clock=lambda: 1000, environ={})
    manager.providers = [{"id": "frankfurter", "status": "OK", "last_success": 900, "received_at": 900}]
    manager.items = [{"provider": "frankfurter", "kind": "reference_fx_rate", "rate": 1.08}]
    manager.last_refresh = 900
    manager._save()
    restored = ExternalResearchManager(path, clock=lambda: 90_000, environ={})
    state = restored.snapshot()
    assert state["providers"][0]["fresh"] is False
    assert state["items"][0]["rate"] == 1.08


def test_non_object_external_cache_is_ignored_without_crashing(tmp_path):
    path = tmp_path / "external.json"
    path.write_text('[{"schema_version": 1}]', encoding="utf-8")

    manager = ExternalResearchManager(path, clock=lambda: 1000, environ={})

    assert manager.providers == []
    assert manager.items == []
    assert manager.last_refresh is None

