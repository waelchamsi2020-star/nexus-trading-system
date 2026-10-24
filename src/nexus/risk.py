"""Independent, account-wide risk veto and contract-aware size calculation."""
from __future__ import annotations

import hashlib
import json
import logging
import math
import time
from decimal import ROUND_FLOOR, Decimal, InvalidOperation

from .store import ACTIVE_STATES, account_key, utc_day

MAGIC = 741903
TRADE_DEAL_TYPES = {0, 1}
COST_DEAL_TYPES = {4, 7, 8, 9, 10, 11, 12, 17}
COMMISSION_DEAL_TYPES = {7, 8, 9, 10, 11}
EXCLUDED_DEAL_TYPES = {2, 3, 6}  # Balance transfers, credit, bonus.
FOUR_SCHOOL_PROTOCOL = "four_school_v1"
MINIMUM_REWARD_RISK = Decimal(2)


def protocol_certificate_hash(proposal):
    """Bind the local decision certificate to its original execution geometry.

    This is an integrity receipt for the authenticated engine, not a substitute
    for running the school rules. Never stamp a proposal merely because it has
    a favourable reward/risk ratio.
    """
    matrix = proposal.get("decision_matrix")
    if not isinstance(matrix, dict):
        raise ValueError("Four-school decision matrix is missing")  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    matrix = {key: value for key, value in matrix.items() if key != "certificate_hash"}
    execution = {key: proposal.get(key) for key in (
        "id", "intent_id", "symbol", "side", "strategy", "strategy_id", "version",
        "timeframe", "data_time", "expires_at", "sl", "execution_stop", "stop",
        "tp", "targets", "entry", "entry_zone", "invalidation", "execution_plan",
        "execution_style", "scalp_variant", "scalp_session_id", "requested_risk_percent", "requested_min_reward_risk", "requested_profit_percent",
        "execution_policy_revision", "scalp_policy_revision", "rule_revision", "protocol_revision",
    )}
    try:
        content = json.dumps({"execution": execution, "decision_matrix": matrix},
                             sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Four-school decision certificate contains invalid data") from exc
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _positive_decimal(value, label):
    if isinstance(value, bool):
        raise ValueError(label + " is invalid")  # noqa: TRY004 -- Keep ValueError validation contract consumed by API handlers and existing risk tests.
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(label + " is invalid") from None
    if not result.is_finite() or result <= 0:
        raise ValueError(label + " must be finite and positive")
    return result


def number(value, label, positive=False):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(label + " is missing or invalid") from None
    if not math.isfinite(value) or (positive and value <= 0):
        raise ValueError(label + " is invalid")
    return value


def intent_identity(proposal, key):
    supplied = proposal.get("intent_id", proposal.get("id"))
    identity = supplied or {k: proposal.get(k) for k in ("symbol", "side", "strategy", "version", "timeframe", "data_time", "expires_at", "sl", "tp")}
    return hashlib.sha256(json.dumps([key, identity], sort_keys=True, default=str).encode()).hexdigest()


def comment_for(intent_id):
    return "NX:" + intent_id[:24]


def record_matches(record, intent, magic=MAGIC):
    return record.get("magic") == magic and str(record.get("comment", "")) == comment_for(intent["id"])


def cashflow_records(deals, intents, magic=MAGIC):
    """Normalize actual broker cash flows with unique, proven ENTRY ownership.

    Separate broker fees often carry magic=0. Their order/position/comment must
    identify exactly one known entry; magic alone never establishes ownership.
    Opening commission offset additionally requires the original opening order,
    because a position link cannot distinguish entry from exit/periodic fees.
    """
    entries = [i for i in intents if i["kind"] == "ENTRY"]
    root_ids = {i["id"]: set(i["payload"].get("position_ids", [])) for i in entries}
    opening_orders = {i["id"]: set() for i in entries}
    closing_orders = {i["id"]: set() for i in entries}
    all_orders = {i["id"]: set() for i in entries}
    comments = {}
    for i in entries:
        comments.setdefault(comment_for(i["id"]), set()).add(i["id"])
    for i in entries:
        order = (i["payload"].get("result") or {}).get("order")
        if order not in (None, 0):
            opening_orders[i["id"]].add(order)
            all_orders[i["id"]].add(order)
    # Fill history can prove the opening order even after a lost send response.
    for d in deals:
        if d.get("type") not in TRADE_DEAL_TYPES or d.get("entry") != 0 or d.get("magic") != magic:
            continue
        owners = {i["id"] for i in entries if record_matches(d, i, magic) or d.get("order") in opening_orders[i["id"]]}
        if len(owners) == 1:
            owner = next(iter(owners))
            if d.get("position_id") not in (None, 0):
                root_ids[owner].add(d["position_id"])
            if d.get("order") not in (None, 0):
                opening_orders[owner].add(d["order"])
                all_orders[owner].add(d["order"])
    for i in intents:
        if i["kind"] != "MANAGEMENT":
            continue
        payload = i["payload"]
        owners = {root for root, ids in root_ids.items() if payload.get("position_id") not in (None, 0) and payload.get("position_id") in ids}
        removed = payload.get("request", {}).get("order")
        owners.update(root for root, ids in opening_orders.items() if removed not in (None, 0) and removed in ids)
        if owners:
            comments.setdefault(comment_for(i["id"]), set()).update(owners)
            order = (payload.get("result") or {}).get("order")
            if order not in (None, 0):
                for root in owners:
                    all_orders[root].add(order)
                    if payload.get("request", {}).get("action") == "DEAL":
                        closing_orders[root].add(order)
    for d in deals:
        if d.get("type") not in TRADE_DEAL_TYPES or d.get("entry") not in (1, 2, 3) or d.get("magic") != magic:
            continue
        owners = set(comments.get(str(d.get("comment", "")), set()))
        owners.update(root for root, ids in root_ids.items() if d.get("position_id") not in (None, 0) and d.get("position_id") in ids)
        if len(owners) == 1 and d.get("order") not in (None, 0):
            owner = next(iter(owners))
            all_orders[owner].add(d["order"])
            closing_orders[owner].add(d["order"])
    normalized, seen = [], {}
    for deal in deals:
        ticket = deal.get("ticket")
        if ticket not in (None, 0):
            if ticket in seen:
                if seen[ticket] != deal:
                    raise ValueError("Conflicting broker cash flow ticket")
                continue
            seen[ticket] = deal
        typ = deal.get("type")
        if typ in EXCLUDED_DEAL_TYPES:
            continue
        profit = number(deal.get("profit", 0), "deal profit")
        charges = sum(number(deal.get(k, 0), "deal " + k) for k in ("commission", "fee", "swap"))
        net = profit + charges
        if typ not in TRADE_DEAL_TYPES and net >= 0:
            continue  # Unproven financial windfalls never replenish budget/goal.
        kind = "TRADE" if typ in TRADE_DEAL_TYPES else "COST" if typ in COST_DEAL_TYPES else "UNKNOWN_COST"
        owners = set(comments.get(str(deal.get("comment", "")), set()))
        owners.update(root for root, ids in root_ids.items() if deal.get("position_id") not in (None, 0) and deal.get("position_id") in ids)
        owners.update(root for root, ids in all_orders.items() if deal.get("order") not in (None, 0) and deal.get("order") in ids)
        allowed_magic = deal.get("magic") == magic or (kind != "TRADE" and deal.get("magic", 0) == 0)
        owner = next(iter(owners)) if len(owners) == 1 and allowed_magic and kind != "UNKNOWN_COST" else None
        opening_cost = 0.
        if owner and kind == "TRADE" and deal.get("entry") == 0:
            opening_cost = max(0., -number(deal.get("commission", 0), "entry commission") - number(deal.get("fee", 0), "entry fee"))
        elif owner and typ == 7 and deal.get("order") not in (None, 0) and deal.get("order") in opening_orders[owner]:
            opening_cost = max(0., -net)
        normalized.append({"deal": deal, "kind": kind, "owner_id": owner, "net": net,
                           "gross": profit if kind == "TRADE" else 0.,
                           "costs": charges if kind == "TRADE" else net,
                           "opening_cost": opening_cost,
                           "closing_cost": bool(owner and deal.get("order") not in (None, 0) and deal.get("order") in closing_orders[owner]),
                           "ambiguous": len(owners) > 1 or (bool(owners) and not allowed_magic),
                           "foreign": bool(deal.get("magic", 0) not in (0, magic)) and not owners})
    return normalized


def cost_uncertainties(records, intents):
    planned = {i["id"] for i in intents if i["kind"] == "ENTRY" and i["state"] in ACTIVE_STATES and i["reserved"] > 0 and number(i["payload"].get("planned_cost", 0), "planned costs") > 0}
    reasons = []
    for r in records:
        uncertain = r["ambiguous"] or r["kind"] == "UNKNOWN_COST"
        if r["kind"] != "TRADE" and not r["foreign"]:
            if not r["owner_id"] and planned:
                uncertain = True
            if r["deal"].get("type") in COMMISSION_DEAL_TYPES and r["owner_id"] in planned and not r["opening_cost"] and not r["closing_cost"]:
                uncertain = True
        if uncertain:
            reasons.append("deal:" + str(r["deal"].get("ticket", "unknown")))
    return reasons


def calendar_event_veto(info, calendar, now):
    currencies = {str(info.get(k)) for k in ("currency_profit", "currency_margin") if info.get(k)}
    base = info.get("currency_base")
    if base and len(base) == 3 and base not in ("XAU", "XAG", "XPT", "XPD"):
        currencies.add(base)
    if not currencies or not currencies.issubset(set(calendar.get("currencies", []))):
        raise ValueError("Calendar currency coverage is incomplete for this contract")
    for event in calendar.get("events", []):
        if event.get("currency") not in currencies or number(event.get("importance", 0), "event importance") < 3:
            continue
        event_time = number(event.get("time_utc"), "high-impact event time")
        date_only = event.get("time_mode", 0) != 0
        if (date_only and int(event_time // 86400) == int(now // 86400)) or (not date_only and now - 1800 <= event_time <= now + 1800):
            raise ValueError("High-impact economic event blackout")


class RiskManager:
    def __init__(self, broker, store, magic=MAGIC):
        self.broker, self.store, self.magic = broker, store, magic
        self.settings = None
        self.key = None

    def configure(self, settings, now=None):
        now = time.time() if now is None else now
        settings = dict(settings)
        policy=settings.get("validation_policy","historical")
        if policy not in ("historical","forward_demo"):raise ValueError("Unknown validation policy")
        settings["validation_policy"]=policy
        protocol = settings.get("decision_protocol", "general")
        if protocol not in ("general", FOUR_SCHOOL_PROTOCOL, "multi_school_v1"):
            raise ValueError("Unknown decision protocol")
        settings["decision_protocol"] = protocol
        account = self.broker.account()
        cash_protection=settings.get('fast_profit_protection',False)
        if type(cash_protection) is not bool:
            raise ValueError('Fast profit protection must be boolean')
        if cash_protection and (account.get('trade_mode')!=0 or account.get('currency')!='USD'):
            raise ValueError('Dollar profit protection requires a USD Demo account')
        settings['fast_profit_protection']=cash_protection
        cash_target=number(settings.get('fast_cash_target_usd',1.),'cash profit target',True)
        if not 1 <= cash_target <= 2:raise ValueError('Cash target must be between one and two USD')
        settings['fast_cash_target_usd']=cash_target
        max_open = settings.get("max_open_positions", 3)
        if type(max_open) is not int or not 1 <= max_open <= 3:
            raise ValueError("Demo maximum open positions must be an integer from one to three")
        settings["max_open_positions"] = max_open
        key = account_key(account)
        equity = number(account.get("equity"), "equity", True)
        risk = number(settings.get("risk_amount", settings.get("daily_risk")), "daily risk", True)
        target = number(settings.get("target_amount", settings.get("daily_target")), "daily target", True)
        risk_unit = settings.get("risk_unit", "amount")
        target_unit = settings.get("target_unit", "amount")
        if risk_unit not in ("amount", "percent") or target_unit not in ("amount", "percent"):
            raise ValueError("Budget unit must be amount or percent")
        if risk_unit == "percent":
            risk = equity * risk / 100
        if target_unit == "percent":
            target = equity * target / 100
        commission = number(settings.get("commission_per_lot"), "known round-trip commission per lot")
        slippage = number(settings.get("slippage_points", settings.get("deviation", 10)), "slippage reserve points")
        if commission < 0 or slippage < 0:
            raise ValueError("Cost and slippage reserves cannot be negative")
        for field, default in (("max_trade_fraction", .2), ("correlation_cap_fraction", .5)):
            settings[field] = number(settings.get(field, default), field, True)
            if settings[field] > 1:
                raise ValueError(field + " must be at most one")
        settings.update(commission_per_lot=commission, slippage_points=slippage,
                        max_tick_age=number(settings.get("max_tick_age", 15), "max tick age", True),
                        max_session_age=number(settings.get("max_session_age", 300), "max session age", True),
                        max_calendar_age=number(settings.get("max_calendar_age", 300), "max calendar age", True),
                        margin_fraction=number(settings.get("margin_fraction", .8), "margin fraction", True))
        if settings["margin_fraction"] > 1:
            raise ValueError("margin_fraction must be at most one")
        day = self.store.ensure_day(key, risk, target, equity, now)
        if settings.pop("amend_daily_limits",False) is True:
            allow_increase=settings.pop("allow_daily_risk_increase",False) is True
            if allow_increase and account.get("trade_mode") != 0:
                raise ValueError("Daily risk increases require a verified Demo account")
            day=self.store.amend_day_limits(key,risk,target,now,allow_increase=allow_increase)
        settings.update(risk_amount=day["risk_amount"], target_amount=day["target_amount"])
        self.store.audit("DAILY_SETTINGS", {"account_key": key, "settings": settings, "day": day["day"]})
        self.settings, self.key = settings, key
        return settings

    def _settings(self):
        if self.settings is None or self.key is None:
            raise ValueError("Daily settings have not been activated")
        return self.settings

    def buckets(self, symbol):
        info = self.broker.symbol(symbol)
        configured = self._settings().get("correlation_buckets", {}).get(symbol)
        if configured:
            return list({str(v) for v in configured})
        buckets = {"symbol:" + symbol}
        for field in ("currency_base", "currency_profit"):
            if info.get(field):
                buckets.add("currency:" + str(info[field]))
        # Broker taxonomy adds a conservative common factor across instruments.
        path = str(info.get("path", "UNKNOWN")).split("\\")[0].split("/")[0]
        buckets.add("market:" + path)
        return sorted(buckets)

    def _owned_intent(self, position, intents):
        for intent in intents:
            if intent["kind"] != "ENTRY":
                continue
            if record_matches(position, intent, self.magic):
                return intent
            ids = intent["payload"].get("position_ids", [])
            if position.get("identifier") in ids and position.get("magic") == self.magic:
                return intent
        return None

    def snapshot(self, now=None):
        now = time.time() if now is None else now
        settings = self._settings()
        account = self.broker.account()
        if account_key(account) != self.key:
            raise ValueError("Account changed since activation")
        day = self.store.get_day(self.key, now)
        if day is None:
            raise ValueError("UTC day changed; explicit activation is required")
        start = int(now // 86400) * 86400
        deals = self.broker.deals(start)
        positions = self.broker.positions()
        orders = self.broker.orders()
        if deals is None or positions is None or orders is None:
            raise ValueError("Incomplete broker risk book")
        intents = self.store.intents(self.key)
        active = [i for i in intents if i["state"] in ACTIVE_STATES]
        reserved = sum(i["reserved"] for i in active)
        realized_losses = 0.0
        realized_net = account_realized_net = commission = swap = gross = 0.0
        unattributed_costs = 0.
        records = cashflow_records(deals, intents, self.magic)
        cost_uncertainty = cost_uncertainties(records, intents)
        for record in records:
            deal, net = record["deal"], record["net"]
            realized_losses += max(0.0, -net)
            account_realized_net += net
            if record["owner_id"]:
                realized_net += net
                gross += record["gross"]
                if record["kind"] == "TRADE":
                    commission += number(deal.get("commission", 0), "commission") + number(deal.get("fee", 0), "fee")
                    swap += number(deal.get("swap", 0), "swap")
                else:
                    commission += record["costs"]
            elif record["kind"] != "TRADE":
                unattributed_costs += max(0., -net)
        exposure = 0.0
        external_exposure = 0.0
        floating_net = 0.0
        floating_losses = 0.0
        closing_cost = 0.0
        unbounded = []
        bucket_exposure = {}
        owned_losses = {}
        owned_buckets = {}
        provenance = None
        for position in positions:
            symbol = position["symbol"]
            side = "BUY" if position.get("type") == 0 else "SELL" if position.get("type") == 1 else None
            if side is None:
                raise ValueError("Unknown position direction")
            volume = number(position.get("volume"), "position volume", True)
            profit = number(position.get("profit"), "position profit") + number(position.get("swap", 0), "position swap")
            floating_losses += max(0., -profit)
            sl = number(position.get("sl", 0), "position stop")
            info = self.broker.symbol(symbol)
            point = number(info.get("point"), "point", True)
            cost_per_lot = self._commission(symbol)
            cost = volume * cost_per_lot / 2
            owner = self._owned_intent(position, intents)
            if owner and account.get("margin_mode") == 0:
                if provenance is None:
                    since = min([start] + [number(p.get("time", start), "position time") - 86400 for p in positions])
                    provenance = self.broker.deals(max(0., since))
                    if provenance is None:
                        raise ValueError("Netting ownership history is missing")
                related = [d for d in provenance if d.get("position_id") == position.get("identifier") and d.get("type") in (0, 1)]
                entering = [d for d in related if d.get("entry") == 0]
                if not entering or any(d.get("entry") in (2, 3) or d.get("magic") != self.magic for d in related) or any(not any(record_matches(d, i, self.magic) for i in intents if i["kind"] == "ENTRY") for d in entering):
                    unbounded.append("mixed-netting:" + symbol)
                    owner = None
            if owner:
                floating_net += profit
                closing_cost += cost
            if sl <= 0:
                loss = day["risk_amount"]
                unbounded.append(symbol)
            else:
                stop = sl - settings["slippage_points"] * point if side == "BUY" else sl + settings["slippage_points"] * point
                stop_profit = number(self.broker.calc_profit(side, symbol, volume, number(position["price_open"], "open price", True), stop), "stop profit")
                # Stop risk is measured from the original fill, never from a
                # temporarily profitable mark. Profits do not reduce the frozen
                # intent reservation; realized results are netted below.
                stop_profit -= max(0., -number(position.get("swap", 0), "open swap"))
                loss = max(0., -profit, -stop_profit) + cost
            if owner and owner["state"] in ACTIVE_STATES:
                # Already paid entry costs and losses are in the realized-loss ledger.
                # Reserve replaces position risk, avoiding two counts of the same stop.
                owned_losses[owner["id"]] = owned_losses.get(owner["id"], 0.) + loss
                owned_buckets.setdefault(owner["id"], set()).update(self.buckets(symbol))
                bucket_amount = 0.
            else:
                exposure += loss
                external_exposure += loss
                bucket_amount = loss
            for bucket in self.buckets(symbol):
                bucket_exposure[bucket] = bucket_exposure.get(bucket, 0.) + bucket_amount
        for owner_id, loss in owned_losses.items():
            owner = next(i for i in active if i["id"] == owner_id)
            extra = max(0., loss - owner["reserved"])
            exposure += extra
            for bucket in owned_buckets[owner_id]:
                bucket_exposure[bucket] = bucket_exposure.get(bucket, 0.) + extra
        for order in orders:
            if not any(record_matches(order, i, self.magic) for i in active):
                # Unknown pending entries can execute independently of this app.
                unbounded.append("order:" + str(order.get("ticket")))
                exposure += day["risk_amount"]
                external_exposure += day["risk_amount"]
        # Daily limit is net realized trading loss, including external trades
        # and broker costs. Deposits/withdrawals are excluded by cashflow_records.
        # Realized gains offset losses but never expand the configured limit.
        # Keep original reservations intact for every active/uncertain intent.
        realized_net_loss = max(0., -account_realized_net)
        used = realized_net_loss + reserved + exposure
        remaining = max(0., day["risk_amount"] - used)
        net_target = realized_net + floating_net - closing_cost - unattributed_costs
        halted = self.store.day_halt(self.key, now)
        return {"account_key": self.key, "day": day["day"], "risk_amount": day["risk_amount"],
                "target_amount": day["target_amount"], "realized_losses": realized_losses,
                "account_realized_net": account_realized_net, "realized_net_loss": realized_net_loss,
                "daily_loss_basis": "net_realized_plus_floating_losses",
                "realized_gross": gross, "realized_net": realized_net, "commission_fee": commission,
                "swap": swap, "floating_net": floating_net, "estimated_exit_cost": closing_cost,
                "reserved": reserved, "exposure": exposure, "external_exposure": external_exposure,
                "used": used, "remaining": remaining, "net_target": net_target,
                "target_reached": net_target >= day["target_amount"] and not cost_uncertainty,
                "unattributed_costs": unattributed_costs, "cost_uncertainty": cost_uncertainty,
                "floating_losses": floating_losses,
                "loss_limit_reached": realized_net_loss + floating_losses >= day["risk_amount"],
                "budget_exhausted": used >= day["risk_amount"], "halted": halted,
                "unbounded": unbounded, "bucket_exposure": bucket_exposure,
                "positions": positions, "orders": orders}

    def _commission(self, symbol):
        costs = self._settings().get("symbol_commission_per_lot", {})
        value = number(costs.get(symbol, self.settings["commission_per_lot"]), "round-trip commission reserve")
        if value < 0:
            raise ValueError("Commission reserve cannot be negative")
        return value

    def validate_protocol_certificate(self, proposal):
        """Require the current, untampered matrix when strict mode is active."""
        if self._settings().get("decision_protocol", "general") not in (FOUR_SCHOOL_PROTOCOL,"multi_school_v1"):
            return
        # The expected revision comes from the shipped rules, never from a
        # caller-supplied setting or a superficially plausible SHA string.
        from .confluence import PROTOCOL_REVISION
        if self._settings().get("decision_protocol")=="multi_school_v1":
            from .multischool import PROTOCOL_REVISION
            if proposal.get("decision_protocol")!="multi_school_v1":raise ValueError("Multi-school protocol identity changed")
        revision = proposal.get("protocol_revision")
        if (not isinstance(revision, str) or len(revision) != 64 or
                any(c not in "0123456789abcdef" for c in revision) or
                revision != PROTOCOL_REVISION):
            raise ValueError("Current four-school protocol revision is required")
        matrix = proposal.get("decision_matrix")
        if not isinstance(matrix, dict) or matrix.get("passed") is not True:
            raise ValueError("Four-school confluence certificate has not passed")
        supplied = matrix.get("certificate_hash")
        if (not isinstance(supplied, str) or len(supplied) != 64 or
                supplied != protocol_certificate_hash(proposal)):
            raise ValueError("Four-school decision certificate is missing or changed")

    def scalp_risk_cap(self, proposal, account):
        """A percentage of current broker Equity can reduce, never add budget."""
        if proposal.get("execution_style") != "SCALP":
            return None
        variant = proposal.get("scalp_variant", "normal")
        if variant not in ("normal", "fast"):
            raise ValueError("Unknown scalp variant")
        percent = _positive_decimal(proposal.get("requested_risk_percent"), "Scalp risk percent")
        if percent > Decimal(100):
            raise ValueError("Scalp risk percent must be at most 100")
        equity = _positive_decimal(account.get("equity"), "Scalp broker Equity")
        cap = number(equity * percent / Decimal(100), "Scalp requested risk amount", True)
        extra = {}
        if proposal.get("requested_profit_percent") is not None:
            profit_percent = _positive_decimal(proposal["requested_profit_percent"], "Scalp profit percent")
            if profit_percent > 100: raise ValueError("Scalp profit percent must be at most 100")
            extra = {"requested_profit_percent": float(profit_percent),
                     "requested_profit_amount": float(equity * profit_percent / Decimal(100))}
        return {**extra, "scalp_variant": variant, "requested_risk_percent": float(percent),
                "requested_risk_amount": cap, "equity_at_risk_sizing": float(equity)}

    def minimum_rr_check(self, proposal, request, info):
        """Independently veto price and final-volume net reward/risk below 2.

        Every adverse reserve is included: entry slippage, stop slippage,
        target slippage and the known round-trip commission. Geometry remains
        exactly as supplied; this function never manufactures a farther target
        or a wider stop to pass the protocol.
        """
        settings = self._settings()
        if settings.get("decision_protocol", "general") not in (FOUR_SCHOOL_PROTOCOL,"multi_school_v1"):
            return None
        self.validate_protocol_certificate(proposal)
        minimum = _positive_decimal(proposal.get("requested_min_reward_risk", 2), "Requested reward/risk minimum")
        if minimum < MINIMUM_REWARD_RISK:
            raise ValueError("Requested reward/risk minimum must be at least 2")
        side, symbol = request.get("side"), request.get("symbol")
        if (side not in ("BUY", "SELL") or symbol != proposal.get("symbol") or
                side != str(proposal.get("side", "")).upper()):
            raise ValueError("Four-school execution identity changed")
        price = _positive_decimal(request.get("price"), "Reward/risk entry")
        stop = _positive_decimal(request.get("sl"), "Reward/risk stop")
        target = _positive_decimal(request.get("tp"), "Reward/risk TP1")
        original_stop = proposal.get("sl", proposal.get("execution_stop", proposal.get("stop")))
        original_targets = proposal.get("targets") or []
        original_target = proposal.get("tp", original_targets[0] if original_targets else None)
        if (stop != _positive_decimal(original_stop, "Certified stop") or
                target != _positive_decimal(original_target, "Certified TP1")):
            raise ValueError("Certified structural stop or TP1 changed")
        volume = _positive_decimal(request.get("volume"), "Reward/risk volume")
        tick_size = _positive_decimal(info.get("trade_tick_size"), "Reward/risk tick size")
        for value, label in ((stop, "stop"), (target, "TP1")):
            units = value / tick_size
            if abs(units - units.to_integral_value()) > Decimal("0.000001"):
                raise ValueError("Reward/risk " + label + " is off the broker price grid")
        direction = Decimal(1) if side == "BUY" else Decimal(-1)
        price_risk = (price - stop) * direction
        price_reward = (target - price) * direction
        if price_risk <= 0 or price_reward < price_risk * minimum:
            raise ValueError("Four-school price reward/risk is below 1:" + str(minimum))
        point = _positive_decimal(info.get("point"), "Reward/risk point")
        slip = Decimal(str(settings["slippage_points"])) * point
        worst_open = price + direction * slip
        worst_stop = stop - direction * slip
        worst_target = target - direction * slip
        if min(worst_open, worst_stop, worst_target) <= 0:
            raise ValueError("Reward/risk slippage gives an invalid execution price")
        try:
            stop_profit = Decimal(str(self.broker.calc_profit(
                side, symbol, float(volume), float(worst_open), float(worst_stop))))
            target_profit = Decimal(str(self.broker.calc_profit(
                side, symbol, float(volume), float(worst_open), float(worst_target))))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Broker reward/risk calculation is invalid") from None
        if (not stop_profit.is_finite() or not target_profit.is_finite() or
                stop_profit >= 0 or target_profit <= 0):
            raise ValueError("Broker reward/risk calculation has invalid direction")
        fee = Decimal(str(self._commission(symbol))) * volume
        net_risk, net_reward = -stop_profit + fee, target_profit - fee
        if net_risk <= 0 or net_reward <= 0 or net_reward < net_risk * minimum:
            raise ValueError("Four-school net reward/risk after costs is below 1:" + str(minimum))
        return {"protocol": settings["decision_protocol"], "protocol_revision": proposal["protocol_revision"],
                "minimum": str(minimum), "price_reward_risk": str(price_reward / price_risk),
                "net_reward_risk": str(net_reward / net_risk), "net_risk": str(net_risk),
                "net_reward": str(net_reward), "volume": str(volume),
                "worst_entry": str(worst_open), "worst_stop": str(worst_stop),
                "worst_target": str(worst_target), "round_trip_commission": str(fee)}

    def prepare(self, proposal, intent_id=None, now=None, *, clock=None):
        # Explicit numeric `now` remains a fixed clock for deterministic callers.
        # The sender supplies its clock so broker I/O cannot freeze validation
        # at the instant preparation began.
        validation_clock = clock if clock is not None else (time.time if now is None else lambda: now)
        try:
            return self._prepare(proposal, intent_id, validation_clock)
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            result = {"approved": False, "reasons": [str(exc)], "reason": str(exc)}
            self.store.audit("RISK_REJECTED", {"proposal": proposal, **result})
            return result

    def _prepare(self, proposal, intent_id, clock):
        if self._settings().get("scalp_only") is True:
            variant=proposal.get("scalp_variant")
            profile=self._settings().get("scalping",{}).get(variant,{})
            if proposal.get("execution_style") != "SCALP" or not profile.get("enabled"):
                raise ValueError("Authorization allows the selected scalp variant only")
        settings = self._settings()
        self.validate_protocol_certificate(proposal)
        symbol, side = proposal.get("symbol"), str(proposal.get("side", "")).upper()
        if not symbol or side not in ("BUY", "SELL"):
            raise ValueError("Symbol and BUY/SELL direction are required")
        if proposal.get("allow_additions") or proposal.get("add_on"):
            raise ValueError("Position additions are not an authorized v1 execution policy")
        forward_trial=(settings.get("validation_policy")=="forward_demo" and proposal.get("validation_policy")=="forward_demo" and proposal.get("signal_validated") is True)
        if (proposal.get("qualified") is not True and not forward_trial) or proposal.get("news_ok") is not True:
            raise ValueError("Committee, quantitative and news gates are required")
        expires = number(proposal.get("expires_at"), "proposal expiry", True)
        data_time = number(proposal.get("data_time"), "data time", True)
        account = self.broker.account()
        if account_key(account) != self.key or account.get("trade_mode") != 0:
            raise ValueError("Only the authorized Demo account is eligible")
        scalp_limit = self.scalp_risk_cap(proposal, account)
        info, tick = self.broker.symbol(symbol), self.broker.tick(symbol)
        session, calendar = self.broker.session(symbol), self.broker.calendar()
        def check_time(now):
            if not data_time <= now < expires or now - data_time > settings.get("max_proposal_age", 900):
                raise ValueError("Proposal is stale or from the future")
            if session is None or not session.get("known") or not session.get("open"):
                raise ValueError("Market session unknown or closed")
            if not 0 <= now - number(session.get("as_of"), "session time") <= settings["max_session_age"]:
                raise ValueError("Market session data is stale")
            if calendar is None or calendar.get("ok") is not True or not calendar.get("known", calendar.get("coverage_known", False)):
                raise ValueError("Economic calendar coverage unknown")
            calendar_time = calendar.get("as_of", calendar.get("received_at"))
            if not 0 <= now - number(calendar_time, "calendar time") <= settings["max_calendar_age"]:
                raise ValueError("Economic calendar is stale")
            if not number(calendar.get("from_utc"), "calendar interval start") <= now <= number(calendar.get("to_utc"), "calendar interval end"):
                raise ValueError("Economic calendar does not cover current time")
            calendar_event_veto(info, calendar, now)
            if not 0 <= now - number(tick.get("time"), "tick time") <= settings["max_tick_age"]:
                raise ValueError("Tick is stale or from the future")
            if info.get("expiration_time") and info["expiration_time"] <= now:
                raise ValueError("Contract expired")
        now = clock()
        check_time(now)
        modes = (1, 4) if side == "BUY" else (2, 4)
        if info.get("trade_mode") not in modes:
            raise ValueError("Symbol does not allow this direction")
        expiration = info.get("expiration_time", 0)
        if expiration and expiration <= now:
            raise ValueError("Contract expired")
        point = number(info.get("point"), "point", True)
        tick_size = number(info.get("trade_tick_size"), "price tick size", True)
        bid, ask = number(tick.get("bid"), "bid", True), number(tick.get("ask"), "ask", True)
        if ask < bid:
            raise ValueError("Invalid quote spread")
        price = ask if side == "BUY" else bid
        zone = proposal.get("entry_zone")
        if zone is not None and (not isinstance(zone, (list, tuple)) or len(zone) != 2 or not number(zone[0], "entry zone lower") <= price <= number(zone[1], "entry zone upper")):
            raise ValueError("Fresh quote is outside the qualified entry zone")
        sl = number(proposal.get("sl", proposal.get("execution_stop", proposal.get("stop"))), "execution stop", True)
        targets = proposal.get("targets") or []
        tp = number(proposal.get("tp", targets[0] if targets else None), "target", True)
        for value, label in ((sl, "stop"), (tp, "target")):
            if abs(value / tick_size - round(value / tick_size)) > 1e-6:
                raise ValueError(label + " is not on the broker price grid")
        distance = max(number(info.get("trade_stops_level", 0), "stop level"), number(info.get("trade_freeze_level", 0), "freeze level")) * point
        if side == "BUY" and not (sl < bid and bid - sl >= distance and tp > ask and tp - ask >= distance):
            raise ValueError("BUY stop/target violates direction or broker distance")
        if side == "SELL" and not (sl > ask and sl - ask >= distance and tp < bid and bid - tp >= distance):
            raise ValueError("SELL stop/target violates direction or broker distance")
        book = self.snapshot(now)
        active_entries = [i for i in self.store.intents(self.key)
                          if i["kind"] == "ENTRY" and i["state"] in ACTIVE_STATES]
        if (len(book["positions"]) + len(book["orders"]) + len(active_entries)
                >= settings["max_open_positions"]):
            raise ValueError("MAX_OPEN_POSITIONS_REACHED")
        if book["cost_uncertainty"]:
            raise ValueError("Broker cost attribution is uncertain; new entries are blocked")
        if book["unbounded"]:
            raise ValueError("Unbounded external or unstopped account exposure")
        if book["target_reached"] or book["loss_limit_reached"] or book["halted"]:
            raise ValueError("Daily target/loss policy has stopped entry")
        # Do not aggregate an entry into an existing netting position; its identity
        # and stops could modify a position outside this intent's authority.
        if account.get("margin_mode") not in (0, 2):
            raise ValueError("Unknown account position accounting mode")
        if account.get("margin_mode") == 0 and any(p["symbol"] == symbol for p in book["positions"]):
            raise ValueError("Netting symbol already has a position")
        min_volume = number(info.get("volume_min"), "minimum lot", True)
        max_volume = number(info.get("volume_max"), "maximum lot", True)
        step = number(info.get("volume_step"), "volume step", True)
        worst_stop = sl - settings["slippage_points"] * point if side == "BUY" else sl + settings["slippage_points"] * point
        worst_open = price + settings["slippage_points"] * point if side == "BUY" else price - settings["slippage_points"] * point
        if worst_stop <= 0:
            raise ValueError("Slippage reserve gives invalid stop price")
        unit_loss = max(0., -number(self.broker.calc_profit(side, symbol, 1., worst_open, worst_stop), "contract stop loss")) + self._commission(symbol)
        if unit_loss <= 0:
            raise ValueError("Contract-aware stop risk is not positive")
        permitted = min(book["remaining"], book["risk_amount"] * settings["max_trade_fraction"])
        if scalp_limit is not None:
            permitted = min(permitted, scalp_limit["requested_risk_amount"])
        bucket_names = self.buckets(symbol)
        bucket_limits = {b: max(0., book["risk_amount"] * settings["correlation_cap_fraction"] - book["bucket_exposure"].get(b, 0)) for b in bucket_names}
        active = [i for i in self.store.intents(self.key) if i["state"] in ACTIVE_STATES]
        for b in bucket_names:
            permitted = min(permitted, bucket_limits[b] - sum(i["reserved"] for i in active if b in i["buckets"]))
        if scalp_limit is not None:
            scalp_limit["actual_risk_cap"] = max(0., permitted)
        volume = float((Decimal(str(min(max_volume, permitted / unit_loss))) / Decimal(str(step))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(step)))
        profit_cap = scalp_limit.get("requested_profit_amount") if scalp_limit else None
        worst_target = tp - settings["slippage_points"] * point if side == "BUY" else tp + settings["slippage_points"] * point
        def net_target(lots):
            return number(self.broker.calc_profit(side, symbol, lots, worst_open, worst_target), "Scalp target profit") - self._commission(symbol) * lots
        if profit_cap is not None:
            unit_reward = net_target(1.)
            if unit_reward <= 0: raise ValueError("Scalp net target must be positive")
            volume = min(volume, float((Decimal(str(profit_cap / unit_reward)) / Decimal(str(step))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(step))))
        limit = number(info.get("volume_limit", 0), "direction volume limit")
        if limit > 0:
            existing = sum(number(p["volume"], "position volume") for p in book["positions"] if p["symbol"] == symbol and p.get("type") == (0 if side == "BUY" else 1))
            existing += sum(number(o.get("volume_current", o.get("volume_initial", 0)), "order volume") for o in book["orders"] if o.get("symbol") == symbol and o.get("type") in ((0, 2, 4, 6) if side == "BUY" else (1, 3, 5, 7)))
            volume = min(volume, float((Decimal(str(max(0., limit - existing))) / Decimal(str(step))).to_integral_value(rounding=ROUND_FLOOR) * Decimal(str(step))))
        free_margin = number(account.get("margin_free"), "free margin") * settings["margin_fraction"]
        # Margin models can be nonlinear. Binary search on valid broker lot steps.
        units = round(volume / step)
        low, high = 0, units
        while low < high:
            mid = (low + high + 1) // 2
            margin = number(self.broker.calc_margin(side, symbol, mid * step, price), "required margin")
            if margin < 0:
                raise ValueError("Invalid negative required margin")
            if margin <= free_margin and (profit_cap is None or net_target(mid * step) <= profit_cap + 1e-8):
                low = mid
            else:
                high = mid - 1
        volume = round(low * step, 10)
        if volume + 1e-10 < min_volume:
            raise ValueError("Minimum broker lot exceeds risk or margin budget")
        amount = -number(self.broker.calc_profit(side, symbol, volume, worst_open, worst_stop), "stop loss") + self._commission(symbol) * volume
        if amount <= 0 or amount > permitted + 1e-8:
            raise ValueError("Final contract risk exceeds permitted budget")
        if profit_cap is not None:
            planned_reward = net_target(volume)
            if planned_reward <= 0 or planned_reward > profit_cap + 1e-8:
                raise ValueError("Final scalp target exceeds requested Equity profit percentage")
            scalp_limit["planned_net_target"] = planned_reward
        rr_evidence = self.minimum_rr_check(proposal, {
            "symbol": symbol, "side": side, "price": price, "sl": sl,
            "tp": tp, "volume": volume}, info)
        iid = intent_id or intent_identity(proposal, self.key)
        request = {"action": "DEAL", "symbol": symbol, "side": side, "volume": volume,
                   "price": price, "sl": sl, "tp": tp, "magic": self.magic,
                   "comment": comment_for(iid), "deviation": int(settings["slippage_points"])}
        check = self.broker.check(request)
        if not check or check.get("retcode") != 0:
            raise ValueError("Broker preflight rejected request: " + str(check))
        payload = {"proposal": proposal, "request": request, "original_risk": amount,
                   "planned_cost": self._commission(symbol) * volume,
                   "contract": {k: info.get(k) for k in ("trade_calc_mode", "trade_contract_size", "currency_profit", "currency_margin", "point", "trade_tick_size", "volume_min", "volume_max", "volume_step", "trade_stops_level")},
                   "filled_volume": 0., "position_ids": []}
        if rr_evidence is not None:
            payload["minimum_rr_evidence"] = rr_evidence
        if scalp_limit is not None:
            payload.update(scalp_limit)
        # Sizing, history and preflight are broker calls too. Refuse an expired
        # proposal/quote or changed UTC day before recording any reservation.
        reservation_account = self.broker.account()
        now = clock()
        check_time(now)
        if account_key(reservation_account) != self.key or reservation_account.get("trade_mode") != 0:
            raise ValueError("Only the authorized Demo account is eligible")
        if utc_day(now) != book["day"]:
            raise ValueError("UTC day changed; explicit activation is required")
        reservation = self.store.reserve(iid, self.key, amount, payload, bucket_names,
                                         book["risk_amount"] - book["realized_net_loss"] - book["exposure"], bucket_limits, now)
        if not reservation["approved"]:
            return {"approved": False, "reasons": [reservation["reason"]], "reason": reservation["reason"], "intent_id": iid}
        result = {"approved": True, "reasons": [], "request": request, "intent_id": iid, "risk": amount,
                  "volume": volume, "remaining_before": book["remaining"], "buckets": bucket_names}
        if rr_evidence is not None:
            result["minimum_rr_evidence"] = rr_evidence
        if scalp_limit is not None:
            result.update(scalp_limit)
        return result
