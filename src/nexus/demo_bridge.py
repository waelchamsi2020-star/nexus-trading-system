"""One desktop UI backed by the existing, sole Demo sender."""
import json
import sqlite3

from tools.demo_control import Controls


class DemoBridge:
    def __init__(self, engine, directory):
        self.engine = engine
        self.controls = Controls(directory)

    def snapshot(self):
        view = self.engine.snapshot()
        try:
            demo = self.controls.snapshot()
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            demo = {"error": str(exc), "running": False, "fresh": False,
                    "status": {}, "identity": {}, "limits": None}
        if demo.get("error") or not demo.get("running"):
            return self._read_only_fallback(view, demo)

        # Once the sender is current, its journal is authoritative. Never mix
        # broker-reader P&L or orders with the single Demo sender's records.
        view.update(account={}, positions=[], orders=[], risk={},
                    performance={'rows': []}, execution={
                        'mode': 'READ_ONLY', 'entries_paused': True,
                        'reason': 'حالة منفّذ Demo غير متاحة'},
                    mode='READ_ONLY', status='DATA_ERROR', error=None, last_update=None)
        s = demo["status"]
        paused = demo["user_paused"] or s.get("daily_halt") or s.get("target_halt")
        view["demo_live"] = demo
        view['performance'] = demo.get('performance') or {'rows': []}
        view["mode"] = "AUTO_DEMO" if not paused else "READ_ONLY"
        view["status"] = "CONNECTED" if not paused else "READ_ONLY"
        view["last_update"] = demo['status_timestamp']
        if "positions" in s:
            view["positions"] = [{**p, "owned": p.get("magic") == 20261019,
                                  "side": {0: "BUY", 1: "SELL"}.get(p.get("type"), "UNKNOWN")}
                                 for p in s["positions"]]
        reason = ('متوقف بطلبك' if demo['user_paused'] else
                  'بلغ حد الخسارة' if s.get('daily_halt') else
                  'بلغ هدف اليوم' if s.get('target_halt') else 'المنفّذ التجريبي')
        view["execution"] = {"mode": view["mode"], "entries_paused": bool(paused),
                             "reason": reason}
        view["account"] = {"login": s["account"], "trade_mode": 0,
                           "type": "DEMO", "currency": "USD",
                           "balance": s.get("balance"), "equity": s.get("equity"),
                           "server": demo['identity'].get('server')}
        view["risk"] = {"daily_risk": s.get("daily_loss_limit"),
                        "risk_limit": s.get("daily_loss_limit"),
                        "remaining": (max(0, s['daily_loss_limit'] - s['daily_loss'] - s['exposure'])
                                      if all(s.get(k) is not None for k in
                                             ('daily_loss_limit', 'daily_loss', 'exposure')) else None),
                        "used": (s['daily_loss'] + s['exposure'] if all(s.get(k) is not None
                                  for k in ('daily_loss', 'exposure')) else None),
                        "floating_pnl": s.get("floating_pnl"), "net_target": s.get("daily_profit"),
                        "target": s.get("daily_profit_target"), "reserved": s.get("exposure")}
        return view

    @staticmethod
    def _read_only_fallback(view, demo):
        """Keep live, identity-matched Demo market/account visibility when sender is stopped."""
        account = view.get("account") or {}
        terminal = view.get("terminal") or {}
        expected = (demo.get("identity") or {}).get("login")
        actual = account.get("login")
        same_login = type(expected) is int and type(actual) is int and expected == actual
        same_server = (not (demo.get("identity") or {}).get("server") or
                       str(account.get("server", "")).casefold() ==
                       str(demo["identity"]["server"]).casefold())
        verified = (same_login and same_server and account.get("trade_mode") == 0 and
                    terminal.get("connected") is True)
        reason = demo.get("stop_reason") or demo.get("error") or "EXECUTOR_NOT_RUNNING"
        stale = demo.get("fresh") is not True
        if stale:
            reason = f"{reason}؛ آخر حالة للمنفذ قديمة، وليست دليلاً على أنه يعمل الآن"
        view["demo_live"] = {**demo, "running": False, "read_only_fallback": True}
        view["mode"] = "READ_ONLY"
        view["execution"] = {"mode": "READ_ONLY", "entries_paused": True,
                              "reason": "منفذ Demo غير نشط؛ العرض قراءة فقط. " + str(reason)}
        view["status"] = "READ_ONLY" if verified else "DATA_ERROR"
        view["error"] = None if verified else "تعذر إثبات هوية حساب Demo المتصل؛ التنفيذ متوقف"
        view["risk"] = {}
        view["performance"] = {"rows": [], "source": "UNAVAILABLE_WHILE_DEMO_SENDER_STOPPED"}
        if verified:
            view["positions"] = [{**p, "owned": p.get("magic") == 20261019,
                                  "side": {0: "BUY", 1: "SELL"}.get(p.get("type"), "UNKNOWN")}
                                 for p in view.get("positions", [])]
            view["orders"] = [{**p, "owned": p.get("magic") == 20261019}
                              for p in view.get("orders", [])]
        else:
            view["account"] = {}
            view["positions"] = []
            view["orders"] = []
        return view

    def snapshot_json(self):
        return json.dumps(self.snapshot(), ensure_ascii=False, allow_nan=False).encode("utf-8")

    def action(self, payload):
        action = payload.get("action")
        if action == "demo_limits":
            return self.controls.action({**payload, "action": "limits"})
        if action in ("demo_pause", "demo_resume"):
            return self.controls.action({"action": action.removeprefix("demo_")})
        if action == "stop":
            return self.controls.action({"action": "pause"})
        if action in ("start", "approve", "cancel", "flatten", "simulation"):
            raise ValueError("التنفيذ موحّد؛ استخدم أزرار وحدود التداول في الصفحة الرئيسية")
        return self.engine.action(payload)

    def action_result(self, request_id):
        return self.engine.action_result(request_id)
