"""Evidence committee. Proposals are data; the independent risk authority acts.

No daily target or budget is accepted here. Entry standards cannot be weakened
because a target has not been reached.
"""
from __future__ import annotations

import math
import time
from typing import Any

from .strategies import REGISTRY

GROUPS = {"trend": "price_transform", "momentum": "price_transform", "volatility": "price_transform",
          "statistical": "price_transform", "structure": "price_structure", "candle": "price_structure",
          # Explicit compatibility alias used by an older broker-path fixture.
          # Any other undeclared group remains ineligible below.
          "candles": "price_structure", "volume": "volume_weighted", "interasset": "other_asset"}

AR_REASONS = {
    "no fresh completed and triggered entry setup": "انتظار: لا يوجد إعداد دخول مكتمل ومفعّل وحديث",
    "invalid trade direction": "اتجاه الصفقة غير صالح",
    "required news/calendar coverage missing, stale, or in event blackout": "التغطية المطلوبة للأخبار أو التقويم ناقصة أو قديمة، أو يقع الوقت داخل حظر حدث",
    "strategy lacks eligible chronological cost-adjusted broker OOS evidence": "الاستراتيجية لا تملك نتائج مؤهلة خارج العينة على بيانات الوسيط بعد التكاليف",
    "quant evidence version, instrument or timeframe mismatch": "نتائج التحقق الكمي لا تطابق الإصدار أو الرمز أو الفريم",
    "simulation evidence cannot qualify broker proposal": "بيانات المحاكاة لا تؤهل اقتراحاً للتنفيذ لدى الوسيط",
    "quant evidence lacks a valid past data timestamp": "وقت بيانات التحقق الكمي مفقود أو يقع في المستقبل",
    "quant certificate expired or has inconsistent check time": "شهادة التحقق الكمي منتهية أو وقت فحصها غير متسق",
    "timeframes disagree": "الفريمات تختلف في الاتجاه",
    "triggered schools disagree": "مدارس ذات إعداد دخول مفعّل تختلف في الاتجاه",
    "M1 directional evidence has no clear advantage": "أدلة الدقيقة لا ترجح اتجاهًا بوضوح",
    "fewer than two distinct evidence families after dependency grouping": "عدد عائلات الأدلة أقل من اثنتين بعد تجميع المؤشرات المترابطة",
    "need corroborating evidence on at least two completed timeframes": "يلزم دليل متوافق من فريمين مكتملين على الأقل",
    "missing or invalid execution prices": "أسعار الدخول أو الوقف أو الهدف ناقصة أو غير صالحة",
    "execution stop and target must bracket entry": "يجب أن يقع سعر الدخول بين الوقف والهدف في اتجاه الصفقة",
    "market eligibility, session or freshness failed": "فشل تأهيل السوق أو الجلسة أو حداثة البيانات",
    "spread exceeds 20 percent of proposed stop distance": "السبريد يتجاوز 20% من مسافة الوقف المقترح",
    "current quote outside approved entry zone": "السعر الحالي خارج منطقة الدخول المعتمدة",
    "triggered entry; distinct evidence families and timeframe agreement; required news and fixed OOS gates passed": "تحقق الدخول مع اتفاق الفريمات وعائلات أدلة مختلفة؛ اكتملت الأخبار المطلوبة واجتازت الاستراتيجية معايير خارج العينة الثابتة",
}


def _ar(reason):
    return f"{AR_REASONS.get(reason, reason)} ({reason})"


def _quant_for(card, quant_results):
    if isinstance(quant_results, list):
        matches = [q for q in quant_results if q.get("strategy_id") == card["id_strategy"] and
                   q.get("symbol") == card["symbol"] and q.get("timeframe") == card["timeframe"]]
        return matches[-1] if matches else {}
    if isinstance(quant_results, dict):
        key = f"{card['symbol']}:{card['timeframe']}:{card['id_strategy']}"
        return quant_results.get(key, quant_results.get(card["id_strategy"], {}))
    return {}


def decide(cards: list[dict], quant_results=None, news: dict | None = None, as_of: float | None = None,
           market: dict | None = None, portfolio: dict | None = None) -> dict:
    as_of = time.time() if as_of is None else float(as_of)
    forward_demo=(portfolio or {}).get("validation_policy")=="forward_demo"
    autonomous_fast=bool(forward_demo and (portfolio or {}).get('autonomous_fast') is True
                         and (portfolio or {}).get('decision_protocol')=='multi_school_v1')
    result: dict[str, Any] = {"decision": "WAIT", "proposals": [], "ranked": [], "reasons": [], "supporting": [], "opposing": [],
              "as_of": as_of, "expires_at": as_of, "formula": "أعلى درجة فقط لكل عائلة أدلة مترابطة؛ يلزم عائلتان على الأقل، ومعايير كمية ثابتة",
              "limitations": ["تجميع الأدلة يقلل العد المكرر للمؤشرات المترابطة ولا يثبت استقلالها الإحصائي"],
              "risk_authority": "محرك المخاطر المستقل يملك حق الرفض النهائي؛ اللجنة لا ترسل الأوامر"}
    fresh = []
    for raw in cards:
        c = dict(raw)
        # The registry's id initially identifies the strategy; cards' stable id
        # identifies a signal. The explicit strategy_id is authoritative.
        c["id_strategy"] = c.get("strategy_id", c.get("registry_id", c.get("strategy", "")))
        meta = REGISTRY.get(c["id_strategy"])
        registry_id = c.get("registry_id")
        declared_group = c.get("evidence_group")
        declared_family = GROUPS.get(declared_group) if isinstance(declared_group, str) else None
        registry_family = GROUPS.get(meta.get("evidence_group") or "") if meta else None
        # Cards are derived data, not the authority for implementation state.
        # A partial strategy must remain unable to vote even if a corrupted or
        # stale card claims IMPLEMENTED/READY and is paired with a forged
        # certificate. Unknown dependency groups also fail closed so a newly
        # named group cannot become an independent vote by accident.
        registry_eligible = bool(
            meta
            and meta.get("coverage") == "IMPLEMENTED"
            and c.get("coverage") == "IMPLEMENTED"
            and c.get("version") == meta.get("version")
            and (registry_id is None or registry_id == c["id_strategy"])
            and declared_family is not None
            and declared_family == registry_family
        )
        if (registry_eligible and meta is not None and c.get("status") in ("READY", "WAIT") and c.get("quality") == "VALIDATED_OHLC"
                and c.get("data_time") is not None and c["data_time"] <= as_of < c.get("expires_at", 0)):
            # Anchor all later dependency grouping to the registry declaration,
            # even when a known compatibility alias was used on the card.
            c["evidence_group"] = meta["evidence_group"]
            fresh.append(c)
    candidates = [c for c in fresh if c["status"] == "READY" and c.get("actionable") and (c.get("entry") or {}).get("triggered")]
    result['evidence_coverage'] = {
        'registered_models': len(REGISTRY),
        'present_models': len({c.get('strategy_id', c.get('registry_id')) for c in cards}),
        'fresh_eligible_cards': len(fresh),
        'directional_cards': sum(c.get('direction') in ('BUY', 'SELL') for c in fresh),
        'neutral_cards': sum(c.get('direction') not in ('BUY', 'SELL') for c in fresh),
        'excluded_cards': len(cards)-len(fresh),
        'missing_is_confirmation': False,
        'scope': 'card counts are disclosure, never independent votes or win probabilities',
    }
    if autonomous_fast:
        fresh=[c for c in fresh if c['timeframe']=='M1']
        candidates=[c for c in candidates if c['timeframe']=='M1']
        result['formula']='ترجيح عائلات أدلة الدقيقة؛ يلزم عائلتان ودعم يتجاوز المعارضة دون نسبة تصويت ثابتة؛ فحص التكلفة الصافية مستقل'
    if not candidates:
        result["reason_codes"] = ["no fresh completed and triggered entry setup"]
        result["reasons"] = [_ar("no fresh completed and triggered entry setup")]
        return result
    news = news or {}
    for candidate in candidates:
        reasons = []
        symbol, side = candidate["symbol"], candidate["direction"]
        if side not in ("BUY", "SELL"):
            reasons.append("invalid trade direction")
        requirements = candidate.get("news_requirements", ["calendar"])
        coverage = news.get("coverage", {})
        missing_sources = [r for r in requirements if not coverage.get(r, False)]
        if not news.get("ok") or news.get("blackout") or missing_sources:
            reasons.append("required news/calendar coverage missing, stale, or in event blackout")
        quant = _quant_for(candidate, quant_results)
        if forward_demo:
            pass  # Explicit Demo forward experiment; never fabricate a certificate.
        elif not quant.get("qualified"):
            reasons.append("strategy lacks eligible chronological cost-adjusted broker OOS evidence")
        elif (quant.get("strategy_id") != candidate["id_strategy"] or quant.get("version") != candidate.get("version")
                or quant.get("symbol") != symbol or quant.get("timeframe") != candidate["timeframe"]):
            reasons.append("quant evidence version, instrument or timeframe mismatch")
        elif quant.get("data_kind") not in ("broker", "broker_verified"):
            reasons.append("simulation evidence cannot qualify broker proposal")
        elif not isinstance(quant.get("data_time"), (int, float)) or not math.isfinite(quant["data_time"]) or quant["data_time"] > as_of:
            reasons.append("quant evidence lacks a valid past data timestamp")
        elif ("certificate_expires_at" in quant and (not isinstance(quant["certificate_expires_at"], (int, float))
                or not math.isfinite(quant["certificate_expires_at"]) or quant["certificate_expires_at"] <= as_of)) or ("checked_at" in quant and (not isinstance(quant["checked_at"], (int, float)) or not math.isfinite(quant["checked_at"])
                or not 0 <= as_of-quant["checked_at"] < 86400)):
            reasons.append("quant certificate expired or has inconsistent check time")
        peers = [c for c in fresh if c["symbol"] == symbol and c["direction"] in ("BUY", "SELL")]
        opposing = [c for c in peers if c["direction"] != side]
        # A WAIT card can describe directional context without an entry.  It
        # must not veto an otherwise corroborated proposal merely because one
        # of many schools labels another timeframe in the opposite direction.
        # Only a complete, actionable and triggered opposing setup is a real
        # conflict.  Supporting evidence still has to span two timeframes and
        # two dependency groups below, so this does not remove confirmation.
        triggered_opposing = [c for c in opposing if c.get("status")=="READY" and c.get("actionable")
                              and (c.get("entry") or {}).get("triggered")]
        if market is not None:
            tick=market.get("tick",{})
            def still_in_entry_zone(c, tick=tick):
                quote=tick.get("ask" if c["direction"]=="BUY" else "bid")
                zone=(c.get("entry") or {}).get("zone")
                # Missing/invalid quote data must not silently remove a veto.
                if not isinstance(quote,(int,float)) or not math.isfinite(quote):return True
                if not isinstance(zone,(list,tuple)) or len(zone)!=2:return True
                if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in zone):return True
                return zone[0]<=quote<=zone[1]
            # A historical trigger whose executable quote has left its entry
            # zone remains visible as opposing context, but cannot veto entry.
            triggered_opposing=[c for c in triggered_opposing if still_in_entry_zone(c)]
        if not autonomous_fast and any(c["timeframe"] != candidate["timeframe"] for c in triggered_opposing):
            reasons.append("timeframes disagree")
        if triggered_opposing and not autonomous_fast:
            reasons.append("triggered schools disagree")
        supporting = [c for c in peers if c["direction"] == side]
        independent: dict[str, float] = {}
        for c in supporting:
            group = GROUPS[c["evidence_group"]]
            active=c.get('actionable') and c.get('status')=='READY' and (market is None or still_in_entry_zone(c))
            weight=.5 if autonomous_fast and not active else 1.
            independent[group] = max(independent.get(group, 0), c.get("score", 0)*weight)
        # Waiting trend direction is context, but only explicit met conditions
        # contribute quality. A direction label by itself is insufficient.
        independent = {group: score for group, score in independent.items() if score > 0}
        if len(independent) < 2:
            reasons.append("fewer than two distinct evidence families after dependency grouping")
        directions_by_tf = {c["timeframe"] for c in supporting if c.get("conditions_met")}
        if autonomous_fast:
            opposite_groups: dict[str, float] = {}
            for c in opposing:
                if not c.get('conditions_met'):continue
                weight=1. if c in triggered_opposing else .5
                group=GROUPS[c['evidence_group']]
                opposite_groups[group]=max(opposite_groups.get(group,0),c.get('score',0)*weight)
            if sum(independent.values())<=sum(opposite_groups.values()):
                reasons.append('M1 directional evidence has no clear advantage')
        elif len(directions_by_tf) < 2:
            reasons.append("need corroborating evidence on at least two completed timeframes")
        entry = candidate["entry"]["price"]
        sl = (candidate.get("stop") or {}).get("price")
        tp = candidate.get("targets", [{}])[0].get("price") if candidate.get("targets") else None
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in (entry, sl, tp)):
            reasons.append("missing or invalid execution prices")
        elif not (sl < entry < tp if side == "BUY" else tp < entry < sl):
            reasons.append("execution stop and target must bracket entry")
        if market is not None:
            if market.get("eligible") is False or market.get("open") is False or market.get("stale"):
                reasons.append("market eligibility, session or freshness failed")
            spread = market.get("spread", market.get("spread_price"))
            if not autonomous_fast and isinstance(spread, (int, float)) and sl is not None and spread > .2*abs(entry-sl):
                reasons.append("spread exceeds 20 percent of proposed stop distance")
            tick = market.get("tick", {})
            quote = tick.get("ask" if side == "BUY" else "bid")
            if quote is not None and not candidate["entry"]["zone"][0] <= quote <= candidate["entry"]["zone"][1]:
                reasons.append("current quote outside approved entry zone")
        score = sum(independent.values())/len(independent) if independent else 0.0
        record = {"card_id": candidate["id"], "strategy_id": candidate["id_strategy"], "symbol": symbol,
                  "side": side, "score": round(score, 2), "evidence_families": independent,
                  "supporting": [c["id"] for c in supporting], "opposing": [c["id"] for c in opposing],
                  "reason_codes": reasons, "reasons": [_ar(r) for r in reasons], "eligible": not reasons}
        if autonomous_fast:
            record['directional_evidence']={'support':sum(independent.values()),
                'opposition':sum(opposite_groups.values()),
                'net':sum(independent.values())-sum(opposite_groups.values()),
                'policy':'strict_family_net_advantage_no_fixed_vote_percentage',
                'family_balance': {group:{'support':independent.get(group,0),
                                          'opposition':opposite_groups.get(group,0),
                                          'net':independent.get(group,0)-opposite_groups.get(group,0)}
                                   for group in sorted(set(independent)|set(opposite_groups))}}
        result["ranked"].append(record)
        if reasons:
            continue
        expiry = min([candidate["expires_at"]]+[c["expires_at"] for c in supporting])
        result["proposals"].append({"id": candidate["id"], "symbol": symbol, "side": side,
                    "strategy_id": candidate["id_strategy"], "strategy_version": candidate["version"],
                    "timeframe": candidate["timeframe"], "entry": entry, "entry_zone": candidate["entry"]["zone"],
                    "sl": sl, "tp": tp, "invalidation": candidate["invalidation"], "targets": candidate["targets"],
                    "execution_plan": candidate["execution_plan"], "data_time": candidate["data_time"],
                    "expires_at": expiry, "qualified": not forward_demo, "news_ok": True, "score": round(score, 2),
                    "validation_policy":"forward_demo" if forward_demo else "historical",
                    "signal_validated":True,
                    "evidence_group": candidate["evidence_group"], "card_ids": record["supporting"],
                    "evidence": candidate["evidence"], "quant_metrics": quant.get("metrics", {}),
                    "reason": "اختبار أمامي تجريبي بإشارة استراتيجية؛ التأهيل التاريخي غير مشترط" if forward_demo else _ar("triggered entry; distinct evidence families and timeframe agreement; required news and fixed OOS gates passed")})
    result["ranked"].sort(key=lambda x: (-x["score"], x["symbol"], x["strategy_id"]))
    result["proposals"].sort(key=lambda x: (-x["score"], -(x["quant_metrics"].get("expectancy_r") or 0), x["symbol"]))
    if result["proposals"]:
        best = result["proposals"][0]
        result.update(decision=best["side"], expires_at=best["expires_at"], supporting=best["card_ids"],
                      reasons=[best["reason"]], **{k: best[k] for k in ("symbol", "side", "entry", "sl", "tp")})
    else:
        result.update(decision="REJECT", reasons=sorted({reason for r in result["ranked"] for reason in r["reasons"]}),
                      reason_codes=sorted({reason for r in result["ranked"] for reason in r["reason_codes"]}),
                      opposing=sorted({id for r in result["ranked"] for id in r["opposing"]}))
    return result
