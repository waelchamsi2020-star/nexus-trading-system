"""Official MT5 adapter. No research module may call send()."""
from __future__ import annotations

import copy
import json
import logging
import math
import os
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from .store import account_key
from .timeframes import PERIODS as TIMEFRAMES
from .timeframes import bar_close_time, month_start

# MQL5 SYMBOL_FILLING_* values are symbol-property BIT MASKS. The pinned
# official Python module exposes ORDER_FILLING_* request enums, not these masks.
SYMBOL_FILL_MASK_FOK = 1
SYMBOL_FILL_MASK_IOC = 2
SYMBOL_FILL_MASK_BOC = 4


class BrokerError(RuntimeError):
    pass


def plain(value):
    if hasattr(value, "_asdict"):
        return {k: plain(v) for k, v in value._asdict().items()}
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(x) for x in value]
    if hasattr(value, "item"):
        return value.item()
    return value


class MT5Broker:
    is_simulation = False

    def __init__(self, terminal_path="", bridge_path=""):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise BrokerError("مكتبة MT5 غير مثبتة. استخدم حزمة Windows أو الإعداد المرفق.") from exc
        self.mt5 = mt5
        self.lock = threading.RLock()
        self._initialize_args = [terminal_path] if terminal_path else []
        self._bridge_override = str(bridge_path or "")
        if not mt5.initialize(*self._initialize_args, timeout=10000):
            raise BrokerError(f"تعذر الاتصال بـMT5: {mt5.last_error()}")
        terminal = self.terminal()
        self.platform_id = os.path.normcase(os.path.abspath(terminal.get("path", terminal_path)))
        self.bridge_path = Path(bridge_path) if bridge_path else Path(terminal["data_path"]) / "MQL5" / "Files" / "NEXUS_bridge.json"
        self.account()  # Never substitute synthetic data if MT5 connection fails.

    def reconnect(self):
        """Rebind the process-global MT5 IPC channel after terminal restart.

        Reconnection never authorizes trading.  The coordinator replaces the
        executor after this succeeds, leaving the recovered session READ_ONLY
        until the user explicitly activates the Demo account again.
        """
        with self.lock:
            try:
                self.mt5.shutdown()
            except Exception:
                logging.getLogger(__name__).exception("Handled boundary failure")
            if not self.mt5.initialize(*self._initialize_args, timeout=10000):
                raise BrokerError(f"تعذر إعادة الاتصال بـMT5: {self.mt5.last_error()}")
            terminal = self.terminal()
            if not terminal.get("connected"):
                raise BrokerError("أعيد فتح قناة MT5 لكن المنصة غير متصلة بالخادم")
            self.platform_id = os.path.normcase(os.path.abspath(terminal.get("path", self._initialize_args[0] if self._initialize_args else "")))
            self.bridge_path = Path(self._bridge_override) if self._bridge_override else Path(terminal["data_path"]) / "MQL5" / "Files" / "NEXUS_bridge.json"
            self.account()
            return terminal

    def _call(self, name, *args, **kwargs):
        with self.lock:
            result = getattr(self.mt5, name)(*args, **kwargs)
            if result is None:
                raise BrokerError(f"{name}: {self.mt5.last_error()}")
            return plain(result)

    def account(self):
        a = self._call("account_info")
        a["platform_id"] = getattr(self, "platform_id", "")
        return a

    def terminal(self):
        return self._call("terminal_info")

    def symbols(self):
        # Intentionally NO group filter and NO Market Watch filter.
        return self._call("symbols_get")

    def symbol(self, name):
        return self._call("symbol_info", name)

    def select(self, name):
        if not self._call("symbol_select", name, True):
            raise BrokerError(f"تعذر إتاحة بيانات {name} في Market Watch")
        return True

    def tick(self, name):
        return self._call("symbol_info_tick", name)

    def bars(self, name, timeframe, count):
        if timeframe not in TIMEFRAMES:
            raise BrokerError("فريم غير معتمد")
        with self.lock:
            rates = self.mt5.copy_rates_from_pos(name, getattr(self.mt5, "TIMEFRAME_" + timeframe), 1, count)
            if rates is None:
                raise BrokerError(f"التاريخ غير متاح: {name}: {self.mt5.last_error()}")
            now = time.time()
            return [{k: plain(row[k]) for k in rates.dtype.names} for row in rates
                    if bar_close_time(float(row["time"]),timeframe) <= now]

    def positions(self):
        return self._call("positions_get")

    def orders(self):
        return self._call("orders_get")

    def deals(self, since):
        return self._call("history_deals_get", datetime.fromtimestamp(since, UTC), datetime.now(UTC))

    def history_orders(self, since):
        return self._call("history_orders_get", datetime.fromtimestamp(since, UTC), datetime.now(UTC))

    def _side(self, side):
        if side not in ("BUY", "SELL"):
            raise BrokerError("اتجاه غير صالح")
        return self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL

    def calc_profit(self, side, name, volume, open_price, close_price):
        return self._call("order_calc_profit", self._side(side), name, volume, open_price, close_price)

    def calc_margin(self, side, name, volume, price):
        return self._call("order_calc_margin", self._side(side), name, volume, price)

    def _request(self, request):
        m = self.mt5
        action = request["action"]
        actions = {"DEAL": m.TRADE_ACTION_DEAL, "REMOVE": m.TRADE_ACTION_REMOVE, "SLTP": m.TRADE_ACTION_SLTP}
        if action not in actions:
            raise BrokerError("نوع طلب غير معتمد")
        raw = {k: v for k, v in request.items() if k in {"symbol", "volume", "price", "sl", "tp", "magic", "comment", "position", "order", "deviation"}}
        raw["action"] = actions[action]
        if action == "DEAL":
            raw["type"] = self._side(request["side"])
            info = self.symbol(request["symbol"])
            modes = info.get("filling_mode", 0)
            execution_mode = info.get("trade_exemode")
            if type(modes) is not int or modes < 0 or modes & ~(SYMBOL_FILL_MASK_FOK | SYMBOL_FILL_MASK_IOC | SYMBOL_FILL_MASK_BOC):
                raise BrokerError("سياسة تعبئة الرمز غير معروفة")
            if execution_mode not in (m.SYMBOL_TRADE_EXECUTION_REQUEST, m.SYMBOL_TRADE_EXECUTION_INSTANT,
                                       m.SYMBOL_TRADE_EXECUTION_MARKET, m.SYMBOL_TRADE_EXECUTION_EXCHANGE):
                raise BrokerError("نمط تنفيذ الرمز غير معروف")
            # FOK/IOC are symbol bit flags; ORDER_FILLING enum has different values.
            if modes & SYMBOL_FILL_MASK_FOK:
                raw["type_filling"] = m.ORDER_FILLING_FOK
            elif modes & SYMBOL_FILL_MASK_IOC:
                raw["type_filling"] = m.ORDER_FILLING_IOC
            elif execution_mode != m.SYMBOL_TRADE_EXECUTION_MARKET:
                raw["type_filling"] = m.ORDER_FILLING_RETURN
            else:
                raise BrokerError("لا توجد سياسة تعبئة مؤكدة لهذا العقد")
            raw["type_time"] = m.ORDER_TIME_GTC
        return raw

    def check(self, request):
        # Pinned SDK 5.0.6231 accepts request fields as named arguments. A
        # positional dictionary errors; request=... silently produces an empty
        # native request. This form was verified with a real read-only check.
        return self._call("order_check", **self._request(request))

    def send(self, request):
        # Defense in depth, including close/modify/cancel actions. Never accept Contest.
        with self.lock:
            account = self.account()
            terminal = self.terminal()
            if type(account.get("trade_mode")) is not int or account.get("trade_mode") != self.mt5.ACCOUNT_TRADE_MODE_DEMO:
                raise BrokerError("حظر دائم: إرسال الأوامر مسموح لحساب Demo فقط")
            if request.get("_authorized_account_key") != account_key(account):
                raise BrokerError("الحساب أو المنصة يختلف عن التفويض؛ أعد التفعيل")
            if not terminal.get("connected") or not terminal.get("trade_allowed") or terminal.get("tradeapi_disabled") or not account.get("trade_allowed"):
                raise BrokerError("التنفيذ غير متاح أو الاتصال منقطع")
            return self._call("order_send", **self._request(request))

    def _bridge(self):
        try:
            if self.bridge_path.stat().st_size > 16_000_000:
                raise ValueError("bridge size")
            data = json.loads(self.bridge_path.read_text(encoding="utf-8-sig"))
            account = self.account()
            if str(data.get("login")) != str(account["login"]) or data.get("server") != account["server"]:
                raise ValueError("الجسر صادر من حساب مختلف")
            if os.path.normcase(os.path.abspath(data.get("terminal_path", ""))) != self.platform_id:
                raise ValueError("الجسر صادر من منصة مختلفة")
            age = time.time() - float(data["as_of"])
            if age < -5 or age > 120 or not data.get("connected"):
                raise ValueError("بيانات الجسر قديمة أو غير متصلة")
            if data.get("schema") != 1 or not data.get("clock_ok"):
                raise ValueError("إصدار الجسر أو توقيت الخادم غير مؤكد")
            if abs(float(data["server_offset_seconds"])) > 50400:
                raise ValueError("توقيت الخادم غير صالح")
            return data
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise BrokerError(f"الجسر غير صالح: {exc}") from exc

    def session(self, name):
        try:
            data = self._bridge()
            row = data.get("sessions", {}).get(name)
            if row is None:
                raise BrokerError("لم يُصدّر الجسر جلسة هذا الرمز")
            return {**row, "as_of": data["as_of"], "server_offset_seconds": data["server_offset_seconds"]}
        except BrokerError as exc:
            return {"known": False, "open": False, "as_of": 0, "reason": str(exc)}

    def calendar(self):
        try:
            return self._bridge()["calendar"]
        except (BrokerError, KeyError) as exc:
            return {"ok": False, "as_of": 0, "events": [], "reason": str(exc)}

    def close(self):
        with self.lock:
            self.mt5.shutdown()


class SimBroker:
    """Explicit industrial fixture. Prices and fills are synthetic, not market data."""
    is_simulation = True

    def __init__(self, clock=time.time):
        self.clock = clock
        self.lock = threading.RLock()
        self.connected = True
        self._account = {"login": 900001, "server": "NEXUS-SYNTHETIC", "trade_mode": 0, "margin_mode": 2,
                             "balance": 10000., "equity": 10000., "currency": "USD", "margin_free": 10000.,
                             "trade_allowed": True, "platform_id": "NEXUS-SIMULATOR", "trade_expert": True}
        specs = [("EURUSD.demo", "Forex", "EUR", "USD", 1.08, .00001, 100000, 0),
                 ("GOLD#", "Metals", "XAU", "USD", 2450., .01, 100, 1),
                 ("US500.cash", "Indices", "", "USD", 5200., .1, 1, 3),
                 ("OIL-FUT", "Energy/Futures", "", "USD", 73., .01, 1000, 2),
                 ("STOCK.A", "Stocks", "", "USD", 210., .01, 1, 4),
                 ("CLOSED.asset", "Stocks", "", "USD", 50., .01, 1, 4)]
        self._symbols = {}
        self._prices = {}
        for name, path, base, profit, price, point, contract, calc in specs:
            self._symbols[name] = {"name": name, "path": path, "description": "عقد صناعي للاختبارات", "currency_base": base,
                "currency_profit": profit, "currency_margin": profit, "trade_calc_mode": calc, "trade_contract_size": contract,
                "trade_mode": 4, "point": point, "trade_tick_size": point, "trade_tick_value": point*contract,
                "volume_min": .01, "volume_max": 100., "volume_step": .01, "volume_limit": 100., "trade_stops_level": 10,
                "trade_freeze_level": 0, "trade_exemode": 2, "filling_mode": 3, "order_mode": 127,
                "expiration_time": 0, "start_time": 0, "visible": False, "custom": False, "digits": 5 if point < .01 else 2}
            self._prices[name] = price
        self._positions, self._orders, self._deals, self._history = [], [], [], []
        self.sent = []
        self.next_result = None
        self._ticket = 1000

    def account(self):
        with self.lock:
            floating = sum(p["profit"] + p.get("swap", 0) for p in self.positions())
            self._account["equity"] = self._account["balance"] + floating
            self._account["margin_free"] = self._account["equity"]
            return copy.deepcopy(self._account)

    def terminal(self):
        return {"connected": self.connected, "trade_allowed": True, "tradeapi_disabled": False, "path": "SYNTHETIC", "data_path": ""}

    def symbols(self):
        return copy.deepcopy(list(self._symbols.values()))

    def symbol(self, name):
        try:
            return copy.deepcopy(self._symbols[name])
        except KeyError as exc:
            raise BrokerError("رمز غير معروف") from exc

    def select(self, name):
        self._symbols[name]["visible"] = True
        return True

    def tick(self, name):
        if not self.connected:
            raise BrokerError("انقطاع صناعي")
        p = self._prices[name]
        point = self._symbols[name]["point"]
        return {"time": self.clock(), "time_msc": int(self.clock()*1000), "bid": p, "ask": p+point, "last": p}

    def bars(self, name, timeframe, count):
        sec = TIMEFRAMES[timeframe]
        end = month_start(self.clock()) if timeframe=="MN1" else int(self.clock()//sec)*sec
        point = self.symbol(name)["point"]
        base = self._prices[name]
        scale = max(base*.001, point*30)
        rows = []
        # Fixed series tied to bar epoch, not the requested count: prefixes agree.
        for i in range(count):
            epoch = month_start(end,i-count) if timeframe=="MN1" else end-(count-i)*sec
            k = epoch//sec
            opening = base + scale*(math.sin(k*.07) + .35*math.sin(k*.23))
            close = base + scale*(math.sin((k+1)*.07) + .35*math.sin((k+1)*.23))
            rows.append({"time": epoch, "open": opening, "high": max(opening,close)+scale*.15,
                "low": min(opening,close)-scale*.15, "close": close, "tick_volume": 100+int(abs(math.sin(k))*90), "real_volume": 0, "spread": 1})
        return rows

    def positions(self):
        with self.lock:
            for p in self._positions:
                p["price_current"] = self.tick(p["symbol"])["bid" if p["type"] == 0 else "ask"]
                p["profit"] = self.calc_profit("BUY" if p["type"]==0 else "SELL", p["symbol"], p["volume"], p["price_open"], p["price_current"])
            return copy.deepcopy(self._positions)

    def orders(self):
        return copy.deepcopy(self._orders)

    def deals(self, since):
        return copy.deepcopy([d for d in self._deals if d["time"] >= since])

    def history_orders(self, since):
        return copy.deepcopy([d for d in self._history if d["time_done"] >= since])

    def calc_profit(self, side, name, volume, open_price, close_price):
        return (close_price-open_price)*self.symbol(name)["trade_contract_size"]*volume*(1 if side=="BUY" else -1)

    def calc_margin(self, side, name, volume, price):
        return price*self.symbol(name)["trade_contract_size"]*volume/100

    def session(self, name):
        return {"known": True, "open": not name.startswith("CLOSED"), "as_of": self.clock(), "server_offset_seconds": 0,
                    "reason": "جلسة صناعية للاختبار", "sessions": [{"from":0,"to":86400}]}

    def calendar(self):
        return {"ok": True, "known": True, "coverage_known": True, "as_of": self.clock(), "from_utc": self.clock()-86400, "to_utc": self.clock()+172800,
                    "events": [], "currencies": ["USD", "EUR", "GBP", "JPY"], "provider": "SYNTHETIC"}

    def check(self, request):
        return {"retcode": 0, "comment": "فحص صناعي فقط"}

    def send(self, request):
        with self.lock:
            if type(self._account.get("trade_mode")) is not int or self._account.get("trade_mode") != 0 or not self.connected:
                raise BrokerError("رفض بيئة الاختبار غير المسموحة")
            if request.get("_authorized_account_key") != account_key(self.account()):
                raise BrokerError("تفويض المحاكاة لا يطابق الحساب")
            self.sent.append(copy.deepcopy(request))
            if self.next_result == "disconnect_before":
                self.next_result=None; self.connected=False
                raise BrokerError("انقطاع قبل القبول، النتيجة يجب أن تبقى غير محسومة")
            if request["action"] == "REMOVE":
                self._orders = [o for o in self._orders if o["ticket"] != request["order"]]
                return {"retcode": 10009, "order": request["order"], "deal": 0, "volume": 0}
            if request["action"] == "SLTP":
                for p in self._positions:
                    if p["ticket"] == request["position"]:
                        p["sl"],p["tp"] = request["sl"],request.get("tp",p["tp"])
                return {"retcode": 10009, "order": 0, "deal": 0, "volume": 0}
            self._ticket+=1
            ticket = self._ticket
            partial = self.next_result == "partial"
            step=self.symbol(request["symbol"])["volume_step"]
            # A broker partial fill must be on the symbol's lot grid.
            volume=round(math.floor((request["volume"]*.5+1e-10)/step)*step,10) if partial else request["volume"]
            if volume<self.symbol(request["symbol"])["volume_min"]:
                volume=request["volume"];partial=False
            closing = bool(request.get("position"))
            profit = 0.
            identifier = ticket
            if closing:
                found = next((p for p in self._positions if p["ticket"] == request["position"]), None)
                if not found:
                    return {"retcode": 10036, "comment": "المركز مغلق"}
                identifier = found["identifier"]
                volume = min(volume, found["volume"])
                profit=self.calc_profit("BUY" if found["type"]==0 else "SELL",found["symbol"],volume,found["price_open"],request["price"])
                found["volume"]-=volume
                self._positions=[p for p in self._positions if p["volume"]>1e-9]
                self._account["balance"]+=profit
            else:
                self._positions.append({"ticket": ticket,"identifier": ticket,"symbol": request["symbol"],"type": 0 if request["side"]=="BUY" else 1,
                    "volume": volume,"price_open": request["price"],"price_current": request["price"],"sl": request["sl"],"tp": request.get("tp",0),
                    "profit": 0.,"swap": 0.,"magic": request["magic"],"comment": request["comment"],"time": self.clock()})
            deal = {"ticket": ticket,"order": ticket,"position_id": identifier,"time": self.clock(),"time_msc": int(self.clock()*1000),
                        "symbol": request["symbol"],"type": 0 if request["side"]=="BUY" else 1,"entry": 1 if closing else 0,
                        "volume": volume,"price": request["price"],"profit": profit,"commission": 0.,"swap": 0.,"fee": 0.,"magic": request["magic"],"comment": request["comment"]}
            self._deals.append(deal)
            self._history.append({"ticket": ticket,"position_id": identifier,"symbol": request["symbol"],"magic": request["magic"],
                "comment": request["comment"],"state": 4,"volume_initial": request["volume"],"volume_current": 0.,"time_setup": self.clock(),"time_done": self.clock()})
            result = {"retcode": 10010 if partial else 10009,"order": ticket,"deal": ticket,"volume": volume,"price": request["price"]}
            lost = self.next_result == "lost_response"
            self.next_result = None
            if lost:
                raise BrokerError("رد صناعي مفقود بعد تنفيذ الصفقة")
            return result

    def close(self):
        pass
