"""The single guarded sender and broker-confirmed trade lifecycle.

An ambiguous result is never retried. Restart, disconnection, account change,
day change or changed settings revoke the in-memory trading authorization.
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from contextlib import nullcontext
from decimal import ROUND_FLOOR, Decimal

from . import regime_router
from .broker import TIMEFRAMES
from .risk import (
    FOUR_SCHOOL_PROTOCOL,
    calendar_event_veto,
    cashflow_records,
    comment_for,
    number,
    record_matches,
)
from .risk import MAGIC as MAGIC  # noqa: PLC0414 -- Explicit public re-export or deterministic side-effect model registration; removing it breaks compatibility.
from .store import ACTIVE_STATES, account_key, blocks_send, utc_day
from .timeframes import bar_close_time

SUCCESS_CODES = {10008: "ACCEPTED", 10009: "FILLED", 10010: "PARTIAL"}
UNKNOWN_CODES = {10011, 10012, 10023, 10028, 10031, 10039}
# Explicit MT5 rejection enums. Never infer rejection from a numeric interval:
# 10037 is not defined. Changed/locked/existing-close states need reconciliation.
# 10046 HEDGE_PROHIBITED is documented by MetaQuotes although the pinned Python
# header does not expose its constant yet.
KNOWN_REJECTION_CODES = {
    10004, 10006, 10007, 10013, 10014, 10015, 10016, 10017, 10018,
    10019, 10020, 10021, 10022, 10024, 10025, 10026, 10027, 10029,
    10030, 10032, 10033, 10034, 10035, 10036, 10038, 10040, 10041,
    10042, 10043, 10044, 10045, 10046,
}
TERMINAL_ORDER_STATES = {2, 4, 5, 6}
SETTLEMENT_GRACE_SECONDS = 6.
SETTLEMENT_POLL_SECONDS = .25
SETTLEMENT_MAX_READS = 25


class Executor:
    def __init__(self, broker, store, risk, clock=time.time, *, settlement_clock=time.monotonic, settlement_sleep=time.sleep,
                 regime_routing_enabled=False, routing_config_path=None):
        if type(regime_routing_enabled) is not bool:
            raise ValueError("Regime routing opt-in must be boolean")
        self.broker, self.store, self.risk, self.clock = broker, store, risk, clock
        # Research-candidate opt-in only. Neither a route nor its configuration
        # grants send authority; every existing Demo/risk guard still applies.
        self.regime_routing_enabled = regime_routing_enabled
        self.routing_config_path = routing_config_path
        self._authorized_routing_fingerprint = None
        self.lock = threading.RLock()
        self.mode, self.entries_paused = "READ_ONLY", True
        self.authorization = None
        self.last_reason = "Explicit Demo activation is required"
        self._settlement_clock,self._settlement_sleep=settlement_clock,settlement_sleep
        # PREPARED was durably recorded before the send claim. It is provably
        # unsent. SENDING may have reached the broker, even if the app crashed.
        for intent in self.store.intents():
            if intent["state"] == "PREPARED":
                self.store.set_intent_state(intent["id"], "REJECTED", reason="Restart before send claim")
            elif intent["state"] == "SENDING":
                self.store.set_intent_state(intent["id"], "UNKNOWN", reason="Restart during send")

    def _settings_digest(self):
        policy = {"risk_settings": self.risk.settings, "regime_routing_enabled": self.regime_routing_enabled,
                  "routing_config_path": str(self.routing_config_path) if self.routing_config_path is not None else None}
        return hashlib.sha256(json.dumps(policy, sort_keys=True, allow_nan=False).encode()).hexdigest()

    def _regime_entry_check(self, proposal, *, phase, prior=None):
        """Fresh causal filter before reservation and immediately before send.

        Missing/changed context fails closed when explicitly opted in. The
        receipt is attached to the intent, so post-read changes cannot silently
        replace the closed-bar evidence accepted before reservation. A failed
        audit insert itself also prevents reservation/send.
        """
        if not self.regime_routing_enabled:
            return None
        evidence = {"account_key": self.risk.key, "phase": phase,
                    "model_id": proposal.get("strategy_id"), "regime": "UNCERTAIN",
                    "symbol": proposal.get("symbol"), "timeframe": proposal.get("timeframe"),
                    "signal_id": proposal.get("id"), "data_time": proposal.get("data_time"),
                    "rule_version": None, "routing_fingerprint": None, "snapshot_sha256": None}
        try:
            config = regime_router.load_routing_config(self.routing_config_path)
            evidence.update(rule_version=config["version"], routing_fingerprint=config["routing_fingerprint"])
            if config["routing_fingerprint"] != self._authorized_routing_fingerprint:
                raise ValueError("Authorized regime routing configuration changed")
            if phase == "BEFORE_SEND" and not isinstance(prior, dict):
                raise ValueError("Prepared entry has no regime routing receipt")
            timeframe = proposal.get("timeframe")
            if timeframe not in TIMEFRAMES:
                raise ValueError("Regime routing requires an explicit supported timeframe")
            now = self.clock()
            signal_time = number(proposal.get("data_time"), "regime signal time")
            if not signal_time <= now < number(proposal.get("expires_at"), "regime signal expiry"):
                raise ValueError("Regime signal is future or expired")
            if now - signal_time >= TIMEFRAMES[timeframe]:
                raise ValueError("Regime signal data is stale")
            count = max(300, config["classifier"]["min_bars"])
            bars = self.broker.bars(proposal["symbol"], timeframe, count)
            evidence["snapshot_sha256"] = hashlib.sha256(
                json.dumps(bars, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()
            result = regime_router.route_signal(proposal.get("strategy_id"), bars, timeframe, signal_time, config=config)
            evidence.update({key: result.get(key) for key in (
                "regime", "rule_version", "routing_fingerprint", "last_closed_time", "metrics")})
            if not result["allowed"]:
                raise ValueError("; ".join(result["reasons"]))
            if result["last_closed_time"] != signal_time:
                raise ValueError("Regime input does not match the proposal closed-bar time")
            if prior is not None and any(prior.get(key) != evidence.get(key) for key in (
                    "model_id", "symbol", "timeframe", "data_time", "routing_fingerprint", "snapshot_sha256")):
                raise ValueError("Closed regime input snapshot changed before send")
        except Exception as exc:
            evidence.update(allowed=False, reasons=[str(exc)])
            self.store.audit("REGIME_ROUTING_REJECTED", evidence)
            raise ValueError("Regime routing refused: " + str(exc)) from exc
        return {**evidence, "allowed": True, "reasons": []}

    def _connection(self):
        account, terminal = self.broker.account(), self.broker.terminal()
        key = account_key(account)
        if type(account.get("trade_mode")) is not int or account.get("trade_mode") != 0:
            raise ValueError("Permanent Demo-only guard: Real, Contest and unknown accounts are refused")
        if account.get("margin_mode") not in (0, 2):
            raise ValueError("Unknown hedging/netting accounting mode")
        if not terminal.get("connected") or not terminal.get("trade_allowed") or terminal.get("tradeapi_disabled") is not False:
            raise ValueError("Terminal disconnected or trading/API disabled")
        if not account.get("trade_allowed") or account.get("trade_expert") is False:
            raise ValueError("Account trading/expert permission disabled")
        return account, key

    def _unresolved(self, key, exclude=None):
        return [i for i in self.store.intents(key) if i["id"] != exclude and blocks_send(i)]

    def _guard(self, entry=False, exclude=None):
        if self.mode not in ("MANUAL_DEMO", "AUTO_DEMO") or self.authorization is None:
            raise ValueError("READ_ONLY: explicit Demo activation is required")
        try:
            account, key = self._connection()
            if key != self.authorization["account_key"]:
                raise ValueError("Account, server or terminal changed")
            if utc_day(self.clock()) != self.authorization["day"]:
                raise ValueError("UTC day changed; explicit activation is required")
            if self._settings_digest() != self.authorization["settings_digest"]:
                raise ValueError("Authorized risk settings changed")
        except Exception as exc:
            self.deactivate(str(exc))
            raise
        if self._unresolved(key, exclude):
            raise ValueError("Unresolved broker result blocks every send")
        if entry and (self.entries_paused or self.store.day_halt(key, self.clock())):
            raise ValueError("New entries are stopped")
        return account, key

    def activate(self, mode, settings):
        with self.lock:
            if mode not in ("MANUAL_DEMO", "AUTO_DEMO"):
                raise ValueError("Activation mode must be MANUAL_DEMO or AUTO_DEMO")
            self.deactivate("Activation requested")
            _account, key = self._connection()
            self._authorized_routing_fingerprint = None
            if self.regime_routing_enabled:
                try:
                    routing = regime_router.load_routing_config(self.routing_config_path)
                    self._authorized_routing_fingerprint = routing["routing_fingerprint"]
                except Exception as exc:
                    self.store.audit("REGIME_ROUTING_REJECTED", {"account_key": key, "phase": "ACTIVATION",
                                     "regime": "UNCERTAIN", "reasons": [str(exc)], "allowed": False})
                    raise
            reconciliation = self.reconcile(key)
            if not reconciliation["ok"] or self._unresolved(key):
                raise ValueError("Broker reconciliation is incomplete; activation refused")
            self.risk.configure(settings, self.clock())
            snapshot = self.risk.snapshot(self.clock())
            if snapshot["target_reached"]:
                self.store.halt_day(key, "DAILY_TARGET", self.clock())
            if snapshot["loss_limit_reached"]:
                self.store.halt_day(key, "DAILY_LOSS", self.clock())
            authorization = {"account_key": key, "day": utc_day(self.clock()),
                             "settings_digest": self._settings_digest(), "at": self.clock()}
            # Persist authorization evidence before granting in-memory send authority.
            # Audit storage failure leaves the prior explicit deactivation intact.
            self.store.audit("AUTHORIZATION_ACTIVATED", {"mode": mode, **authorization})
            self.authorization = authorization
            self.mode = mode
            self.entries_paused = bool(self.store.day_halt(key, self.clock()))
            self.last_reason = "Daily policy stopped new entries" if self.entries_paused else "Demo authorization activated"
            return self.status()

    def deactivate(self, reason="User deactivated trading"):
        with self.lock:
            unchanged = self.mode == "READ_ONLY" and self.authorization is None and self.entries_paused and self.last_reason == str(reason)
            self.mode, self.entries_paused, self.authorization = "READ_ONLY", True, None
            self._authorized_routing_fingerprint = None
            self.last_reason = str(reason)
            if not unchanged:
                self.store.audit("AUTHORIZATION_REVOKED", {"reason": self.last_reason})
            return {"mode": self.mode, "entries_paused": True, "reason": self.last_reason}

    def stop_entries(self, reason="User stopped new entries"):
        with self.lock:
            self.entries_paused, self.last_reason = True, str(reason)
            self.store.audit("ENTRIES_STOPPED", {"reason": self.last_reason})
            return {"mode": self.mode, "entries_paused": True, "reason": self.last_reason}

    def status(self):
        with self.lock:
            if self.authorization:
                try:
                    self._guard()
                except Exception as exc:
                    logging.getLogger(__name__).exception("Handled boundary failure")
                    self.last_reason = str(exc)
            key = self.risk.key
            return {"mode": self.mode, "entries_paused": self.entries_paused,
                    "authorization": dict(self.authorization) if self.authorization else None,
                    "regime_routing": {"enabled": self.regime_routing_enabled,
                                       "authorized_fingerprint": self._authorized_routing_fingerprint,
                                       "authority": "FILTER_ONLY"},
                    "reason": self.last_reason,
                    "unresolved": [i["id"] for i in self._unresolved(key)] if key else []}

    def execute(self, proposal, approved=False):
        with self.lock:
            try:
                self._guard(entry=True)
                if self.mode == "MANUAL_DEMO" and approved is not True:
                    raise ValueError("Manual approval of this proposal is required")
                candidate = dict(proposal)
                routing = self._regime_entry_check(candidate, phase="BEFORE_RESERVATION")
                if routing is not None:
                    candidate["regime_routing"] = routing
                prepared = self.risk.prepare(candidate, clock=self.clock)
                if not prepared["approved"]:
                    # Preparation may itself discover an account/day change;
                    # revoke the in-memory authorization through the same guard.
                    self._guard(entry=True)
                    return prepared
                return self._send(prepared["intent_id"], entry=True)
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                return self._failure(str(exc))

    @staticmethod
    def _failure(reason, intent_id=None):
        return {"approved": False, "ok": False, "state": "REFUSED", "reason": str(reason),
                "reasons": [str(reason)], "intent_id": intent_id}

    def _fresh_price(self, request):
        tick = self.broker.tick(request["symbol"])
        return self._quote_price(tick, self.clock())

    def _quote_price(self, tick, now):
        if not 0 <= now - number(tick.get("time"), "tick time") <= self.risk.settings["max_tick_age"]:
            # A stale quote is instrument-specific. Refuse this send while
            # leaving independent symbols eligible; account guards still apply.
            raise ValueError("Fresh broker price is required")
        bid, ask = number(tick.get("bid"), "bid", True), number(tick.get("ask"), "ask", True)
        if ask < bid:
            raise ValueError("Invalid broker spread")
        return bid, ask

    def _entry_send_check(self, intent, account, *, with_time_check=False):
        request = dict(intent["payload"]["request"])
        proposal = intent["payload"]["proposal"]
        session, calendar = self.broker.session(request["symbol"]), self.broker.calendar()
        info = self.broker.symbol(request["symbol"])
        tick = self.broker.tick(request["symbol"])
        def check_time(now):
            if not number(proposal.get("data_time"), "proposal data time") <= now < number(proposal.get("expires_at"), "proposal expiry"):
                raise ValueError("Proposal expired before send")
            if not session or not session.get("known") or not session.get("open") or not 0 <= now - number(session.get("as_of"), "session time") <= self.risk.settings["max_session_age"]:
                self.stop_entries("Market session unavailable")
                raise ValueError("Fresh open market session is required")
            if not calendar or calendar.get("ok") is not True or not calendar.get("known", calendar.get("coverage_known", False)) or not 0 <= now - number(calendar.get("as_of"), "calendar time") <= self.risk.settings["max_calendar_age"] or not number(calendar.get("from_utc"), "calendar start") <= now <= number(calendar.get("to_utc"), "calendar end"):
                self.stop_entries("Calendar coverage unavailable")
                raise ValueError("Fresh calendar coverage is required")
            calendar_event_veto(info, calendar, now)
            if info.get("expiration_time") and info["expiration_time"] <= now:
                raise ValueError("Symbol direction or contract validity changed")
            return self._quote_price(tick, now)
        # Bridge and quote reads can cross a second boundary. Validate their
        # timestamps against the clock after all reads, then again after math.
        now = self.clock()
        bid, ask = check_time(now)
        request["price"] = ask if request["side"] == "BUY" else bid
        zone = proposal.get("entry_zone")
        if zone is not None and (not isinstance(zone, (list, tuple)) or len(zone) != 2 or not number(zone[0], "entry zone lower") <= request["price"] <= number(zone[1], "entry zone upper")):
            raise ValueError("Quote left the entry zone before send")
        allowed = (1, 4) if request["side"] == "BUY" else (2, 4)
        if info.get("trade_mode") not in allowed or (info.get("expiration_time") and info["expiration_time"] <= now):
            raise ValueError("Symbol direction or contract validity changed")
        distance = max(number(info.get("trade_stops_level", 0), "stop level"), number(info.get("trade_freeze_level", 0), "freeze level")) * number(info.get("point"), "point", True)
        sl, tp = request["sl"], request["tp"]
        if request["side"] == "BUY" and not (sl < bid and bid - sl >= distance and tp > ask and tp - ask >= distance):
            raise ValueError("BUY stop distances changed before send")
        if request["side"] == "SELL" and not (sl > ask and sl - ask >= distance and tp < bid and bid - tp >= distance):
            raise ValueError("SELL stop distances changed before send")
        self.risk.minimum_rr_check(proposal, request, info)
        stop = sl + (-1 if request["side"] == "BUY" else 1) * self.risk.settings["slippage_points"] * info["point"]
        worst_open = request["price"] + (1 if request["side"] == "BUY" else -1) * self.risk.settings["slippage_points"] * info["point"]
        risk = -number(self.broker.calc_profit(request["side"], request["symbol"], request["volume"], worst_open, stop), "fresh stop risk") + self.risk._commission(request["symbol"]) * request["volume"]
        if risk > intent["reserved"] + 1e-8:
            raise ValueError("Price moved beyond the reserved stop risk")
        if proposal.get("execution_style") == "SCALP":
            current_account = self.broker.account()
            if account_key(current_account) != self.risk.key:
                raise ValueError("Scalp broker account changed before send")
            scalp_limit = self.risk.scalp_risk_cap(proposal, current_account)
            if Decimal(str(risk)) > Decimal(str(scalp_limit["requested_risk_amount"])):
                raise ValueError("Scalp percentage of current Equity changed before send")
        required_margin = number(self.broker.calc_margin(request["side"], request["symbol"], request["volume"], request["price"]), "fresh margin")
        if required_margin < 0 or required_margin > number(account.get("margin_free"), "free margin") * self.risk.settings["margin_fraction"]:
            raise ValueError("Free margin changed before send")
        snapshot = self.risk.snapshot(now)
        if snapshot["used"] > snapshot["risk_amount"] + 1e-8 or snapshot["unbounded"] or snapshot["cost_uncertainty"] or snapshot["target_reached"] or snapshot["loss_limit_reached"]:
            raise ValueError("Account-wide risk changed before send")
        if account.get("margin_mode") == 0 and any(p["symbol"] == request["symbol"] for p in snapshot["positions"]):
            raise ValueError("Netting position appeared before send")
        # Concurrent reservations already share the SQLite ledger; check the
        # broker book's factor exposure again immediately before its send claim.
        for bucket in intent["buckets"]:
            used = snapshot["bucket_exposure"].get(bucket, 0.) + sum(i["reserved"] for i in self.store.intents(self.risk.key) if i["state"] in ACTIVE_STATES and bucket in i["buckets"])
            if used > snapshot["risk_amount"] * self.risk.settings["correlation_cap_fraction"] + 1e-8:
                raise ValueError("Correlation exposure changed before send")
        check_time(self.clock())
        return (request, check_time) if with_time_check else request

    def _send(self, intent_id, entry=False):
        intent = self.store.intent(intent_id)
        if not intent or intent["state"] != "PREPARED":
            return self._failure("Intent already claimed or terminal", intent_id)
        # The official adapter uses an RLock, allowing read/check/send to be held
        # together. Independent application processes are guarded by SQLite.
        with getattr(self.broker, "lock", nullcontext()):
            try:
                account, key = self._guard(entry, intent_id)
                if entry:
                    request, entry_time_check = self._entry_send_check(intent, account, with_time_check=True)
                else:
                    request = self._management_send_check(intent)
                request["_authorized_account_key"] = key
                check = self.broker.check(request)
                if not check or check.get("retcode") != 0:
                    raise ValueError("Broker preflight refused: " + str(check))
                # Validate authorization again after order_check. No preflight
                # result grants permission to execute on a changed account.
                self._guard(entry, intent_id)
                rr_evidence = None
                if entry and self.risk.settings.get("decision_protocol", "general") == FOUR_SCHOOL_PROTOCOL:
                    # order_check can outlast the quote that approved its
                    # geometry. Refuse a changed request rather than sending an
                    # unchecked replacement or stretching its technical target.
                    fresh, entry_time_check = self._entry_send_check(intent, account, with_time_check=True)
                    if fresh != {k: v for k, v in request.items() if k != "_authorized_account_key"}:
                        raise ValueError("Quote changed during broker preflight; a fresh decision is required")
                    rr_evidence = self.risk.minimum_rr_check(
                        intent["payload"]["proposal"], fresh, self.broker.symbol(fresh["symbol"]))
                if entry:
                    # Calculation and preflight calls can consume the last
                    # valid second or cross the authorization's UTC day.
                    self._guard(entry, intent_id)
                    entry_time_check(self.clock())
                    self._regime_entry_check(intent["payload"]["proposal"], phase="BEFORE_SEND",
                                             prior=intent["payload"]["proposal"].get("regime_routing"))
                elif intent['payload'].get('reason') in ('FAST_CASH_TARGET','FAST_CASH_PROTECT_FALLBACK','FAST_CASH_PROTECTION','FAST_CASH_BROKER_TP'):
                    # Recheck cash and legal stop distances after broker I/O.
                    request=self._management_send_check(intent)
                    request['_authorized_account_key']=key
                if not self.store.claim_send(intent_id):
                    raise ValueError("Intent was claimed or another send is unresolved")
                updates = {"request": request, "send_started": self.clock()}
                if rr_evidence is not None:
                    updates["minimum_rr_evidence"] = rr_evidence
                self.store.set_intent_state(intent_id, "SENDING", **updates)
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                current = self.store.intent(intent_id)
                if current and current["state"] == "PREPARED":
                    self.store.set_intent_state(intent_id, "REJECTED", reason=str(exc))
                return self._failure(str(exc), intent_id)
            try:
                result = self.broker.send(request)
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                self.store.set_intent_state(intent_id, "UNKNOWN", reason=str(exc))
                self.deactivate("Broker response lost; reconciliation and reactivation required")
                return {"approved": False, "ok": False, "state": "UNKNOWN", "intent_id": intent_id,
                        "reason": str(exc), "reasons": [str(exc)]}
            code = result.get("retcode") if isinstance(result, dict) else None
            # Unknown/malformed/unsupported retcodes are ambiguous rather than
            # proof of rejection. In particular generic processing error 10011
            # does not prove that no broker-side execution took place.
            if type(code) is not int or code in UNKNOWN_CODES or (code not in SUCCESS_CODES and code not in KNOWN_REJECTION_CODES):
                self.store.set_intent_state(intent_id, "UNKNOWN", result=result, reason="Ambiguous broker result")
                self.deactivate("Ambiguous broker result; reconciliation and reactivation required")
                return {"approved": False, "ok": False, "state": "UNKNOWN", "intent_id": intent_id, "result": result,
                        "reason": "Ambiguous broker result", "reasons": ["Ambiguous broker result"]}
            if code not in SUCCESS_CODES:
                self.store.set_intent_state(intent_id, "REJECTED", result=result, reason="Broker explicitly rejected request")
                return {"approved": False, "ok": False, "state": "REJECTED", "intent_id": intent_id,
                        "result": result, "reason": "Broker explicitly rejected request", "reasons": [str(result)]}
            state = SUCCESS_CODES[code]
            self.store.set_intent_state(intent_id, state, result=result, confirmed=False)
        reconciliation = self._settle_success_ack(intent)
        current = self.store.intent(intent_id)
        resolved = not blocks_send(current)
        return {"approved": resolved, "ok": resolved, "state": current["state"], "intent_id": intent_id,
                "result": result, "request": request, "risk": current["reserved"],
                "confirmed": bool(current["payload"].get("confirmed")), "reconciliation": reconciliation,
                "reasons": [] if resolved else [reconciliation.get("reason") or "Broker confirmation pending; request will not be resent"]}

    def _settle_success_ack(self,intent):
        """Only a known successful send receives a bounded read-only grace.

        Never resend, release reservations without evidence, or restore revoked
        authorization. Individual broker reads can outlast this retry budget.
        """
        key=intent["account_key"];scope={intent["id"]}
        request=intent["payload"]["request"]
        if intent["kind"]=="MANAGEMENT" and request["action"]=="DEAL":
            position_id=intent["payload"].get("position_id")
            owners=[row for row in self.store.intents(key) if row["kind"]=="ENTRY" and
                    row["payload"].get("confirmed") and position_id not in (None,0) and
                    position_id in row["payload"].get("position_ids",[])]
            # A close can remove the live position before its exit deal arrives.
            # Defer only its uniquely confirmed owner, never unrelated results.
            if len(owners)==1:scope.add(owners[0]["id"])
        return self._wait_for_reconciliation(key,scope)

    def _wait_for_reconciliation(self,key,scope):
        """Read-only bounded wait; unresolved intents still block every send.

        Retains an existing authorization only. Never restores a revoked one.
        """
        deadline=self._settlement_clock()+SETTLEMENT_GRACE_SECONDS
        reconciliation=None
        for attempt in range(SETTLEMENT_MAX_READS):
            if attempt and self._settlement_clock()>=deadline:break
            reconciliation=self._reconcile(key,defer_unresolved=scope)
            if reconciliation.get("reason") or not self.authorization:return reconciliation
            try:self._guard()
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                # The normal guard still checks account, permissions, day and
                # settings before its expected unresolved-send refusal.
                if not self.authorization or reconciliation["ok"] or str(exc)!="Unresolved broker result blocks every send":
                    if self.authorization:self.deactivate(str(exc))
                    return {**reconciliation,"ok":False,"reason":str(exc)}
            if reconciliation["ok"]:return reconciliation
            remaining=deadline-self._settlement_clock()
            if remaining<=0 or attempt+1>=SETTLEMENT_MAX_READS:break
            try:self._settlement_sleep(min(SETTLEMENT_POLL_SECONDS,remaining))
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                if self.authorization:self.deactivate("Reconciliation failed: "+str(exc))
                return {**reconciliation,"ok":False,"reason":str(exc)}
        if self.authorization:self.deactivate("Broker result remains unresolved")
        return reconciliation

    def _history_book(self, key):
        account = self.broker.account()
        if account_key(account) != key:
            raise ValueError("Cannot reconcile another account's broker history")
        terminal = self.broker.terminal()
        if not terminal or not terminal.get("connected"):
            raise ValueError("Cannot reconcile while disconnected")
        intents = self.store.intents(key)
        positions, orders = self.broker.positions(), self.broker.orders()
        if positions is None or orders is None:
            raise ValueError("Broker positions/orders are unavailable")
        earliest = min([i["created"] for i in intents] + [p.get("time", self.clock()) for p in positions] + [self.clock()])
        deals, history = self.broker.deals(max(0., earliest - 86400)), self.broker.history_orders(max(0., earliest - 86400))
        if deals is None or history is None:
            raise ValueError("Broker deals/order history is unavailable")
        return account, intents, positions, orders, deals, history

    def reconcile(self, key=None):
        with self.lock:
            result=self._reconcile(key,allow_confirmed_exit_grace=True)
            scope=set(result.pop('confirmed_exit_grace',[]))
            if scope and self.authorization:
                self.store.audit('BROKER_EXIT_CONFIRMATION_WAIT',{'intent_ids':sorted(scope),
                    'maximum_seconds':SETTLEMENT_GRACE_SECONDS,'new_sends_blocked':True})
                started=self._settlement_clock()
                outcome=self._wait_for_reconciliation(key or self.risk.key,scope)
                self.store.audit('BROKER_EXIT_CONFIRMATION_RESULT',{'intent_ids':sorted(scope),
                    'confirmed':outcome.get('ok') is True,'elapsed_seconds':self._settlement_clock()-started,
                    'authorization_retained':self.authorization is not None})
                return outcome
            return result

    def _reconcile(self, key=None, *, defer_unresolved=(),allow_confirmed_exit_grace=False):
        with self.lock:
            try:
                key = key or self.risk.key or account_key(self.broker.account())
                _account, intents, positions, orders, deals, history = self._history_book(key)
                changes = [];exit_grace=set()
                # Entry reconciliation first establishes durable position IDs.
                for intent in intents:
                    if intent["kind"] == "ENTRY" and intent["state"] in ACTIVE_STATES:
                        change = self._reconcile_entry(intent, positions, orders, deals, history)
                        if change:
                            changes.append(change)
                            # A previously broker-confirmed position can leave
                            # the live book shortly before its TP/SL deal reaches
                            # history. Reserve its full risk and block all sends
                            # while allowing one bounded confirmation window.
                            # Existing UNKNOWN/SENDING results never qualify.
                            if (allow_confirmed_exit_grace and self.authorization
                                    and intent['state'] in ('FILLED','PARTIAL')
                                    and intent['payload'].get('confirmed') is True
                                    and intent['payload'].get('position_ids')
                                    and intent['payload'].get('filled_volume',0)>0
                                    and change.get('state')=='UNKNOWN'
                                    and self.store.intent(intent['id'])['payload'].get('reason')
                                        =='Filled position is absent without confirmed exit'):
                                exit_grace.add(intent['id'])
                for intent in self.store.intents(key):
                    if intent["kind"] == "MANAGEMENT" and intent["state"] in ACTIVE_STATES:
                        change = self._reconcile_management(intent, positions, orders, deals, history)
                        if change:
                            changes.append(change)
                unresolved = self._unresolved(key)
                deferred=set(defer_unresolved)|exit_grace
                if any(row["id"] not in deferred for row in unresolved) and self.authorization:
                    self.deactivate("Broker result remains unresolved")
                return {"ok": not unresolved, "changes": changes, "unresolved": [i["id"] for i in unresolved],
                        "as_of": self.clock(),"confirmed_exit_grace":sorted(exit_grace)}
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                if self.authorization:
                    self.deactivate("Reconciliation failed: " + str(exc))
                return {"ok": False, "changes": [], "unresolved": [], "reason": str(exc), "as_of": self.clock()}

    def _direct_match(self, record, intent):
        if record_matches(record, intent, self.risk.magic):
            return True
        result = intent["payload"].get("result") or {}
        request = intent["payload"]["request"]
        return record.get("magic") == self.risk.magic and record.get("symbol") == request["symbol"] and (
            (result.get("order") not in (None, 0) and (record.get("order") == result["order"] if "entry" in record else record.get("ticket") == result["order"])) or
            ("entry" in record and result.get("deal") not in (None, 0) and record.get("ticket") == result["deal"]))

    def _reconcile_entry(self, intent, positions, orders, deals, history):
        request = intent["payload"]["request"]
        entering = [d for d in deals if d.get("type") in (0, 1) and d.get("entry") == 0 and self._direct_match(d, intent)]
        ids = set(intent["payload"].get("position_ids", []))
        ids.update(d.get("position_id") for d in entering if d.get("position_id") not in (None, 0))
        owned_positions = [p for p in positions if p.get("magic") == self.risk.magic and
                           (record_matches(p, intent, self.risk.magic) or p.get("identifier") in ids)]
        ids.update(p.get("identifier", p.get("ticket")) for p in owned_positions)
        active_orders = [o for o in orders if self._direct_match(o, intent)]
        matched_history = [o for o in history if self._direct_match(o, intent)]
        exits = [d for d in deals if d.get("type") in (0, 1) and d.get("entry") in (1, 2, 3) and d.get("position_id") in ids]
        filled = sum(number(d.get("volume"), "entry fill volume", True) for d in entering)
        remaining = sum(number(p.get("volume"), "live position volume", True) for p in owned_positions)
        # A live position with our exact magic/comment is affirmative evidence of
        # entry, even when the history API has not exposed its deal yet.
        evidenced_fill = max(filled, remaining, number(intent["payload"].get("filled_volume", 0), "previous fill volume"))
        original_order = (intent["payload"].get("result") or {}).get("order")
        cancelled_proof = original_order not in (None, 0) and any(
            i["kind"] == "MANAGEMENT" and i["state"] == "CLOSED" and i["payload"].get("confirmed") and
            i["payload"]["request"]["action"] == "REMOVE" and i["payload"]["request"].get("order") == original_order
            for i in self.store.intents(intent["account_key"]))
        terminal = (cancelled_proof or (bool(matched_history) and all(h.get("state") in TERMINAL_ORDER_STATES for h in matched_history))) and not active_orders
        if not evidenced_fill:
            rejected = [h for h in matched_history if h.get("state") in (2, 5, 6)]
            if terminal and (rejected or cancelled_proof):
                state = "REJECTED" if any(h.get("state") == 5 for h in rejected) else "CANCELLED"
                self.store.set_intent_state(intent["id"], state, confirmed=True, reason="Broker history confirms no fill")
                return {"intent_id": intent["id"], "state": state}
            if active_orders:
                self.store.set_intent_state(intent["id"], "ACCEPTED", confirmed=True)
                return {"intent_id": intent["id"], "state": "ACCEPTED"}
            return None  # Absence is never proof that a request was rejected.
        exited = sum(number(d.get("volume"), "exit volume", True) for d in exits)
        if not owned_positions and exited + 1e-8 >= evidenced_fill and terminal:
            self.store.set_intent_state(intent["id"], "CLOSED", confirmed=True, filled_volume=evidenced_fill,
                                        position_ids=sorted(ids), reason="Broker fills and closed book confirm exit")
            return {"intent_id": intent["id"], "state": "CLOSED"}
        if not owned_positions and evidenced_fill and not active_orders:
            # A filled deal without an observable open position or confirmed exit
            # is inconsistent. Keep the original reservation and block all sends.
            self.store.set_intent_state(intent["id"], "UNKNOWN", reason="Filled position is absent without confirmed exit", position_ids=sorted(ids))
            return {"intent_id": intent["id"], "state": "UNKNOWN"}
        state = "PARTIAL" if evidenced_fill + 1e-8 < request["volume"] or active_orders else "FILLED"
        fields = {"confirmed": True, "filled_volume": evidenced_fill, "position_ids": sorted(ids)}
        if terminal and owned_positions and entering:
            # Only an affirmative terminal order history AND live book release
            # the unfilled/closed portion. Paid entry costs replace their planned
            # cost component; they are already charged in realized_losses.
            original = number(intent["payload"]["original_risk"], "original risk", True)
            paid_entry_cost = sum(r["opening_cost"] for r in cashflow_records(deals, self.store.intents(intent["account_key"]), self.risk.magic) if r["owner_id"] == intent["id"])
            offset = min(paid_entry_cost, number(intent["payload"].get("planned_cost", 0), "planned costs")) * min(1., remaining / filled)
            fields["reserved"] = max(0., original * min(1., remaining / request["volume"]) - offset)
        self.store.set_intent_state(intent["id"], state, **fields)
        return {"intent_id": intent["id"], "state": state, "reserved": self.store.intent(intent["id"])["reserved"]}

    def _reconcile_management(self, intent, positions, orders, deals, history):
        request, payload = intent["payload"]["request"], intent["payload"]
        result = payload.get("result") or {}
        done = result.get("retcode") == 10009
        action = request["action"]
        if action == "REMOVE":
            present = any(o.get("ticket") == request["order"] for o in orders)
            cancelled = any(h.get("ticket") == request["order"] and h.get("state") in (2, 6) for h in history)
            if not present and (cancelled or done):
                self.store.set_intent_state(intent["id"], "CLOSED", confirmed=True, confirmation_reason="Broker confirmed order removal")
                return {"intent_id": intent["id"], "state": "CLOSED"}
        elif action == "SLTP":
            position = next((p for p in positions if p.get("ticket") == request["position"]), None)
            if position and position.get("magic") == self.risk.magic and abs(number(position.get("sl"), "observed stop") - request["sl"]) < 1e-8 and abs(number(position.get("tp", 0), "observed target") - request.get("tp", 0)) < 1e-8:
                self.store.set_intent_state(intent["id"], "CLOSED", confirmed=True, confirmation_reason="Broker book confirms protection change")
                return {"intent_id": intent["id"], "state": "CLOSED"}
            if position is None:
                position_id=payload.get('position_id')
                owners=[i for i in self.store.intents(intent['account_key']) if i['kind']=='ENTRY'
                        and i['state']=='CLOSED' and i['payload'].get('confirmed')
                        and position_id not in (None,0) and position_id in i['payload'].get('position_ids',[])]
                exits=[d for d in deals if d.get('position_id')==position_id and d.get('type') in (0,1) and d.get('entry') in (1,2,3)]
                before=number(payload.get('position_volume_before',0),'amended position volume')
                still_live=any(p.get('identifier',p.get('ticket'))==position_id for p in positions)
                still_working=any(o.get('position_id')==position_id for o in orders)
                if len(owners)==1 and not still_live and not still_working and before>0 and sum(number(d.get('volume'),'exit volume',True) for d in exits)+1e-8>=before:
                    self.store.set_intent_state(intent['id'],'CLOSED',confirmed=True,
                        amendment_confirmed=done,
                        confirmation_reason=('Broker accepted amendment; owned position subsequently closed' if done else
                            'Owned position fully closed; uncertain protection amendment superseded without replay'))
                    return {'intent_id':intent['id'],'state':'CLOSED'}
        else:
            position_id = payload.get("position_id")
            exiting = [d for d in deals if d.get("position_id") == position_id and d.get("entry") in (1, 2, 3) and self._direct_match(d, intent)]
            filled = sum(number(d.get("volume"), "management fill volume", True) for d in exiting)
            live = sum(number(p.get("volume"), "remaining position volume", True) for p in positions if p.get("identifier") == position_id)
            before = number(payload.get("position_volume_before"), "position volume before close", True)
            working = any(self._direct_match(o, intent) for o in orders)
            terminal = any(self._direct_match(h, intent) and h.get("state") in TERMINAL_ORDER_STATES for h in history)
            if filled > 0 and abs(before - filled - live) <= 1e-7 and not working and (terminal or done):
                self.store.set_intent_state(intent["id"], "CLOSED", confirmed=True, filled_volume=filled,
                                            confirmation_reason="Broker exit deals and live book confirm close action")
                return {"intent_id": intent["id"], "state": "CLOSED", "filled_volume": filled}
        return None

    def _ownership(self, position, intents, deals, account):
        owner = self.risk._owned_intent(position, intents)
        if not owner or position.get("magic") != self.risk.magic:
            raise ValueError("Position ownership is not proven")
        identifier = position.get("identifier", position.get("ticket"))
        if account.get("margin_mode") == 0:
            related = [d for d in deals if d.get("position_id") == identifier and d.get("type") in (0, 1)]
            entering = [d for d in related if d.get("entry") == 0]
            if not entering or any(d.get("entry") in (2, 3) for d in related):
                raise ValueError("Netting position history is incomplete or mixed")
            for deal in related:
                if deal.get("magic") != self.risk.magic:
                    raise ValueError("External trades are mixed into the netting position")
                if deal.get("entry") == 0 and not any(i["kind"] == "ENTRY" and self._direct_match(deal, i) for i in intents):
                    raise ValueError("Netting entry is outside known Quant Trading AI intents")
        return owner

    def _management_send_check(self, intent):
        request = dict(intent["payload"]["request"])
        account, intents, positions, orders, deals, _history = self._history_book(intent["account_key"])
        if request["action"] == "REMOVE":
            order = next((o for o in orders if o.get("ticket") == request["order"]), None)
            if not order or not any(i["kind"] == "ENTRY" and self._direct_match(order, i) for i in intents):
                raise ValueError("Pending order ownership is not proven or order is absent")
            return request
        position = next((p for p in positions if p.get("ticket") == request["position"]), None)
        if not position:
            raise ValueError("Position disappeared before management send")
        owner=self._ownership(position, intents, deals, account)
        session = self.broker.session(request["symbol"])
        if not session or not session.get("known") or not session.get("open") or not 0 <= self.clock() - number(session.get("as_of"), "session time") <= self.risk.settings["max_session_age"]:
            raise ValueError("Fresh open market session is required for position management")
        bid, ask = self._fresh_price(request)
        info = self.broker.symbol(request["symbol"])
        cash_reason=intent['payload'].get('reason')
        if cash_reason in ('FAST_CASH_TARGET','FAST_CASH_PROTECT_FALLBACK','FAST_CASH_PROTECTION','FAST_CASH_BROKER_TP'):
            cash=self._fast_cash_context(position,owner,intents,deals,account)
            if cash is None:raise ValueError('Fast cash protection authorization changed')
            if cash_reason=='FAST_CASH_BROKER_TP':
                if request['action']!='SLTP':raise ValueError('Cash target requires an owned stop/target amendment')
                if abs(request['sl']-position.get('sl',0))>info['trade_tick_size']/2:
                    raise ValueError('Cash target amendment must preserve the existing stop')
                value=self._fast_cash_net(position,cash,request['tp'])
            elif cash_reason=='FAST_CASH_PROTECTION':
                value=self._fast_cash_net(position,cash,request['sl'])
            else:
                value=self._fast_cash_net(position,cash,bid if position['type']==0 else ask)
            minimum=self.risk.settings.get('fast_cash_target_usd',1.) if cash_reason in ('FAST_CASH_TARGET','FAST_CASH_BROKER_TP') else 1.
            if value+1e-8<minimum:raise ValueError('Cash profit changed before management send')
            if request['action']=='SLTP' and request.get('tp',0)!=position.get('tp',0):
                target=number(request.get('tp'),'cash broker target',True)
                grid=info['trade_tick_size'];quote=bid if position['type']==0 else ask
                distance=max(info.get('trade_stops_level',0),info.get('trade_freeze_level',0))*info['point']
                if abs(target/grid-round(target/grid))>1e-7 or cash['sign']*(target-quote)<max(distance,grid)-grid*1e-7:
                    raise ValueError('Cash target violates the broker price grid or distance')
                old_target=position.get('tp',0)
                if old_target>0 and cash['sign']*(target-old_target)>grid/2:
                    raise ValueError('Cash target must not delay an existing closer target')
                if self._fast_cash_net(position,cash,target)+1e-8<self.risk.settings.get('fast_cash_target_usd',1.):
                    raise ValueError('Cash broker target no longer covers the authorized net dollars')
        if request["action"] == "DEAL":
            if request["side"] != ("SELL" if position.get("type") == 0 else "BUY"):
                raise ValueError("Management direction must reduce the owned position")
            if request["volume"] > position["volume"] + 1e-8 or request["volume"] < info["volume_min"] - 1e-8:
                raise ValueError("Close volume violates broker or owned-volume bounds")
            if abs(request["volume"] / info["volume_step"] - round(request["volume"] / info["volume_step"])) > 1e-7:
                raise ValueError("Close volume is not on the broker lot grid")
            if abs(position["volume"] - intent["payload"]["position_volume_before"]) > 1e-7:
                raise ValueError("Position volume changed before close send")
            request["price"] = bid if request["side"] == "SELL" else ask
        else:
            sl, old_sl = number(request["sl"], "new protective stop", True), number(position.get("sl", 0), "old protective stop")
            distance = max(info.get("trade_stops_level", 0), info.get("trade_freeze_level", 0)) * info["point"]
            if abs(sl / info["trade_tick_size"] - round(sl / info["trade_tick_size"])) > 1e-7:
                raise ValueError("Protective stop is not on the price grid")
            if position["type"] == 0 and (sl < old_sl or not sl < bid or bid - sl < distance):
                raise ValueError("BUY protection cannot widen risk or violate stop distance")
            if position["type"] == 1 and ((old_sl > 0 and sl > old_sl) or not sl > ask or sl - ask < distance):
                raise ValueError("SELL protection cannot widen risk or violate stop distance")
        return request

    def _management_request(self, request, reason, position=None):
        try:
            _account, key = self._guard()
            target = request.get("position", request.get("order"))
            prior = [i for i in self.store.intents(key) if i["kind"] == "MANAGEMENT" and
                     i["payload"]["request"].get("position", i["payload"]["request"].get("order")) == target and
                     i["payload"]["request"]["action"] == request["action"]]
            if any(i["state"] in ACTIVE_STATES for i in prior):
                raise ValueError("Previous action on this target is not confirmed")
            if prior and prior[-1]["state"] == "REJECTED" and self.clock() - prior[-1]["updated"] < self.risk.settings.get("management_retry_seconds", 30):
                raise ValueError("Known rejection cooldown; broker state must be refreshed")
            # Sequence advances only after a confirmed action or explicit broker
            # rejection. An unknown result cannot create a replacement identity.
            seed = [key, request["action"], target, reason, request.get("volume"), request.get("sl"), len(prior)]
            iid = hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()
            request = {**request, "magic": self.risk.magic, "comment": comment_for(iid),
                       "deviation": int(self.risk.settings["slippage_points"])}
            if not self.store.management_intent(iid, key, request, reason, self.clock()):
                raise ValueError("Duplicate management intent")
            if position:
                self.store.set_intent_state(iid, "PREPARED", position_id=position.get("identifier", position["ticket"]),
                                            position_volume_before=position["volume"])
            return self._send(iid)
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            return self._failure(str(exc))

    def cancel_owned_orders(self, reason="User cancelled Quant Trading AI orders"):
        with self.lock:
            try:
                self._guard()
                if not self.reconcile()["ok"]:
                    raise ValueError("Reconciliation is incomplete")
                key = self.risk.key
                intents = self.store.intents(key)
                results = []
                for order in self.broker.orders():
                    if any(i["kind"] == "ENTRY" and self._direct_match(order, i) for i in intents):
                        results.append(self._management_request({"action": "REMOVE", "symbol": order["symbol"], "order": order["ticket"]}, reason))
                return {"ok": all(r.get("ok") for r in results), "results": results, "reason": reason}
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                return self._failure(str(exc))

    def _close_position(self, position, reason, volume=None):
        volume = position["volume"] if volume is None else volume
        return self._management_request({"action": "DEAL", "symbol": position["symbol"],
                                         "position": position["ticket"], "side": "SELL" if position["type"] == 0 else "BUY",
                                         "volume": volume, "price": position["price_current"], "sl": 0., "tp": 0.}, reason, position)

    def flatten_owned_positions(self, reason="User closed Quant Trading AI positions"):
        with self.lock:
            try:
                self._guard()
                if not self.reconcile()["ok"]:
                    raise ValueError("Reconciliation is incomplete")
                account, intents, positions, _orders, deals, _history = self._history_book(self.risk.key)
                results = []
                for position in positions:
                    if not self.risk._owned_intent(position, intents):
                        continue
                    try:
                        self._ownership(position, intents, deals, account)
                        results.append(self._close_position(position, reason))
                    except Exception as exc:
                        logging.getLogger(__name__).exception("Handled boundary failure")
                        results.append(self._failure(str(exc)))
                return {"ok": all(r.get("ok") for r in results), "results": results, "reason": reason,
                        "remaining_owned": len([p for p in self.broker.positions() if self.risk._owned_intent(p, self.store.intents(self.risk.key))])}
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                return self._failure(str(exc))

    def manage(self):
        with self.lock:
            try:
                self._guard()
                if not self.reconcile()["ok"]:
                    raise ValueError("Reconciliation is incomplete")
                book = self.risk.snapshot(self.clock())
                reason = "DAILY_LOSS" if book["loss_limit_reached"] else "DAILY_TARGET" if book["target_reached"] else None
                if reason:
                    self.store.halt_day(self.risk.key, reason, self.clock())
                halted = self.store.day_halt(self.risk.key, self.clock())
                if halted:
                    self.stop_entries(halted["reason"])
                    cancelled = self.cancel_owned_orders(halted["reason"])
                    flattened = self.flatten_owned_positions(halted["reason"])
                    final = self.risk.snapshot(self.clock())
                    final_intents = self.store.intents(self.risk.key)
                    owned_positions = [p for p in final["positions"] if self.risk._owned_intent(p, final_intents)]
                    owned_orders = [o for o in final["orders"] if any(i["kind"] == "ENTRY" and self._direct_match(o, i) for i in final_intents)]
                    return {"ok": cancelled.get("ok", False) and flattened.get("ok", False), "policy": halted["reason"],
                            "cancelled": cancelled, "flattened": flattened, "snapshot": final,
                            "remaining_owned_positions": len(owned_positions), "remaining_owned_orders": len(owned_orders),
                            "target_confirmed": final["realized_net"] - final["unattributed_costs"] >= final["target_amount"] and not final["cost_uncertainty"] and not owned_positions and not owned_orders and not self._unresolved(self.risk.key)}
                return self._manage_plans(book)
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                return self._failure(str(exc))

    def _manage_plans(self, book):
        account, intents, positions, _orders, deals, _history = self._history_book(self.risk.key)
        results = []
        for position in positions:
            intent = self.risk._owned_intent(position, intents)
            if not intent:
                continue
            try:
                self._ownership(position, intents, deals, account)
                proposal = intent["payload"].get("proposal", {})
                execution_plan = proposal.get("execution_plan", {})
                plan = {**execution_plan, **proposal.get("management", {})}
                if plan.get("allow_addition"):
                    raise ValueError("Position additions are not authorized")
                if not book.get('cost_uncertainty'):
                    cash_result=self._manage_fast_cash(position,intent,intents,deals,account)
                    if cash_result is not None:
                        results.append(cash_result)
                        if cash_result.get('ok'):continue
                bar_exit = self._completed_bar_exit(position, intent, execution_plan)
                if bar_exit:
                    results.append(self._close_position(position, bar_exit))
                    continue
                hold = plan.get("max_hold_seconds", proposal.get("max_hold_seconds"))
                invalidation = plan.get("invalidation_price", proposal.get("invalidation_price"))
                if hold is not None and self.clock() - position["time"] >= number(hold, "time exit", True):
                    results.append(self._close_position(position, "TIME_EXIT"))
                    continue
                bid, ask = self._fresh_price({"symbol": position["symbol"]})
                current = bid if position["type"] == 0 else ask
                if invalidation is not None and ((position["type"] == 0 and current <= number(invalidation, "invalidation")) or (position["type"] == 1 and current >= number(invalidation, "invalidation"))):
                    results.append(self._close_position(position, "SCENARIO_INVALIDATED"))
                    continue
                initial_stop = intent["payload"]["request"]["sl"]
                initial_distance = abs(position["price_open"] - initial_stop)
                if initial_distance <= 0:
                    continue
                multiple = (current - position["price_open"]) * (1 if position["type"] == 0 else -1) / initial_distance
                info = self.broker.symbol(position["symbol"])
                if plan.get("partial_at_r") is not None and multiple >= number(plan["partial_at_r"], "partial trigger", True) and not intent["payload"].get("partial_taken"):
                    fraction = number(plan.get("partial_fraction", .5), "partial fraction", True)
                    if fraction >= 1:
                        raise ValueError("Partial fraction must be below one")
                    volume = float((Decimal(str(position["volume"] * fraction)) / Decimal(str(info["volume_step"]))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(info["volume_step"])))
                    if volume >= info["volume_min"] and position["volume"] - volume >= info["volume_min"]:
                        result = self._close_position(position, "PLAN_PARTIAL_PROFIT", volume)
                        results.append(result)
                        if result.get("confirmed"):
                            current_intent = self.store.intent(intent["id"])
                            self.store.set_intent_state(intent["id"], current_intent["state"], partial_taken=True)
                        continue
                protect_at = plan.get("protect_at_r", plan.get("break_even_at_r"))
                if protect_at is not None and multiple >= number(protect_at, "protection trigger", True):
                    buffer_points = number(plan.get("breakeven_buffer_points", 0), "protection buffer")
                    if buffer_points < 0:
                        raise ValueError("Protection buffer cannot widen risk")
                    new_sl = position["price_open"] + (1 if position["type"] == 0 else -1) * info["point"] * buffer_points
                    new_sl = round(new_sl / info["trade_tick_size"]) * info["trade_tick_size"]
                    improves = new_sl > position.get("sl", 0) + info["trade_tick_size"] / 2 if position["type"] == 0 else position.get("sl", 0) == 0 or new_sl < position["sl"] - info["trade_tick_size"] / 2
                    if improves:
                        results.append(self._management_request({"action": "SLTP", "symbol": position["symbol"],
                                                                 "position": position["ticket"], "sl": new_sl, "tp": position.get("tp", 0)}, "PLAN_PROTECTION", position))
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                results.append(self._failure(str(exc)))
        return {"ok": all(r.get("ok") for r in results), "results": results, "policy": "STRATEGY_PLANS"}

    def _fast_cash_context(self,position,intent,intents,deals,account):
        """Explicit USD Demo management policy; never applies to manual positions."""
        p=intent.get('payload',{}).get('proposal',{})
        if not (self.risk.settings.get('fast_profit_protection') is True
                and p.get('execution_style')=='SCALP' and p.get('scalp_variant')=='fast'):
            return None
        if account.get('trade_mode')!=0 or account.get('currency')!='USD':
            raise ValueError('Cash protection requires the authorized USD Demo account')
        info=self.broker.symbol(position['symbol'])
        flows=cashflow_records(deals,intents,self.risk.magic)
        paid=sum(r['net'] for r in flows if r.get('owner_id')==intent['id'])
        return {'paid':paid,'swap':number(position.get('swap',0),'open swap'),
                'fee':self.risk._commission(position['symbol'])*position['volume']/2,
                'slip':self.risk.settings['slippage_points']*info['point'],
                'info':info,'sign':1 if position['type']==0 else -1}

    def _fast_cash_net(self,position,cash,exit_price):
        worst=number(exit_price,'cash exit price',True)-cash['sign']*cash['slip']
        if worst<=0:raise ValueError('Invalid cash exit after slippage reserve')
        return (number(self.broker.calc_profit('BUY' if cash['sign']==1 else 'SELL',position['symbol'],
                position['volume'],position['price_open'],worst),'cash profit')
                +cash['paid']+cash['swap']-cash['fee'])

    def _manage_fast_cash(self,position,intent,intents,deals,account):
        cash=self._fast_cash_context(position,intent,intents,deals,account)
        if cash is None:return None
        bid,ask=self._fresh_price({'symbol':position['symbol']})
        quote=bid if cash['sign']==1 else ask
        net=self._fast_cash_net(position,cash,quote)
        target_cash=self.risk.settings.get('fast_cash_target_usd',1.)
        if net+1e-8>=target_cash:
            return self._close_position(position,'FAST_CASH_TARGET')
        old=number(position.get('sl',0),'existing stop',True)
        target=self._fast_cash_broker_target(position,cash,quote)
        if net+1e-8<1. or self._fast_cash_net(position,cash,old)+1e-8>=1.:
            if target is None:return None
            plan=intent.get('payload',{}).get('proposal',{}).get('execution_plan',{})
            bar_exit=self._completed_bar_exit(position,intent,plan)
            if bar_exit:return self._close_position(position,bar_exit)
            result=self._management_request({'action':'SLTP','symbol':position['symbol'],
                'position':position['ticket'],'sl':old,'tp':target},'FAST_CASH_BROKER_TP',position)
            if not result.get('ok') and self.authorization:
                bid,ask=self._fresh_price({'symbol':position['symbol']})
                current=self._fast_cash_net(position,cash,bid if cash['sign']==1 else ask)
                if current+1e-8>=1.:
                    return self._close_position(position,'FAST_CASH_TARGET' if current+1e-8>=target_cash else 'FAST_CASH_PROTECT_FALLBACK')
            return result
        info=cash['info'];grid=number(info['trade_tick_size'],'cash price grid',True)
        distance=max(info.get('trade_stops_level',0),info.get('trade_freeze_level',0))*info['point']
        # Search legal broker ticks for the least protective improvement that
        # preserves a dollar after known costs and the adverse slippage reserve.
        import math
        if cash['sign']==1:
            lower=math.ceil(old/grid-1e-8)+1
            upper=math.floor((quote-max(distance,grid))/grid+1e-8)
        else:
            lower=-math.floor(old/grid+1e-8)+1
            upper=-math.ceil((quote+max(distance,grid))/grid-1e-8)
        if lower>upper or self._fast_cash_net(position,cash,cash['sign']*upper*grid)+1e-8<1.:
            return self._close_position(position,'FAST_CASH_PROTECT_FALLBACK')
        while lower<upper:
            middle=(lower+upper)//2
            if self._fast_cash_net(position,cash,cash['sign']*middle*grid)+1e-8>=1.:upper=middle
            else:lower=middle+1
        stop=round(cash['sign']*lower*grid,10)
        result=self._management_request({'action':'SLTP','symbol':position['symbol'],
            'position':position['ticket'],'sl':stop,'tp':target if target is not None else position.get('tp',0)},'FAST_CASH_PROTECTION',position)
        if not result.get('ok') and self.authorization:
            # A known amendment rejection must not hold a profitable position
            # through its retry cooldown. Cash is rechecked before this close.
            return self._close_position(position,'FAST_CASH_PROTECT_FALLBACK')
        return result

    def _fast_cash_broker_target(self,position,cash,quote):
        """Put the net cash exit at the broker without moving the loss stop.

        Rounded to a profitable broker tick, never further than a closer TP.
        If the contract geometry prevents this, local cash management remains.
        """
        import math
        info=cash['info'];grid=number(info['trade_tick_size'],'cash target grid',True);sign=cash['sign']
        old_sl=number(position.get('sl',0),'existing stop',True)
        distance=max(info.get('trade_stops_level',0),info.get('trade_freeze_level',0))*info['point']
        if sign*(quote-old_sl)<distance:return None
        lower=math.floor(sign*quote/grid);upper=lower+1;step=1
        for _ in range(32):
            price=sign*upper*grid
            if price<=0:return None
            if self._fast_cash_net(position,cash,price)+1e-8>=self.risk.settings.get('fast_cash_target_usd',1.):break
            step*=2;upper=lower+step
        else:return None
        while lower+1<upper:
            middle=(lower+upper)//2
            if self._fast_cash_net(position,cash,sign*middle*grid)+1e-8>=self.risk.settings.get('fast_cash_target_usd',1.):upper=middle
            else:lower=middle
        target=round(sign*upper*grid,10)
        if sign*(target-quote)<max(distance,grid)-grid*1e-7:return None
        old_target=number(position.get('tp',0),'existing target')
        if old_target>0 and (abs(old_target-target)<grid/2 or sign*(target-old_target)>0):return None
        return target

    def _completed_bar_exit(self, position, intent, plan):
        """Same causal plan used by walk-forward evaluation: a bar CLOSE must
        first be observable; its exit is sent at the following available quote.
        Missing bars never become synthetic elapsed-time bars.
        """
        max_hold = plan.get("max_hold_bars")
        invalidation = plan.get("invalidation")
        if max_hold is None and not invalidation:
            return None
        timeframe = plan.get("timeframe", intent["payload"].get("proposal", {}).get("timeframe"))
        seconds = TIMEFRAMES.get(timeframe)
        if seconds is None:
            raise ValueError("Execution plan requires a supported completed-bar timeframe")
        count = 100
        if max_hold is not None:
            max_hold = number(max_hold, "maximum hold bars", True)
            if int(max_hold) != max_hold or max_hold > 10000:
                raise ValueError("Maximum hold bars must be an integer up to 10000")
            count = max(count, int(max_hold) + 3)
        bars = self.broker.bars(position["symbol"], timeframe, count)
        if not bars:
            raise ValueError("Completed bars are missing for the execution plan")
        now = self.clock()
        last_time = -1.
        completed_since_entry = []
        for bar in bars:
            opening = number(bar.get("time"), "bar opening time")
            closing = number(bar.get("close"), "bar close", True)
            closed_at = bar_close_time(opening, timeframe)
            if opening <= last_time or closed_at > now:
                raise ValueError("Execution-plan bars are duplicated, unsorted or incomplete")
            last_time = opening
            if closed_at > position["time"]:
                completed_since_entry.append((opening, closing))
        # The entry bar counts after its close, as it does in quant next-open
        # simulation. A mid-bar broker fill therefore never counts a future close.
        if max_hold is not None and len(completed_since_entry) >= max_hold:
            return "PLAN_COMPLETED_BAR_TIME_EXIT"
        if invalidation:
            if not isinstance(invalidation, dict) or invalidation.get("evaluation") != "completed_bar_close":
                raise ValueError("Execution-plan invalidation evaluation is unsupported")
            level = number(invalidation.get("price"), "completed-bar invalidation level", True)
            reviewed = intent["payload"].get("last_reviewed_bar_time", -1.)
            new_bars = [(opening, close) for opening, close in completed_since_entry if opening > reviewed]
            if any((position["type"] == 0 and close < level) or (position["type"] == 1 and close > level) for opening, close in new_bars):
                return "PLAN_COMPLETED_BAR_INVALIDATION"
            if new_bars:
                current = self.store.intent(intent["id"])
                self.store.set_intent_state(intent["id"], current["state"], last_reviewed_bar_time=new_bars[-1][0])
        return None
