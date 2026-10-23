"""On-demand public research data connectors; never an execution-price source."""
from __future__ import annotations

import concurrent.futures
import json
import math
import os
import ssl
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

import certifi

MAX_RESPONSE_BYTES = 2_000_000
TIMEOUT_SECONDS = 8
USER_AGENT = "NEXUS-Research/0.7.5"


def _read_json(url: str, *, payload: dict | None = None, headers: dict | None = None,
               timeout: int = TIMEOUT_SECONDS) -> object:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    request = urllib.request.Request(url, data=body, headers=request_headers)
    context = _verified_tls_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            if response.status != 200:
                raise ValueError("http_status")
            if urllib.parse.urlsplit(response.url).scheme != "https":
                raise ValueError("insecure_redirect")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except FileNotFoundError as exc:
        raise FileNotFoundError("HTTPS_REQUEST_FILE_NOT_FOUND") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("response_too_large")
    return json.loads(raw.decode("utf-8"))


def _certificate_bundle() -> Path:
    """Resolve certifi's PEM from source or PyInstaller's onedir runtime."""
    candidates: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        candidates.append(Path(bundle_root) / "certifi" / "cacert.pem")
    executable_dir = Path(sys.executable).resolve().parent
    candidates.extend((executable_dir / "_internal" / "certifi" / "cacert.pem",
                      executable_dir / "certifi" / "cacert.pem"))
    try:
        candidates.append(Path(certifi.where()))
    except OSError:
        # In a frozen build, certifi may resolve its package resource as a
        # non-filesystem path. Continue to the explicit onedir data locations.
        pass
    for candidate in candidates:
        try:
            if candidate.is_file() and candidate.stat().st_size > 100_000:
                return candidate
        except OSError:
            # A resource-backed certifi path may disappear after its context closes.
            continue
    raise FileNotFoundError("Bundled HTTPS root CA bundle is unavailable")


def _verified_tls_context() -> ssl.SSLContext:
    # Loading the PEM contents avoids Windows/PyInstaller path virtualization
    # failures seen when OpenSSL reopens a CA file after certifi resolved it.
    bundle = _certificate_bundle()
    try:
        ca_pem = bundle.read_text(encoding="ascii")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"TLS_CA_READ_FAILED:{bundle}:{bundle.is_file()}") from exc
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_verify_locations(cadata=ca_pem)
    return context


class ExternalResearchManager:
    """Fetch independent context feeds on user request, with provenance/staleness."""

    def __init__(self, cache_path: str | Path, clock=time.time, environ=None):
        self.path = Path(cache_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        self.environ = os.environ if environ is None else environ
        self.lock = threading.RLock()
        self.refreshing = False
        self.providers: list[dict] = []
        self.items: list[dict] = []
        self.last_refresh: float | None = None
        self._load()

    def _load(self) -> None:
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if saved.get("schema_version") == 1:
                self.providers = saved.get("providers", [])
                self.items = saved.get("items", [])
                self.last_refresh = saved.get("last_refresh")
        except (OSError, ValueError, TypeError):
            pass

    def _save(self) -> None:
        payload = {"schema_version": 1, "last_refresh": self.last_refresh,
                   "providers": self.providers, "items": self.items}
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temp.replace(self.path)

    def refresh(self) -> dict:
        with self.lock:
            if self.refreshing:
                return {"ok": True, "started": False, "message": "التحديث جارٍ بالفعل"}
            self.refreshing = True
        threading.Thread(target=self._refresh_worker, name="external-research-apis", daemon=True).start()
        return {"ok": True, "started": True, "message": "بدأ جلب بيانات المصادر البحثية"}

    def _refresh_worker(self) -> None:
        fetchers = (self._massive, self._frankfurter, self._bls, self._world_bank)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda fn: fn(self.clock()), fetchers))
            with self.lock:
                self.providers = [provider for provider, _ in results]
                self.items = [item for _, items in results for item in items]
                self.last_refresh = self.clock()
                self._save()
        finally:
            with self.lock:
                self.refreshing = False

    @staticmethod
    def _provider(provider_id, name, url, received_at, status, reason, terms_url, coverage):
        return {"id": provider_id, "name": name, "url": url, "received_at": received_at,
                "last_success": received_at if status == "OK" else None,
                "status": status, "fresh": status == "OK", "reason": reason,
                "terms_url": terms_url, "coverage": coverage}

    @staticmethod
    def _error(provider_id, name, url, received_at, terms_url, coverage, exc):
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            reason = f"HTTP_{code}"
        elif isinstance(exc, FileNotFoundError):
            missing = getattr(exc, "filename", None)
            frames = traceback.extract_tb(exc.__traceback__)
            origin = f"{frames[-1].name}:{frames[-1].lineno}" if frames else "unknown"
            detail = Path(missing).name if isinstance(missing, str) else f"{origin}:{str(exc)[:80]}"
            reason = f"ملف مطلوب غير موجود ({detail})"
        else:
            reason = f"تعذر الجلب ({type(exc).__name__})"
        return ExternalResearchManager._provider(provider_id, name, url, received_at,
            "ERROR", reason, terms_url, coverage), []

    def _massive(self, now):
        key = str(self.environ.get("NEXUS_MASSIVE_API_KEY", "")).strip()
        base = "https://massive.com/docs/rest/forex/aggregates/custom-bars"
        if not key:
            return self._provider("massive_fx", "Massive · شموع الفوركس", base, now,
                "CONFIG_REQUIRED", "يلزم مفتاح Massive في NEXUS_MASSIVE_API_KEY؛ لم يُطلب أي مفتاح من الواجهة.",
                "https://massive.com/terms", "شموع Bid تاريخية لمقارنة المصدر؛ ليست أسعار تنفيذ الوسيط") , []
        end = datetime.fromtimestamp(now, UTC).date() - timedelta(days=1)
        start = end - timedelta(days=29)
        query = urllib.parse.urlencode({"adjusted": "true", "sort": "asc", "limit": 50000, "apiKey": key})
        request_url = (f"https://api.massive.com/v2/aggs/ticker/C:EURUSD/range/1/day/"
                       f"{start.isoformat()}/{end.isoformat()}?{query}")
        try:
            data = _read_json(request_url)
            if not isinstance(data, dict) or data.get("status") != "OK" or not isinstance(data.get("results"), list):
                raise ValueError("invalid_response")
            bars = []
            for row in data["results"]:
                if not isinstance(row, dict) or not all(isinstance(row.get(k), (int, float)) and math.isfinite(row[k]) for k in ("o", "h", "l", "c", "t")):
                    continue
                if row["l"] <= min(row["o"], row["c"]) <= max(row["o"], row["c"]) <= row["h"]:
                    bars.append({"time": row["t"], "open": row["o"], "high": row["h"],
                                 "low": row["l"], "close": row["c"],
                                 "quote_updates": row.get("n")})
            provider = self._provider("massive_fx", "Massive · شموع الفوركس",
                "https://massive.com/docs/rest/forex/aggregates/custom-bars", now, "OK",
                f"{len(bars)} شمعة يومية صالحة؛ بيانات المقارنة فقط.", "https://massive.com/terms",
                "شموع Bid؛ quote_updates عدد عروض الأسعار وليس حجم تداول")
            return provider, [{"provider": "massive_fx", "kind": "forex_daily_bars",
                "symbol": "EURUSD", "observed_at": now, "period_start": start.isoformat(),
                "period_end": end.isoformat(), "bars": bars}]
        except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            return self._error("massive_fx", "Massive · شموع الفوركس", base, now,
                "https://massive.com/terms", "شموع Bid تاريخية لمقارنة المصدر", exc)

    def _frankfurter(self, now):
        url = "https://api.frankfurter.dev/v2/providers/ecb/rate/eur/usd"
        try:
            data = _read_json(url)
            if not isinstance(data, dict):
                raise TypeError("invalid_response")
            rate, date = data.get("rate"), data.get("date")
            if not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0 or not isinstance(date, str):
                raise ValueError("invalid_fields")
            provider = self._provider("frankfurter", "Frankfurter · سعر مرجعي يومي", url,
                now, "OK", f"سعر مرجعي EUR/USD بتاريخ {date}؛ ليس Bid/Ask لحظياً.",
                "https://frankfurter.dev/", "سعر صرف يومي مرجعي للمقارنة فقط")
            return provider, [{"provider": "frankfurter", "kind": "reference_fx_rate",
                               "base": "EUR", "quote": "USD", "rate": rate,
                               "observation_date": date, "observed_at": now}]
        except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            return self._error("frankfurter", "Frankfurter · سعر مرجعي يومي", url, now,
                "https://frankfurter.dev/", "سعر يومي مرجعي", exc)

    def _bls(self, now):
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
        try:
            data = _read_json(url, payload={"seriesid": ["CUUR0000SA0"], "latest": True}, timeout=15)
            rows = data.get("Results", {}).get("series", [{}])[0].get("data", []) if isinstance(data, dict) else []
            if not rows:
                raise ValueError("empty_series")
            row = rows[0]
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError("invalid_value")
            provider = self._provider("bls_cpi", "BLS · مؤشر أسعار المستهلك", url,
                now, "OK", "آخر قراءة منشورة؛ قد تكون البيانات قد عُدلت لاحقاً.",
                "https://www.bls.gov/developers/", "بيانات تضخم أمريكية تاريخ نشرها ضمن استجابة BLS")
            return provider, [{"provider": "bls_cpi", "kind": "macro_observation",
                "series_id": "CUUR0000SA0", "name": "US CPI All Items, not seasonally adjusted",
                "value": value, "unit": "1982-84=100", "year": row.get("year"),
                "period": row.get("period"), "observed_at": now}]
        except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            return self._error("bls_cpi", "BLS · مؤشر أسعار المستهلك", url, now,
                "https://www.bls.gov/developers/", "بيانات تضخم أمريكية دورية", exc)

    def _world_bank(self, now):
        url = "https://api.worldbank.org/v2/country/USA/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=5&mrnev=5"
        try:
            data = _read_json(url)
            rows = data[1] if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list) else []
            row = next((item for item in rows if isinstance(item, dict) and item.get("value") is not None), None)
            if row is None or not isinstance(row.get("value"), (int, float)) or not math.isfinite(row["value"]):
                raise ValueError("empty_series")
            provider = self._provider("world_bank_gdp", "World Bank · نمو الناتج الأمريكي", url,
                now, "OK", "بيان سنوي متأخر؛ سياق اقتصادي طويل الأجل فقط.",
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation",
                "نمو الناتج المحلي السنوي؛ ليس مؤشر دخول لحظي")
            return provider, [{"provider": "world_bank_gdp", "kind": "macro_observation",
                "series_id": "NY.GDP.MKTP.KD.ZG", "name": "US GDP growth (annual %)",
                "value": row["value"], "observation_date": row.get("date"), "observed_at": now}]
        except (OSError, ValueError, TypeError, KeyError, IndexError, UnicodeError) as exc:
            return self._error("world_bank_gdp", "World Bank · نمو الناتج الأمريكي", url, now,
                "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation",
                "نمو الناتج السنوي", exc)

    def snapshot(self):
        with self.lock:
            now = self.clock()
            providers = []
            for provider in self.providers:
                age = now - (provider.get("last_success") or 0)
                providers.append({**provider, "fresh": provider.get("status") == "OK" and 0 <= age < 86400})
            return {"providers": providers, "items": self.items,
                    "last_refresh": self.last_refresh, "refreshing": self.refreshing,
                    "execution_use": "NONE; broker MT5 remains the only quote/order authority"}
