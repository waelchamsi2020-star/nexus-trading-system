"""Exercise optional research feeds from the frozen app in an isolated READ_ONLY profile."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
import urllib.error
from pathlib import Path

from smoke_service import request, session


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", default=str(root / "Windows" / "Quant Trading AI" / "Quant Trading AI.exe"))
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--output", default=str(root / "reports" / "packaged-external-apis.json"))
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    report: dict[str, object] = {"read_only": True, "orders_sent": 0}
    with tempfile.TemporaryDirectory(prefix="nexus-external-api-smoke-") as temporary:
        data_dir = Path(args.data_dir) if args.data_dir else Path(temporary) / "app-data"
        child = subprocess.Popen([args.exe, "--headless", "--no-connect", "--port", str(args.port), "--data-dir", str(data_dir)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        token = None
        try:
            for _ in range(60):
                if child.poll() is not None:
                    raise RuntimeError(f"Frozen app exited during startup ({child.returncode})")
                try:
                    token = session(url)
                    break
                except (OSError, AttributeError, urllib.error.URLError):
                    time.sleep(0.25)
            if token is None:
                raise RuntimeError("Frozen app did not expose its local service")
            initial = request(url, token)
            if initial.get("mode") != "READ_ONLY" or initial.get("account") is not None:
                raise RuntimeError("External API smoke must start disconnected and READ_ONLY")
            request(url, token, {"action": "refresh_external_research"})
            deadline = time.monotonic() + 90
            latest = initial
            while time.monotonic() < deadline:
                latest = request(url, token)
                research = latest.get("news", {}).get("external_research", {})
                if research.get("last_refresh") is not None and not research.get("refreshing"):
                    break
                time.sleep(0.5)
            research = latest.get("news", {}).get("external_research", {})
            if research.get("last_refresh") is None or research.get("refreshing"):
                raise RuntimeError("Research refresh did not complete within 90 seconds")
            providers = research.get("providers", [])
            if len(providers) != 4:
                raise RuntimeError(f"Expected four provider results, received {len(providers)}")
            report["providers"] = [{"id": item.get("id"), "status": item.get("status"),
                                    "reason": item.get("reason")} for item in providers]
            report["read_only"] = latest.get("mode") == "READ_ONLY"
            report["orders_sent"] = 0
            if not report["read_only"] or latest.get("intents"):
                raise RuntimeError("Research connector altered execution state")
            report["passed"] = not any(
                "FileNotFoundError" in str(item.get("reason"))
                or "ملف مطلوب غير موجود" in str(item.get("reason"))
                for item in providers
            )
            if not report["passed"]:
                raise RuntimeError("Frozen app cannot find its HTTPS certificate bundle")
        except Exception as exc:
            report["passed"] = False
            report["error"] = str(exc)
            raise
        finally:
            if child.poll() is None:
                try:
                    if token:
                        request(url, token, {"action": "shutdown"})
                    child.wait(timeout=15)
                except (OSError, RuntimeError, subprocess.TimeoutExpired, urllib.error.URLError):
                    child.terminate()
                    child.wait(timeout=5)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
