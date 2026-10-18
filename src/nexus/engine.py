"""Local institution coordinator; broker I/O is serialized in one worker."""
from __future__ import annotations

import concurrent.futures
import copy
import ctypes
import hashlib
import json
import logging
import math
import os
import queue
import secrets
import shutil
import sqlite3
import threading
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from . import __version__, confluence, scalping
from .broker import TIMEFRAMES, BrokerError, MT5Broker, SimBroker
from .committee import decide
from .execution import Executor
from .learning import LEARNING_SOURCE_MODULES, LearningMemory, digest, load_library
from .market import UniverseScanner, spread_filter_required
from .multischool import MultiSchoolMixin
from .news import NewsManager
from .quant import walk_forward
from .risk import (
    RiskManager,
    cashflow_records,
    cost_uncertainties,
    protocol_certificate_hash,
)
from .store import Store, account_key, utc_day
from .strategies import (
    REGISTRY,
    analyze_all,
    configured_minimum,
    configured_profile_revision,
    registry_manifest,
    validate_bars,
)
from .valuation import evaluate as evaluate_valuation

DECISION_TIMEFRAMES = ("M1", "M5", "M15", "H1", "H4")
PLAN_VERSION = "closed-bar-calendar-v3"
ACTION_RESULT_TTL = 600
ACTION_RESULT_LIMIT = 128
FAST_BATCH_LIMIT = 32
FAST_BATCH_SECONDS = 1.
FAST_BACKGROUND_SECONDS = 120.
FAST_PUBLISH_SECONDS = 5.
FAST_SCAN_BATCH_LIMIT = 32
FAST_SCAN_SECONDS = .5


class _PriorityYield(Exception):
    """Return to the command queue between serialized broker reads."""


def _analysis_bar_count(timeframe):
    """Provide every chart agent with at least one complete UTC-day context.

    Three extra completed bars cover boundary/alignment differences without
    allowing the current unfinished MT5 bar into research.
    """
    return max(300, max(configured_minimum(sid) for sid in REGISTRY), math.ceil(86400 / TIMEFRAMES[timeframe]) + 3)

LOG = logging.getLogger("nexus")


def resources():
    result={"os":os.name,"logical_cpus":os.cpu_count(),"local_language_model":"غير مثبت؛ التحليل الحسابي لا يحتاج خدمة ذكاء اصطناعي مدفوعة"}
    if os.name=="nt":
        class Memory(ctypes.Structure):
            _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in ("total_physical","available_physical","total_page","available_page","total_virtual","available_virtual","extended")]
        mem=Memory();mem.length=ctypes.sizeof(mem)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
            result.update(total_memory_gb=round(mem.total_physical/2**30,2),available_memory_gb=round(mem.available_physical/2**30,2))
    return result


class ResearchCache:
    def __init__(self,path):
        self.db=sqlite3.connect(str(path),check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS research(key TEXT PRIMARY KEY,at REAL,payload TEXT)")
        self.db.commit()
    def put(self,key,payload):
        self.db.execute("INSERT OR REPLACE INTO research VALUES(?,?,?)",(key,time.time(),json.dumps(payload,ensure_ascii=False,allow_nan=False)));self.db.commit()
    def get(self,key,max_age=86400):
        row=self.db.execute("SELECT at,payload FROM research WHERE key=?",(key,)).fetchone()
        return json.loads(row[1]) if row and 0<=time.time()-row[0]<max_age else None


def _verified_learning_export_reference(root):
    learning_reference=root/"docs/knowledge/learning-reference.json"
    if not learning_reference.exists():
        return None
    reference=json.loads(learning_reference.read_text(encoding="utf-8"))
    claimed=reference.pop("revision",None)
    modules=reference.get("source_modules",{})
    if (digest(reference)!=claimed or set(modules) not in ({"learning.py","risk.py","store.py"},{"learning.py","learning_journal.py","risk.py","store.py"},set(LEARNING_SOURCE_MODULES))
            or any(hashlib.sha256(module["source_python"].encode()).hexdigest()!=module["sha256"]
                   for module in modules.values())):
        raise ValueError("Learning reference fingerprint mismatch")
    return {**reference,"revision":claimed}


class Engine(MultiSchoolMixin):
    def __init__(self,app_root,data_dir,clock=time.time):
        self.root=Path(app_root);self.data=Path(data_dir);self.data.mkdir(parents=True,exist_ok=True)
        self.clock=clock; self.broker=None;self.store=None;self.risk=None;self.executor=None;self.scanner=None
        self.news=NewsManager(self.data/"news.sqlite3",clock,external_feeds=False)
        self.cache=ResearchCache(self.data/"research.sqlite3")
        self.commands=queue.Queue();self.running=False;self.thread=None;self.view_lock=threading.Lock()
        self._json_view_lock=threading.Lock();self._json_view_ref=None;self._json_view_bytes=None
        self._action_result_lock=threading.Lock();self._action_results={};self._action_result_clock=time.monotonic
        self.ever_started=False
        self.analysis_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix="quant-research")
        self.research_cancel=threading.Event()
        self.pending_quant={};self.quant_results={};self.cards_by_symbol={};self.decisions={};self.opportunities=[];self.manual={}
        self.deep_queue=[];self.last_deep=0;self.last_scan=0;self.generation=0;self.attempted={}
        self.last_reconnect_attempt=0
        self.chart={"symbol":"","timeframe":"H1","bars":[],"cards":[]}
        self.settings={};self.research_costs={};self.status="DISCONNECTED";self.error="";self.last_update=0
        self.context_cache={};self.partner_catalog=None
        self.valuation={};self.learning_account=None
        self.learner=None;self.last_learning=0;self.learning_state={"mode":"UNAVAILABLE","error":"","models":[]};self.library_error=""
        try:self.rule_library=load_library(self.root)
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            self.rule_library={};self.library_error=str(exc);self.learning_state["error"]=str(exc)
        try:
            from .school_catalog import catalog
            self.knowledge=catalog(self.root)
        except (ImportError,OSError,ValueError):self.knowledge={"schools":[],"error":"Catalog unavailable"}
        self.knowledge["catalog_revision"]=digest(self.knowledge)
        self.knowledge["library_rules"]=len(self.rule_library)
        self.config_path=self.data/"config.json"
        try:
            self.config=json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError,ValueError):
            self.config={}
        self.scalping_state={};self.execution_reference=None;self.execution_reference_error=""
        self._fast_monotonic=time.monotonic;self._reset_fast_scheduler()
        self._load_execution_reference()
        self._view=self._empty_state()

    def _empty_state(self):
        return {"app_name":"Quant Trading AI","version":__version__,"simulation":False,"mode":"READ_ONLY","status":self.status,"error":self.error,
                "account":None,"terminal":None,"settings":{},"risk":{},"scan":{"rows":[],"discovered":0,"checked":0,"eligible":0,"excluded":0,"complete":False},
                "opportunities":[],"cards":[],"news":{"sources":[],"items":[],"calendar":{},"coverage":{}},
                "positions":[],"orders":[],"intents":[],"events":[],"performance":{"rows":[]},"coverage":registry_manifest(),
                "chart":self.chart,"resources":resources(),"quant_results":[],"last_update":0,
                "knowledge":self.knowledge,"learning":self.learning_state,
                "valuation":self.valuation,"scalping":self.scalping_state,
                "execution_reference":self._execution_reference_summary(),
                "fast_scheduler":self._fast_scheduler_snapshot(),
                "day_boundary":"00:00 UTC / 04:00 Asia/Dubai","setup":self.config,
                "acceptance":"القبول النهائي لم يجتز بعد؛ راجع تقرير التحقق المرفق."}

    def start_worker(self,auto_connect=True):
        with self._action_result_lock:self.running=True;self.ever_started=True
        self.thread=threading.Thread(target=self._loop,name="nexus-coordinator",daemon=True);self.thread.start()
        if auto_connect:
            self.commands.put(({"action":"connect",**self.config},None))
        self.news.refresh()

    def stop_worker(self):
        with self._action_result_lock:self.running=False
        self.research_cancel.set()
        # Revoke before waiting for outstanding analysis. Otherwise a cycle
        # that finishes during join() could still enter after the window closes.
        if self.executor:self.executor.deactivate("إغلاق التطبيق؛ يلزم إعادة التفعيل")
        self._reject_pending_actions()
        if self.thread:self.thread.join(timeout=5)
        self.analysis_pool.shutdown(wait=False,cancel_futures=True)
        if self.executor:self.executor.deactivate("إغلاق التطبيق؛ يلزم إعادة التفعيل")
        if self.broker:self.broker.close()

    def snapshot(self):
        # The public state is a JSON document. Parsing its immutable bytes is
        # much cheaper than recursively copying thousands of Python cards, and
        # callers (including diagnostics) still receive a detached document.
        return json.loads(self.snapshot_json())

    @staticmethod
    def _encode_view(view):
        return json.dumps(view,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')

    def snapshot_json(self):
        # Never serialize while holding the coordinator's publication lock.
        # Serialize each immutable publication once for concurrent UI polls.
        with self._json_view_lock:
            with self.view_lock:
                view=self._view
                if self._json_view_ref is view:return self._json_view_bytes
            raw=self._encode_view(view)
            with self.view_lock:
                if self._view is view:
                    self._json_view_ref=view;self._json_view_bytes=raw
            return raw

    def _invalidate_research(self):
        self._multi_card_cache={}
        # Old account/cost generations must not occupy the only research worker.
        self.research_cancel.set()
        for future,_,_ in self.pending_quant.values():future.cancel()
        self.pending_quant.clear()
        self.research_cancel=threading.Event()
        self.generation+=1
        if hasattr(self,"_fast_metrics"):self._reset_fast_scheduler()

    def action(self,payload,timeout=12):
        if not isinstance(payload,dict) or payload.get("action") not in {"connect","simulation","scan","start","stop","cancel","flatten","approve","chart","diagnostics","knowledge_export","fundamental_analyze","backtest","install_bridge","refresh","reconcile","shutdown"}:
            raise ValueError("إجراء غير معروف")
        with self._action_result_lock:
            if not self.running:
                if self.ever_started:raise ValueError("الخدمة توقفت؛ أعد تشغيل التطبيق")
                direct=True
            else:
                direct=False
                self._prune_action_results()
                if len(self._action_results)>=ACTION_RESULT_LIMIT:
                    raise ValueError("قائمة الإجراءات ممتلئة؛ لم يُرسل هذا الإجراء")
                future=concurrent.futures.Future();request_id=secrets.token_hex(16)
                while request_id in self._action_results:request_id=secrets.token_hex(16)
                future._nexus_request_id=request_id
                command=copy.deepcopy(payload)
                self._action_results[request_id]={"future":future,"completed_at":None,"result":None}
                self.commands.put((command,future))
        if direct:return self._action(payload)
        try:result=future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            if not future.done():
                return {"ok":True,"queued":True,"status":"PENDING","request_id":request_id,
                        "message":"الإجراء في قائمة العمل؛ انتظر نتيجته باستخدام معرّف الطلب."}
            # A command's own TimeoutError is a completed error, not a reason
            # to acknowledge another submission or repeat broker operations.
            try:return future.result()
            finally:self._forget_action_result(request_id)
        except BaseException:
            self._forget_action_result(request_id);raise
        self._forget_action_result(request_id)
        return result

    def _prune_action_results(self):
        """Caller holds the result lock; unfinished work never expires."""
        now=self._action_result_clock()
        for request_id,entry in list(self._action_results.items()):
            completed=entry["completed_at"]
            if completed is not None and now-completed>=ACTION_RESULT_TTL:
                del self._action_results[request_id]

    def _forget_action_result(self,request_id):
        # Immediate responses need no retained ID and free their capacity.
        # An interrupted waiter must not erase work still in the coordinator.
        with self._action_result_lock:
            entry=self._action_results.get(request_id)
            if entry is not None and entry["completed_at"] is not None:
                del self._action_results[request_id]

    def _claim_worker_step(self,future=None):
        """Order dispatch against shutdown without holding a lock during I/O."""
        with self._action_result_lock:
            if not self.running:return False
            if future is not None:
                if future.done() or future.running():return False
                return future.set_running_or_notify_cancel()
            return True

    def _settle_action(self,future,result=None,error=None):
        """Freeze the final response before notifying a waiting API caller."""
        if future is None:return
        final={"ok":False,"error":str(error),"message":str(error)} if error is not None else copy.deepcopy(result)
        with self._action_result_lock:
            if future.done():return
            entry=self._action_results.get(getattr(future,"_nexus_request_id",None))
            if entry is not None and entry["future"] is future:
                entry.update(result=final,completed_at=self._action_result_clock())
            if error is not None:future.set_exception(error)
            else:future.set_result(result)

    def action_result(self,request_id):
        """Protected API lookup only: never submit, replay or authorize work."""
        invalid={"ok":False,"error":"معرّف الإجراء غير موجود أو انتهت مدة حفظ نتيجته",
                 "message":"معرّف الإجراء غير موجود أو انتهت مدة حفظ نتيجته"}
        if not isinstance(request_id,str) or len(request_id)!=32 or any(c not in "0123456789abcdef" for c in request_id):
            return invalid
        with self._action_result_lock:
            self._prune_action_results()
            entry=self._action_results.get(request_id)
            if entry is None:return invalid
            return {"ok":True,"status":"PENDING" if entry["completed_at"] is None else "COMPLETE",
                    "result":copy.deepcopy(entry["result"])}

    def _reject_pending_actions(self):
        """Reject never-started commands on stop; active I/O keeps its result."""
        while True:
            try:_payload,future=self.commands.get_nowait()
            except queue.Empty:return
            self._settle_action(future,error=ValueError("الخدمة توقفت قبل تنفيذ الإجراء؛ لم يُنفذ"))

    def _audit(self,event,payload):
        if self.store:self.store.audit(event,payload)
        LOG.info("%s %s",event,json.dumps(payload,ensure_ascii=False,default=str))

    def _execution_tables(self):
        if not self.store:return
        with self.store.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS execution_reference_versions(revision TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS scalp_sessions(account_key TEXT NOT NULL,day TEXT NOT NULL,variant TEXT NOT NULL,session_id TEXT NOT NULL,target REAL NOT NULL,latched INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL,PRIMARY KEY(account_key,day,variant))")

    def _load_execution_reference(self,required=False):
        """Verify the shipped definitions and inert source archive before use."""
        try:
            reference=json.loads((self.root/"docs/knowledge/execution-reference.json").read_text(encoding="utf-8"))
            claimed=reference.pop("revision",None)
            modules=reference.get("source_modules",{})
            expected={"confluence.py","confluence_registry.py","scalping.py","risk.py","execution.py","engine.py"}
            if (reference.get("schema")!=1 or reference.get("decision_protocol")!="four_school_v1"
                    or digest(reference)!=claimed or set(modules)!=expected
                    or reference.get("protocol_definition")!=confluence.definition()
                    or reference.get("scalp_definition")!={**scalping.POLICY_DEFINITION,"revision":scalping.POLICY_REVISION}):
                raise ValueError("Execution reference definition or fingerprint mismatch")
            for name,module in modules.items():
                source=module["source_python"].encode("utf-8")
                local=(self.root/"src/nexus"/name).read_bytes()
                if (hashlib.sha256(source).hexdigest()!=module.get("sha256")
                        or hashlib.sha256(local).hexdigest()!=module.get("sha256")):
                    raise ValueError("Execution reference source mismatch: "+name)
            self.execution_reference={**reference,"revision":claimed};self.execution_reference_error=""
            if self.store:
                self._execution_tables()
                with self.store.transaction() as db:
                    db.execute("INSERT OR IGNORE INTO execution_reference_versions VALUES(?,?)",(claimed,json.dumps(self.execution_reference,ensure_ascii=False,allow_nan=False)))
            return self.execution_reference
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.execution_reference=None;self.execution_reference_error=str(exc)
            if required:raise ValueError("Strict activation requires a verified execution reference: "+str(exc)) from exc
            return None

    def _execution_reference_summary(self):
        reference=self.execution_reference or {}
        return {"verified":bool(reference),"revision":reference.get("revision"),
                "protocol_revision":confluence.PROTOCOL_REVISION,"scalp_policy_revision":scalping.POLICY_REVISION,
                "source_modules":sorted(reference.get("source_modules",{})),"error":self.execution_reference_error}

    @staticmethod
    def _validate_scalping(payload):
        if not isinstance(payload,dict) or set(payload)-{"normal","fast"}:
            raise ValueError("Scalping profiles must contain normal and fast settings")
        result={}
        for variant in ("normal","fast"):
            raw=payload.get(variant,{})
            if not isinstance(raw,dict) or raw.get("variant",variant)!=variant:
                raise ValueError("Scalp profile variant mismatch")
            result[variant]=scalping.validate_scalp_settings(raw.get("enabled",False),raw.get("target_value"),
                raw.get("risk_percent"),variant,min_reward_risk=raw.get("min_reward_risk",2),profit_percent=raw.get("profit_percent"))
        if sum(v["enabled"] for v in result.values())>1:
            raise ValueError("Only one scalp variant may be enabled")
        return result

    def _check_scalp_targets(self,profiles):
        self._execution_tables();key=account_key(self.broker.account());day=utc_day(self.clock())
        with self.store.lock:
            for variant,settings in profiles.items():
                row=self.store.db.execute("SELECT target FROM scalp_sessions WHERE account_key=? AND day=? AND variant=?",(key,day,variant)).fetchone()
                if settings["enabled"] and row and settings["target_value"]>row["target"]:
                    raise ValueError("Today's authorized scalp target may only be lowered")

    def _authorize_scalping(self,profiles):
        key=account_key(self.broker.account());day=utc_day(self.clock())
        with self.store.transaction() as db:
            for variant,settings in profiles.items():
                if not settings["enabled"]:continue
                row=db.execute("SELECT * FROM scalp_sessions WHERE account_key=? AND day=? AND variant=?",(key,day,variant)).fetchone()
                if row:
                    if settings["target_value"]>row["target"]:raise ValueError("Today's scalp target cannot increase")
                    db.execute("UPDATE scalp_sessions SET target=? WHERE account_key=? AND day=? AND variant=?",(settings["target_value"],key,day,variant))
                else:
                    db.execute("INSERT INTO scalp_sessions VALUES(?,?,?,?,?,0,?)",(key,day,variant,secrets.token_hex(16),settings["target_value"],self.clock()))
        self._refresh_scalping()

    def _refresh_scalping(self):
        """Read owned fills and persist a reached goal; no entry reservation."""
        if not self.store or not self.broker:return self.scalping_state
        self._execution_tables();now=self.clock();key=account_key(self.broker.account());day=utc_day(now)
        profiles=self.settings.get("scalping",self.config.get("scalping",{}))
        profiles=self._validate_scalping(profiles)
        intents=self.store.intents(key);positions=self.broker.positions();state={}
        for variant,settings in profiles.items():
            with self.store.lock:
                row=self.store.db.execute("SELECT * FROM scalp_sessions WHERE account_key=? AND day=? AND variant=?",(key,day,variant)).fetchone()
            session_id=row["session_id"] if row else None;latched=bool(row and row["latched"])
            entries=[i for i in intents if i["kind"]=="ENTRY" and
                i.get("payload",{}).get("proposal",{}).get("scalp_session_id")==session_id and session_id]
            since=max(0,min((i["created"] for i in entries),default=int(now//86400)*86400)-60) if entries else int(now//86400)*86400
            try:
                deals=self.broker.deals(since)
                if deals is None:raise ValueError("Scalp broker history unavailable")
                reserves={}
                if self.risk and self.risk.settings:
                    for position in positions:
                        owner=self.risk._owned_intent(position,intents)
                        if owner and owner["id"] in {i["id"] for i in entries}:
                            symbol=position["symbol"];volume=float(position["volume"]);info=self.broker.symbol(symbol)
                            tick=self.broker.tick(symbol);side="BUY" if position["type"]==0 else "SELL"
                            price=tick["bid"] if side=="BUY" else tick["ask"]
                            slip=self.risk.settings["slippage_points"]*info["point"]
                            adverse=price-slip if side=="BUY" else price+slip
                            reserve=volume*self.risk._commission(symbol)/2+abs(self.broker.calc_profit(side,symbol,volume,price,adverse))
                            reserves[owner["id"]]=reserves.get(owner["id"],0)+reserve
                progress=scalping.snapshot(key,intents,deals,positions,settings,session_id=session_id,
                    closing_reserve_by_intent=reserves,latched=latched)
                if progress["should_latch"]:
                    with self.store.transaction() as db:
                        db.execute("UPDATE scalp_sessions SET latched=1 WHERE account_key=? AND day=? AND variant=?",(key,day,variant))
                    latched=True
                    self._audit("SCALP_TARGET_LATCHED",{"variant":variant,"session_id":session_id,"target":row["target"],"progress_net":progress["progress_net"]})
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                progress={"progress_net":None,"progress_valid":False,"entries_allowed":False,"latched":latched,"cost_uncertainty":[str(exc)]}
            state[variant]={"settings":settings,"progress":progress,"session_id":session_id,"latched":latched}
        if account_key(self.broker.account())!=key:raise ValueError("Account changed during scalp history fetch")
        self.scalping_state=state
        return state

    def _scalp_variant(self,tf):
        for variant,settings in self.settings.get("scalping",{}).items():
            if settings.get("enabled") and tf in scalping.policy_definition(variant)["timeframes"]:return variant
        return None

    def _scalp_entry_guard(self,proposal):
        if proposal.get("execution_style")!="SCALP":return
        state=self._refresh_scalping().get(proposal.get("scalp_variant"),{})
        if (state.get("session_id")!=proposal.get("scalp_session_id") or
                not state.get("progress",{}).get("entries_allowed")):
            raise ValueError("Scalp session goal, ownership or progress gate stopped new entries")

    def _formation_used(self,symbol,tf,formation_id,proposal_id=None):
        if not self.store:return False
        key=account_key(self.broker.account())
        for intent in self.store.intents(key):
            original=intent.get("payload",{}).get("proposal",{})
            if (intent["kind"]=="ENTRY" and original.get("symbol")==symbol and original.get("timeframe")==tf
                    and original.get("formation_id")==formation_id and original.get("id")!=proposal_id):
                return True
        return False

    def _reset_fast_scheduler(self):
        self._fast_symbols=();self._fast_cursor=0;self._fast_seen=set();self._fast_checked={};self._fast_bar_cache={}
        self._fast_sweep_started=None;self._fast_background_job=None;self._fast_background_at=0.;self._fast_publish_at=0.
        self._fast_metrics={"timeframe":"M1","single_worker":True,"batch_limit":FAST_BATCH_LIMIT,
            "time_budget_seconds":FAST_BATCH_SECONDS,"background_interval_seconds":FAST_BACKGROUND_SECONDS,
            "scan_batch_limit":FAST_SCAN_BATCH_LIMIT,"scan_time_budget_seconds":FAST_SCAN_SECONDS,
            "budget_semantics":"checked_between_symbols_broker_reads_may_overrun",
            "symbols_total":0,"verified_eligible":0,"checked_in_sweep":0,"sweep_count":0,
            "last_sweep_seconds":None,"last_batch_seconds":None,"max_batch_seconds":0.,
            "last_checked_at":None,"last_ready_at":None,"observed_revisit_seconds":None,
            "max_observed_revisit_seconds":None,"evaluations":0,"ready_rechecks":0,
            "skipped_unchanged_bar":0,"skipped_unverified":0,"skipped_commands":0,
            "skipped_time_budget":0,"budget_overruns":0,"errors":0,"background_steps":0,
            "last_background_step_seconds":None}

    def _fast_enabled(self):
        settings=getattr(self,"settings",{})
        return bool(settings.get("decision_protocol") in ("four_school_v1","multi_school_v1") and
            settings.get("scalping",{}).get("fast",{}).get("enabled") and self.executor and
            getattr(self.executor,"mode","READ_ONLY") in ("AUTO_DEMO","MANUAL_DEMO"))

    def _fast_scheduler_snapshot(self):
        return {**copy.deepcopy(self._fast_metrics),"enabled":self._fast_enabled()}

    def _priority_yield_requested(self):
        return not self.running or not self.commands.empty()

    def _fast_full_context(self,symbol):
        bars={}
        for tf in DECISION_TIMEFRAMES:
            if self._priority_yield_requested():raise _PriorityYield()
            bars[tf]=self.broker.bars(symbol,tf,_analysis_bar_count(tf))
        if self._priority_yield_requested():raise _PriorityYield()
        info=self.broker.symbol(symbol);session=self.broker.session(symbol);calendar=self.broker.calendar()
        tick=self.broker.tick(symbol);now=self.clock()
        gate=self.news.gate(info,calendar,self.broker.is_simulation,now)
        market={"eligible":bool(self.scanner.rows.get(symbol,{}).get("eligible")),"open":bool(session.get("open")),
            "stale":not 0<=now-tick["time"]<=15,"spread":tick["ask"]-tick["bid"],"tick":tick}
        evaluations={}
        for tf,book in bars.items():
            if self._priority_yield_requested():raise _PriorityYield()
            evaluations[tf]=confluence.evaluate(symbol,tf,book,now,info["trade_tick_size"],quote=tick)
        return evaluations,gate,market,now,bars

    def _fast_commit_decision(self,symbol,result):
        """Replace M1 evidence without accelerating unrelated BASE entries."""
        old=self.decisions.get(symbol,{})
        now=self.clock();fresh=result.get("proposals",[])
        base=[p for p in old.get("proposals",[]) if p.get("timeframe")!="M1" and p.get("expires_at",0)>now]
        if fresh:base=[p for p in base if p["side"]==fresh[0]["side"]]
        matrices={**old.get("decision_matrices",{}),**result.get("decision_matrices",{})}
        reasons={**old.get("protocol_reasons",{}),**result.get("protocol_reasons",{})}
        proposals=fresh+base
        result={**result,"proposals":proposals,"decision_matrices":matrices,"protocol_reasons":reasons,
            "ranked":result.get("ranked",[])+[r for r in old.get("ranked",[]) if r.get("timeframe")!="M1"]}
        if proposals:result.update(decision=proposals[0]["side"],expires_at=max(p["expires_at"] for p in proposals))
        self.decisions[symbol]=result

    def _fast_analyze_symbol(self,symbol):
        """Pure M1 prescreen with exactly the normal strict history window."""
        if self.settings.get("decision_protocol")=="multi_school_v1":return self._multi_analyze_symbol(symbol)
        if self._priority_yield_requested():raise _PriorityYield()
        info=self.broker.symbol(symbol);bars=self.broker.bars(symbol,"M1",_analysis_bar_count("M1"))
        if self._priority_yield_requested():raise _PriorityYield()
        fingerprint=digest([{k:row.get(k) for k in ("time","open","high","low","close")} for row in bars])
        cached=self._fast_bar_cache.get(symbol)
        if cached and cached["fingerprint"]==fingerprint and cached["static_wait"]:
            evaluation=copy.deepcopy(cached["evaluation"]);now=self.clock()
            self._fast_metrics["skipped_unchanged_bar"]+=1
        else:
            tick=self.broker.tick(symbol);now=self.clock()
            evaluation=confluence.evaluate(symbol,"M1",bars,now,info["trade_tick_size"],quote=tick)
            self._fast_metrics["evaluations"]+=1
            static_codes={"INSUFFICIENT_HISTORY","ICT_CHAIN_INCOMPLETE","ICT_OPPOSITION","TIMING_NOT_ALIGNED",
                "MOMENTUM_UNAVAILABLE","ELLIOTT_UNAVAILABLE","MOMENTUM_OPPOSES","ELLIOTT_OPPOSES"}
            codes=set(evaluation.get("reason_codes",[]))
            # Quote, zone, gross/net RR and READY results are deliberately never
            # cached as WAIT: the executable quote may change within one bar.
            self._fast_bar_cache[symbol]={"fingerprint":fingerprint,"evaluation":copy.deepcopy(evaluation),
                "static_wait":bool(codes) and codes<=static_codes and evaluation.get("status")!="READY"}
        if evaluation.get("status")=="READY" and evaluation.get("execution_ready"):
            self._fast_metrics["ready_rechecks"]+=1;self._fast_metrics["last_ready_at"]=now
            evaluations,gate,market,now,_books=self._fast_full_context(symbol)
            if self._priority_yield_requested():raise _PriorityYield()
            cards=self.cards_by_symbol.get(symbol,[])
            result=self._strict_decision(symbol,evaluations,cards,gate,now,market,proposal_timeframes={"M1"})
            if self._priority_yield_requested():raise _PriorityYield()
        else:
            matrix=copy.deepcopy(evaluation["matrix"]);matrix["status"]="WAIT"
            result={"symbol":symbol,"decision":"WAIT","proposals":[],"ranked":[],"as_of":now,"expires_at":now,
                "decision_protocol":"four_school_v1","protocol_revision":confluence.PROTOCOL_REVISION,
                "decision_matrices":{"M1":matrix},"protocol_reasons":{"M1":copy.deepcopy(evaluation.get("reasons",[]))},
                "reasons":[r["ar"] for r in evaluation.get("reasons",[])]}
        self._fast_commit_decision(symbol,result)
        return bool(result.get("proposals"))

    def _run_fast_batch(self):
        """Fair, bounded batches; all broker I/O stays on the coordinator."""
        if not self._fast_enabled():return False
        metrics=self._fast_metrics;started=self._fast_monotonic();ready=False
        names=tuple(sorted(name for name,row in self.scanner.rows.items() if row.get("checked") and row.get("eligible")))
        metrics.update(symbols_total=len(self.scanner.rows),verified_eligible=len(names))
        metrics["skipped_unverified"]+=len(self.scanner.rows)-len(names)
        if names!=self._fast_symbols:
            previous=self._fast_symbols[self._fast_cursor%len(self._fast_symbols)] if self._fast_symbols else None
            had_symbols=bool(self._fast_symbols)
            self._fast_symbols=names;self._fast_cursor=names.index(previous) if previous in names else 0
            # A refreshed market list must not erase progress through symbols
            # that remain eligible. New symbols join this round; removed ones
            # no longer delay completion.
            self._fast_seen.intersection_update(names)
            if not had_symbols or self._fast_sweep_started is None:self._fast_sweep_started=started
        for _ in range(min(FAST_BATCH_LIMIT,len(names))):
            if self._priority_yield_requested():metrics["skipped_commands"]+=1;break
            if self._fast_monotonic()-started>=FAST_BATCH_SECONDS:metrics["skipped_time_budget"]+=1;break
            symbol=names[self._fast_cursor];self._fast_cursor=(self._fast_cursor+1)%len(names)
            checked=self._fast_monotonic();previous=self._fast_checked.get(symbol)
            if previous is not None:
                revisit=max(0.,checked-previous);metrics["observed_revisit_seconds"]=revisit
                metrics["max_observed_revisit_seconds"]=max(revisit,metrics["max_observed_revisit_seconds"] or 0.)
            try:ready=self._fast_analyze_symbol(symbol) or ready
            except _PriorityYield:metrics["skipped_commands"]+=1;break
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                metrics["errors"]+=1;self._audit("FAST_ANALYSIS_ERROR",{"symbol":symbol,"reason":str(exc)})
            self._fast_checked[symbol]=checked;self._fast_seen.add(symbol)
            metrics["last_checked_at"]=self.clock();metrics["checked_in_sweep"]=len(self._fast_seen)
            if names and len(self._fast_seen)==len(names):
                sweep_started=started if self._fast_sweep_started is None else self._fast_sweep_started
                metrics["sweep_count"]+=1;metrics["last_sweep_seconds"]=max(0.,self._fast_monotonic()-sweep_started)
                self._fast_seen=set();self._fast_sweep_started=self._fast_monotonic()
        self._rank()
        if ready and not self._priority_yield_requested():self._trade_candidates(fast_only=True)
        elapsed=self._fast_monotonic()-started
        metrics.update(last_batch_seconds=elapsed,max_batch_seconds=max(metrics["max_batch_seconds"],elapsed))
        if elapsed>FAST_BATCH_SECONDS:metrics["budget_overruns"]+=1
        return ready

    def _fast_background_step(self):
        """Observe 42 schools one timeframe at a time, every bounded job."""
        if self.settings.get('decision_protocol')=='multi_school_v1' and self._autonomous_fast_enabled():return
        if self._priority_yield_requested():return
        started=self._fast_monotonic();job=self._fast_background_job
        if job is None:
            if not self._fast_metrics["sweep_count"]:return
            if not self.deep_queue or started-self._fast_background_at<FAST_BACKGROUND_SECONDS:return
            symbol=self.deep_queue.pop(0)
            if not self.scanner.rows.get(symbol,{}).get("eligible"):return
            job={"symbol":symbol,"index":0,"cards":[]};self._fast_background_job=job;self._fast_background_at=started
        symbol=job["symbol"];tf=DECISION_TIMEFRAMES[job["index"]]
        context=self._context(symbol,tf)
        if self._priority_yield_requested():return
        bars=self.broker.bars(symbol,tf,_analysis_bar_count(tf));now=self.clock()
        if self._priority_yield_requested():return
        cards=analyze_all(symbol,tf,bars,now,context);self._observe_rules(cards);job["cards"].extend(cards);job["index"]+=1
        self._fast_metrics["background_steps"]+=1
        self._fast_metrics["last_background_step_seconds"]=self._fast_monotonic()-started
        if self.chart.get("symbol")==symbol and self.chart.get("timeframe")==tf:
            self.chart={"symbol":symbol,"timeframe":tf,"bars":bars,"cards":cards,"as_of":now}
        if job["index"]==len(DECISION_TIMEFRAMES):
            self.cards_by_symbol[symbol]=job["cards"]
            self.cache.put("cards:"+account_key(self.broker.account())+":"+symbol,job["cards"])
            if self.settings.get("decision_protocol")=="multi_school_v1":
                self._multi_analyze_symbol(symbol);self._fast_background_job=None;self.last_deep=self.clock();return
            try:
                evaluations,gate,market,now,_books=self._fast_full_context(symbol)
                result=self._strict_decision(symbol,evaluations,job["cards"],gate,now,market)
                self.decisions[symbol]=result;self._rank()
                self._audit("COMMITTEE_DECISION",{"symbol":symbol,"decision":result["decision"],"reasons":result["reasons"],"protocol_revision":confluence.PROTOCOL_REVISION,"ranked":result["ranked"]})
            except _PriorityYield:pass
            finally:self._fast_background_job=None;self.last_deep=self.clock()

    def _fast_scan_step(self):
        """Refresh all broker symbols without monopolizing a priority cycle."""
        if self._priority_yield_requested():return
        if not self.scanner.queue and self.clock()-self.last_scan>=300:
            self.scanner.begin();self.last_scan=self.clock()
        started=self._fast_monotonic();had_queue=bool(self.scanner.queue)
        for _ in range(FAST_SCAN_BATCH_LIMIT):
            if not self.scanner.queue or self._priority_yield_requested():break
            if self._fast_monotonic()-started>=FAST_SCAN_SECONDS:break
            self.scanner.step(1)
        if had_queue and not self.scanner.queue and self.scanner.snapshot()["complete"]:
            self.last_scan=self.clock()
            eligible=[r["symbol"] for r in self.scanner.candidates(len(self.scanner.rows))]
            retained=[name for name in self.deep_queue if name in eligible]
            active=(self._fast_background_job or {}).get("symbol")
            self.deep_queue=retained+[name for name in eligible if name not in retained and name!=active]

    def _publish_fast_controls(self):
        # Preserve broker-book ages while exposing current authority/cadence.
        # A full snapshot remains on its normal, slower publication cadence.
        execution={"mode":self.executor.mode,"entries_paused":self.executor.entries_paused,
            "authorization":copy.deepcopy(self.executor.authorization),"reason":self.executor.last_reason}
        with self.view_lock:
            self._view={**self._view,"status":self.status,"error":self.error,"mode":execution["mode"],
                "execution":{**self._view.get("execution",{}),**execution},"settings":copy.deepcopy(self.settings),
                "execution_updated_at":self.clock(),"fast_scheduler":self._fast_scheduler_snapshot()}

    def _connect(self,simulation=False,terminal_path="",bridge_path=""):
        if self.executor:
            self.executor.deactivate("تغيير مصدر البيانات")
        if self.broker and (self.broker.positions() or self.broker.orders()):
            raise ValueError("توجد مراكز أو أوامر في المصدر الحالي؛ أدرها أو أعد تشغيل التطبيق قبل تبديل المصدر.")
        # The official Python MT5 module has a process-global connection. Close
        # it before initialize(), never shutdown() after creating the new adapter.
        if self.broker:self.broker.close()
        if self.store:self.store.close()
        self.broker=self.store=self.risk=self.executor=self.scanner=None
        try:
            new=SimBroker(self.clock) if simulation else MT5Broker(terminal_path,bridge_path)
        except Exception:
            self.status="DISCONNECTED";self.settings={}
            raise
        self._invalidate_research()
        self.context_cache={};self.partner_catalog=None
        self.broker=new;self.store=Store(self.data/("simulation.sqlite3" if simulation else "live.sqlite3"))
        self.learner=LearningMemory(self.store,self.rule_library);self.last_learning=0
        with self.store.lock:
            self.store.db.execute("CREATE TABLE IF NOT EXISTS financial_scenarios(id TEXT PRIMARY KEY,account TEXT NOT NULL,created REAL NOT NULL,payload TEXT NOT NULL)")
            self.store.db.execute("CREATE TABLE IF NOT EXISTS school_reference_versions(revision TEXT PRIMARY KEY,payload TEXT NOT NULL)")
            self.store.db.execute("INSERT OR IGNORE INTO school_reference_versions VALUES(?,?)",(self.knowledge["catalog_revision"],json.dumps(self.knowledge,ensure_ascii=False,allow_nan=False)))
        self._execution_tables()
        self._load_execution_reference()
        self.learning_account=None
        self._sync_learning_scope(account_key(new.account()))
        self.risk=RiskManager(new,self.store);self.executor=Executor(new,self.store,self.risk,self.clock)
        self.scanner=UniverseScanner(new,self.clock)
        self.quant_results={};self.cards_by_symbol={};self.decisions={};self.opportunities=[];self.manual={};self.deep_queue=[];self.attempted={}
        self.settings={};self.status="READ_ONLY";self.error="";self.chart={"symbol":"","timeframe":"H1","bars":[],"cards":[]}
        if not simulation:
            self.config={**self.config,"terminal_path":terminal_path,"bridge_path":bridge_path}
            self.config_path.write_text(json.dumps(self.config,ensure_ascii=False),encoding="utf-8")
        self._audit("CONNECTED_READ_ONLY",{"simulation":simulation,"account_key":account_key(new.account()),"trade_mode":new.account().get("trade_mode")})
        self.scanner.begin();self.last_scan=self.clock()
        return {"ok":True,"message":"متصل للقراءة. التفويض يبدأ فقط بعد إدخال حدود اليوم والضغط على ابدأ."}

    def _recover_mt5_connection(self, cause):
        """Recover a stale Python IPC binding without restoring authorization."""
        if not self.broker or self.broker.is_simulation or not hasattr(self.broker,"reconnect"):
            return False
        now=self.clock()
        if now-self.last_reconnect_attempt<5:
            return False
        self.last_reconnect_attempt=now
        reason="انقطع اتصال MT5 وأعيد ربطه؛ يلزم تفعيل Demo من جديد"
        if self.executor:self.executor.deactivate(reason)
        self.status="DISCONNECTED";self.error=str(cause)
        try:
            terminal=self.broker.reconnect()
            account=self.broker.account();key=account_key(account)
            self._sync_learning_scope(key)
            self.context_cache={};self.partner_catalog=None
            # Build fresh guards around the recovered broker.  In particular,
            # no authorization object or reserved in-memory budget survives.
            self.risk=RiskManager(self.broker,self.store)
            self.executor=Executor(self.broker,self.store,self.risk,self.clock)
            self.scanner=UniverseScanner(self.broker,self.clock)
            reconciliation=self.executor.reconcile(key)
            if not reconciliation.get("ok"):
                raise BrokerError("تعذرت مطابقة سجل الوسيط بعد إعادة الاتصال: "+str(reconciliation.get("reason") or reconciliation.get("unresolved")))
            self._invalidate_research()
            self.settings={};self.quant_results={};self.cards_by_symbol={};self.decisions={};self.opportunities=[];self.manual={};self.deep_queue=[];self.attempted={}
            self.chart={"symbol":"","timeframe":"H1","bars":[],"cards":[]}
            self.scanner.begin();self.last_scan=now
            self.status="READ_ONLY";self.error=""
            self._audit("CONNECTION_RESTORED_READ_ONLY",{"mode":"READ_ONLY","account_key":key,"terminal_connected":bool(terminal.get("connected"))})
            return True
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            self.status="DISCONNECTED";self.error=str(exc)
            return False

    def _action(self,p):
        action=p["action"]
        if action=="connect":return self._connect(False,str(p.get("terminal_path","")).strip(),str(p.get("bridge_path","")).strip())
        if action=="simulation":return self._connect(True)
        if action=="diagnostics":return self._diagnostics()
        if action=="knowledge_export":return self._export_knowledge()
        if action=="fundamental_analyze":
            if not self.store or not self.broker:raise ValueError("اتصل بمصدر البيانات لحفظ التقييم المحلي")
            result=evaluate_valuation(p.get("data"))
            reference=self.root/"docs/knowledge/valuation-reference.json"
            result["model_revision"]=json.loads(reference.read_text(encoding="utf-8"))["revision"] if reference.exists() else "UNVERSIONED"
            key=account_key(self.broker.account());self._sync_learning_scope(key)
            identity=digest([key,result["input_fingerprint"],result["model_revision"]])
            with self.store.transaction() as db:
                db.execute("INSERT OR IGNORE INTO financial_scenarios VALUES(?,?,?,?)",(identity,key,self.clock(),json.dumps({"inputs":p["data"],"result":result},ensure_ascii=False,allow_nan=False)))
            self.valuation=result
            self._audit("VALUATION_SAVED",{"model":result["model"],"input_fingerprint":result["input_fingerprint"]})
            return {"ok":True,"valuation":result,"message":"حُفظ سيناريو التقييم المحلي وافتراضاته"}
        if action=="shutdown":
            if self.executor:self.executor.deactivate("طلب إغلاق الخدمة")
            with self._action_result_lock:self.running=False
            return {"ok":True}
        if not self.broker:raise ValueError("اتصل بـMT5 Demo أو اختر المحاكاة أولًا")
        if action=="reconcile":
            result=self.executor.reconcile()
            self._audit("RECONCILIATION",result)
            return {"ok":result.get("ok") is True,"result":result,
                    "message":"اكتملت مطابقة سجل الوسيط" if result.get("ok") else "تعذرت المطابقة؛ راجع السجل"}
        if action in ("scan","refresh"):
            if not self.scanner.queue:
                self.scanner.begin();self.last_scan=self.clock();self.deep_queue=[]
            self.news.refresh();return {"ok":True,"message":"بدأ فحص جميع رموز المنصة؛ تابع عداد الإنجاز."}
        if action=="install_bridge":return self._install_bridge()
        if action=="start":
            protocol=p.get("decision_protocol","general")
            if protocol not in ("general","four_school_v1","multi_school_v1"):raise ValueError("Unknown decision protocol")
            profiles=self._validate_scalping(p.get("scalping",{}))
            if protocol in ("four_school_v1","multi_school_v1"):
                if p.get("validation_policy","historical")!="forward_demo":
                    raise ValueError("Four-school historical qualification is unavailable; choose forward_demo")
                self._load_execution_reference(required=True)
                if protocol=="multi_school_v1":self._load_multi_reference()
            elif any(v["enabled"] for v in profiles.values()):
                raise ValueError("Scalping requires the four_school_v1 decision protocol")
            self._check_scalp_targets(profiles)
            unit="percent" if p.get("unit")=="percent" else "amount"
            settings={"daily_risk":p.get("risk_value"),"daily_target":p.get("target_value"),"risk_unit":unit,"target_unit":unit,
                "fast_profit_protection":p.get('fast_profit_protection',self.config.get('fast_profit_protection',False)),
                "fast_cash_target_usd":p.get('fast_cash_target_usd',self.config.get('fast_cash_target_usd',1.)),
                "validation_policy":p.get("validation_policy","historical"),
                "decision_protocol":protocol,"scalping":profiles,"scalp_only":p.get("scalp_only") is True,
                "amend_daily_limits":p.get("amend_daily_limits") is True,
                "allow_daily_risk_increase":p.get("allow_daily_risk_increase") is True,
                "commission_per_lot":p.get("commission_per_lot"),"slippage_points":p.get("slippage_points"),
                "max_trade_fraction":.2,"correlation_cap_fraction":.5,"max_proposal_age":14400,
                "max_session_age":120,"max_calendar_age":120,"max_tick_age":15}
            result=self.executor.activate(p.get("mode","AUTO_DEMO"),settings)
            self._invalidate_research()
            self.settings=dict(self.risk.settings or {});self.status=p.get("mode","AUTO_DEMO");self.error=""
            try:
                self._authorize_scalping(profiles)
                self.config.update(decision_protocol=protocol,scalping=profiles,
                    fast_profit_protection=self.settings.get('fast_profit_protection',False),
                    fast_cash_target_usd=self.settings.get('fast_cash_target_usd',1.))
                self.config_path.write_text(json.dumps(self.config,ensure_ascii=False,allow_nan=False),encoding="utf-8")
            except Exception:
                self.executor.deactivate("Activation persistence failed");self.status="READ_ONLY"
                raise
            # Waive only the heuristic cutoff; actual bid/ask costs still bind
            # sizing and independent net reward/risk validation.
            spread_filter=spread_filter_required(self.settings,self.broker.account(),self.broker.is_simulation)
            if self.scanner.spread_filter!=spread_filter:
                self.scanner.spread_filter=spread_filter
                self.scanner.begin();self.last_scan=self.clock()
            # Previous READ_ONLY analysis used unknown costs; invalidate those certificates.
            self.quant_results={};self.decisions={};self.opportunities=[];self.manual={};self.deep_queue=[]
            if self.scanner.snapshot()["complete"]:
                self.deep_queue=[r["symbol"] for r in self.scanner.candidates(len(self.scanner.rows))]
            return {"ok":True,"message":"اعتمد تفويض Demo وحدود اليوم المحفوظة. ينتظر النظام فرصة تستوفي جميع الفحوص.","result":result}
        if action=="stop":
            result=self.executor.stop_entries();self.status="ENTRIES_STOPPED"
            return {"ok":True,"message":"أوقف الدخول الجديد؛ تستمر إدارة المراكز ضمن التفويض القائم.","result":result}
        if action=="cancel":return {"ok":True,"result":self.executor.cancel_owned_orders(),"message":"سجلت محاولات إلغاء أوامر المنظومة؛ التأكيد من الوسيط ظاهر في السجل."}
        if action=="flatten":
            self.executor.stop_entries();self.status="ENTRIES_STOPPED"
            return {"ok":True,"result":self.executor.flatten_owned_positions(),"message":"أوقف الدخول الجديد وسجل محاولات إغلاق مراكز المنظومة؛ تحقق من تأكيد الوسيط والنتائج."}
        if action=="approve":
            proposal=self.manual.get(p.get("intent_id"))
            if not proposal:raise ValueError("الاقتراح غير متاح أو منتهي؛ أعد الفحص")
            proposal=self._fresh_proposal(proposal)
            result=self.executor.execute(proposal,approved=True)
            self.manual.pop(p["intent_id"],None)
            return {"ok":bool(result.get("approved",False)),"result":result,"message":"نتيجة فحص الموافقة مسجلة في السجل."}
        if action=="chart":
            symbol=str(p.get("symbol",""));tf=p.get("timeframe","H1")
            if tf not in TIMEFRAMES or symbol not in self.scanner.rows:raise ValueError("رمز أو فريم غير معتمد")
            self.broker.select(symbol)
            as_of = self.clock()
            bars = validate_bars(self.broker.bars(symbol,tf,_analysis_bar_count(tf)), tf, as_of)
            cards=analyze_all(symbol,tf,bars,as_of,self._context(symbol,tf))
            self._observe_rules(cards)
            self.chart={"symbol":symbol,"timeframe":tf,"bars":bars,"cards":cards,"as_of":as_of,"committee":self.decisions.get(symbol)}
            self.cache.put("chart:"+account_key(self.broker.account())+":"+symbol+":"+tf,self.chart)
            return {"ok":True,"message":"حدّث الشارت وبطاقات المدارس من الشموع المكتملة."}
        if action=="backtest":
            symbol=p.get("symbol",self.chart.get("symbol"));tf=p.get("timeframe",self.chart.get("timeframe","H1"))
            if not symbol or symbol not in self.scanner.rows or tf not in TIMEFRAMES:raise ValueError("اختر رمزًا وفريمًا أولًا")
            costs={k:float(p.get(k)) for k in ("commission_per_lot","slippage_points")}
            if any(not math.isfinite(v) or v<0 for v in costs.values()):raise ValueError("تكاليف معروفة وغير سالبة مطلوبة للتحقق التاريخي")
            if self.settings and any(costs[k]!=self.settings[k] for k in costs):
                raise ValueError("تكاليف البحث تختلف عن التفويض القائم؛ استخدم القيم المعتمدة أو أعد التفويض.")
            if not self.settings:self.research_costs=costs
            self.broker.select(symbol);history=self.broker.bars(symbol,tf,2200)
            for strategy_id,meta in REGISTRY.items():
                if meta["coverage"]=="IMPLEMENTED":self._request_quant(symbol,tf,strategy_id,history)
            return {"ok":True,"message":"بدأ التحقق التاريخي بالترتيب الزمني؛ نتائجه تظهر في الأداء."}
        raise ValueError("إجراء غير مدعوم")

    def _install_bridge(self):
        if self.broker.is_simulation:raise ValueError("الجسر يثبت في MT5 الفعلي فقط")
        terminal=self.broker.terminal()
        destination=Path(terminal["data_path"])/"MQL5"/"Experts"/"QuantTradingAI"
        destination.mkdir(parents=True,exist_ok=True)
        for name in ("QuantTradingAI_ReadOnlyBridge.mq5","QuantTradingAI_ReadOnlyBridge.ex5"):
            source=self.root/"bridge"/name
            if not source.exists():raise ValueError("ملف الجسر المبني غير موجود؛ اجمعه في MetaEditor أولًا")
            target=destination/name
            if target.exists() and hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(source.read_bytes()).digest():
                backup=target.with_name(target.name+"."+str(int(time.time()))+".bak");shutil.copy2(target,backup)
            shutil.copy2(source,target)
        self._audit("READ_ONLY_BRIDGE_INSTALLED",{"path":str(destination)})
        return {"ok":True,"message":"ثبت جسر القراءة. في MT5 افتح Navigator ثم Refresh، واسحب QuantTradingAI_ReadOnlyBridge إلى أي شارت. لا يحتوي الجسر أوامر تداول.","path":str(destination)}

    def _context(self,symbol,timeframe="H1",history_count=300):
        info=self.broker.symbol(symbol)
        context={"point":info["point"],"tick_size":info["trade_tick_size"],"symbol_info":info,
                 "data_kind":"synthetic" if self.broker.is_simulation else "broker"}
        def history(name,tf,count,ttl):
            key=(name,tf,count); cached=self.context_cache.get(key)
            if cached and 0<=self.clock()-cached[0]<ttl:return cached[1]
            self.broker.select(name)
            value=self.broker.bars(name,tf,count)
            self.context_cache[key]=(self.clock(),value)
            capacity=max(64,min(512,len(getattr(self.scanner,"rows",{}))*2))
            while len(self.context_cache)>capacity:self.context_cache.pop(next(iter(self.context_cache)))
            return value
        try:context["daily_bars"]=history(symbol,"D1",1500,600)
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            context["daily_context_error"]=str(exc)
        # Explicit economic pairs, resolved by broker metadata, never suffix
        # guessing. Ambiguous duplicate contracts are rejected, not selected.
        pair_map={("EUR","USD"):("GBP","USD"),("GBP","USD"):("EUR","USD"),
                  ("AUD","USD"):("NZD","USD"),("NZD","USD"):("AUD","USD")}
        pair=pair_map.get((info.get("currency_base"),info.get("currency_profit")))
        if pair:
            try:
                if self.partner_catalog is None:self.partner_catalog=self.broker.symbols()
                matches=[x["name"] for x in self.partner_catalog if
                         (x.get("currency_base"),x.get("currency_profit"))==pair and x["name"]!=symbol]
                if len(matches)==1:
                    context.update(partner_symbol=matches[0],partner_policy="declared FX metadata pair v1",
                                   partner_bars=history(matches[0],timeframe,history_count,min(30,TIMEFRAMES[timeframe])))
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                context["partner_context_error"]=str(exc)
        return context

    def _quant_config(self,symbol):
        info=self.broker.symbol(symbol);tick=self.broker.tick(symbol)
        policy=self.settings or self.research_costs
        known=bool(policy) and "commission_per_lot" in policy
        commission=float(policy.get("commission_per_lot",0))
        if not math.isfinite(commission) or commission<0:raise ValueError("عمولة البحث غير صالحة")
        commission_per_unit=0.
        if commission:
            # A one-point probe can be rounded to zero by the terminal/account
            # currency conversion on low-value contracts (observed on JP225).
            # Use a bounded 100-tick probe for numerical stability.  Zero
            # commission requires no conversion and must never block analysis.
            point=float(info["point"]);tick_size=float(info["trade_tick_size"])
            probe=max(point,tick_size)*100
            price_value=abs(self.broker.calc_profit("BUY",symbol,1.,tick["ask"],tick["ask"]+probe))/probe
            if not math.isfinite(price_value) or price_value<=0:raise ValueError("تعذر تحويل العمولة لوحدات السعر")
            commission_per_unit=commission/price_value
        return {"point":info["point"],"tick_size":info["trade_tick_size"],"slippage_price":info["point"]*policy.get("slippage_points",0),
                "commission_per_unit":commission_per_unit,"commission_known":known,
                "model_config_revision":configured_profile_revision()}

    @staticmethod
    def _cost_hash(config):
        return hashlib.sha256(json.dumps(config,sort_keys=True,allow_nan=False).encode()).hexdigest()

    def _certificate_valid(self,result,symbol,tf,strategy_id,config=None):
        now=self.clock();config=config or self._quant_config(symbol)
        data_kind="synthetic" if self.broker.is_simulation else "broker"
        return (result.get("strategy_id")==strategy_id and result.get("version")==REGISTRY[strategy_id]["version"] and result.get("plan_version")==PLAN_VERSION
            and result.get("data_kind")==data_kind and result.get("symbol")==symbol and result.get("timeframe")==tf
            and result.get("cost_config_hash")==self._cost_hash(config) and 0<=now-result.get("checked_at",0)<86400
            and now<result.get("certificate_expires_at",0) and result.get("data_time",0)<=now)

    def _request_quant(self,symbol,tf,strategy_id,bars):
        config=self._quant_config(symbol);key=f"{symbol}:{tf}:{strategy_id}"
        kind="synthetic" if self.broker.is_simulation else "broker"
        cache_key=account_key(self.broker.account())+":"+key+":"+REGISTRY[strategy_id]["version"]+":"+kind+":"+PLAN_VERSION+":"+self._cost_hash(config)
        cached=self.cache.get("quant:"+cache_key)
        if cached and self._certificate_valid(cached,symbol,tf,strategy_id,config):
            self.quant_results[key]=cached;return
        pending_key=(self.generation,key)
        if pending_key in self.pending_quant:return
        data_kind="synthetic" if self.broker.is_simulation else "broker"
        future=self.analysis_pool.submit(walk_forward,bars,strategy_id,symbol,tf,config,data_kind,self._context(symbol,tf,len(bars)),self.research_cancel)
        self.pending_quant[pending_key]=(future,cache_key,config)
        self.quant_results[key]={"strategy_id":strategy_id,"symbol":symbol,"timeframe":tf,"qualified":False,"status":"RUNNING","reasons":["التحقق التاريخي قيد التنفيذ"],"data_kind":data_kind}

    def _collect_quant(self):
        for pending_key,(future,cache_key,config) in list(self.pending_quant.items()):
            if not future.done():continue
            del self.pending_quant[pending_key]
            if pending_key[0]!=self.generation:continue
            key=pending_key[1]
            try:
                result=future.result();now=self.clock()
                result.update(checked_at=now,certificate_expires_at=min(now+86400,(int(now//86400)+1)*86400),
                    cost_config_hash=self._cost_hash(config),plan_version=PLAN_VERSION)
                self.quant_results[key]=result;self.cache.put("quant:"+cache_key,result)
                self._audit("QUANT_COMPLETED",{k:result.get(k) for k in ("strategy_id","symbol","timeframe","qualified","status","metrics","reasons")})
                symbol=result.get("symbol")
                if result.get("qualified") and symbol in self.scanner.rows:
                    # Refresh the completed candles, news and quote before sending.
                    # Do not wait for every other symbol in the universe first.
                    self.deep_queue=[symbol]+[s for s in self.deep_queue if s!=symbol]
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                self.quant_results[key]={"qualified":False,"status":"ERROR","reasons":[str(exc)]}
                self._audit("QUANT_ERROR",{"key":key,"reason":str(exc)})

    @staticmethod
    def _protocol_reason(code,en,ar):
        return {"code":code,"en":en,"ar":ar}

    def _strict_proposal(self,symbol,tf,evaluation,cards,gate,now,variant=None):
        candidate=evaluation["candidate"];side={"LONG":"BUY","SHORT":"SELL"}[candidate["side"]]
        style="SCALP" if variant else "BASE"
        identity=digest([symbol,tf,candidate["formation_id"],confluence.PROTOCOL_REVISION,style,variant])
        rule=self.rule_library.get("four_school_confluence")
        if not rule:raise ValueError("Current four-school knowledge rule revision is unavailable")
        proposal={"id":identity,"symbol":symbol,"timeframe":tf,"side":side,
            "strategy_id":"four_school_confluence","strategy_version":"1.0.0","version":"1.0.0",
            "rule_revision":rule["revision"],
            "entry":candidate["entry"],"entry_zone":copy.deepcopy(candidate["entry_zone"]),
            "sl":candidate["stop"],"tp":candidate["target"],"targets":[{"price":candidate["target"],"policy":candidate["target_policy"]}],
            "invalidation":{"price":candidate["structure_stop"],"reason":"Protected sweep structure"},
            "execution_plan":{"timeframe":tf,"max_hold_bars":32,"allow_addition":False,"stop_may_only_tighten":True},
            "data_time":candidate["data_time"],"expires_at":candidate["data_time"]+TIMEFRAMES[tf],
            "qualified":False,"signal_validated":True,"validation_policy":"forward_demo","news_ok":True,"news_gate":gate,
            "decision_protocol":"four_school_v1","protocol_revision":confluence.PROTOCOL_REVISION,
            "decision_matrix":copy.deepcopy(evaluation["matrix"]),"formation_id":candidate["formation_id"],
            "formation":copy.deepcopy(candidate["formation"]),"input_snapshot_hash":candidate["input_snapshot_hash"],
            "execution_style":style,"execution_policy_revision":confluence.PROTOCOL_REVISION,
            "score":0,"evidence_group":"structure","card_ids":[],"evidence":copy.deepcopy(candidate["structural_evidence"]),
            "quant_metrics":{},"win_probability_asserted":False,
            "reason":"تقاطع قواعد محددة؛ اختبار أمامي Demo دون ضمان نجاح أو ربح يومي"}
        proposal["decision_matrix"]["status"]="READY"
        matching=[c for c in cards if c.get("timeframe")==tf and c.get("data_time")==candidate["data_time"]
            and c.get("quality")=="VALIDATED_OHLC"]
        for card in matching:
            if card.get("chart_features"):
                proposal["chart_features"]=copy.deepcopy(card["chart_features"])
                proposal["market_regime"]=(card.get("market_regime") or {}).get("name","UNKNOWN")
                break
        proposal["card_ids"]=[c["id"] for c in matching if c.get("strategy_id")=="four_school_confluence"]
        if variant:
            state=self.scalping_state.get(variant,{})
            proposal=scalping.adaptation_plan(proposal,state.get("session_id"),variant)
            profile=self.settings["scalping"][variant]
            proposal.update(requested_risk_percent=profile["risk_percent"],requested_min_reward_risk=profile["min_reward_risk"],
                execution_policy_revision=scalping.POLICY_REVISION)
        if variant and profile.get("profit_percent") is not None:
            proposal["requested_profit_percent"] = profile["profit_percent"]
        self._seal_and_preview(proposal)
        return proposal

    def _seal_and_preview(self,proposal):
        matrix=proposal["decision_matrix"]
        matrix["status"]="READY"
        matrix["certificate_hash"]=protocol_certificate_hash(proposal)
        info=self.broker.symbol(proposal["symbol"])
        evidence=self.risk.minimum_rr_check(proposal,{"symbol":proposal["symbol"],"side":proposal["side"],
            "price":proposal["entry"],"sl":proposal["sl"],"tp":proposal["tp"],"volume":info["volume_min"]},info)
        if evidence is None:raise ValueError("Strict net reward/risk preview unavailable")
        matrix["net_rr_preview"]={**evidence,"volume":info["volume_min"],"read_only":True}
        matrix["structural_rr"]["net_cost_validation_pending"]=False
        matrix["certificate_hash"]=protocol_certificate_hash(proposal)

    def _strict_decision(self,symbol,evaluations,cards,gate,now,market,proposal_timeframes=None):
        """Keep every school observable; only the activated matrix can enter."""
        self._refresh_scalping()
        result={"symbol":symbol,"decision":"WAIT","proposals":[],"ranked":[],"reasons":[],
            "as_of":now,"expires_at":now,"news_gate":gate,"decision_protocol":"four_school_v1",
            "protocol_revision":confluence.PROTOCOL_REVISION,"decision_matrices":{},"protocol_reasons":{},
            "formula":"Linked ICT + actual POC or declared bar timing; structural and net reward/risk >= 2",
            "limitations":["No proven win probability or daily-profit guarantee; historical composite qualification unavailable"]}
        ready={tf:value for tf,value in evaluations.items() if value.get("status")=="READY" and value.get("execution_ready") and value.get("candidate")}
        sides={v["candidate"]["side"] for v in ready.values()}
        for tf,evaluation in evaluations.items():
            reasons=copy.deepcopy(evaluation.get("reasons",[]));matrix=copy.deepcopy(evaluation["matrix"])
            candidate=evaluation.get("candidate");variant=self._scalp_variant(tf)
            actionable=tf in ready and (proposal_timeframes is None or tf in proposal_timeframes)
            if actionable:
                if candidate["data_time"]+TIMEFRAMES[tf]<=now:
                    reasons.append(self._protocol_reason("FORMATION_EXPIRED","The original closed-bar proposal window expired during data collection.","انتهت نافذة الاقتراح الأصلية أثناء جمع بيانات الشموع المكتملة."))
                if self._formation_used(symbol,tf,candidate["formation_id"]):
                    reasons.append(self._protocol_reason("FORMATION_ALREADY_USED","This formation already owns an execution intent; changing style cannot repeat it.","هذا التكوين مرتبط بطلب تنفيذ سابق؛ تغيير الأسلوب لا يعيد دخوله."))
                if len(sides)>1:reasons.append(self._protocol_reason("TIMEFRAME_OPPOSITION","Ready opposing ICT confluence exists on another timeframe.","تقاطع سيولة جاهز في الاتجاه المقابل على فريم آخر."))
                if self.settings.get("validation_policy")!="forward_demo":reasons.append(self._protocol_reason("FORWARD_DEMO_REQUIRED","Composite historical qualification is unavailable.","التأهيل التاريخي للمركب غير متاح؛ يلزم اختبار أمامي Demo."))
                if not gate.get("ok") or gate.get("blackout"):reasons.append(self._protocol_reason("NEWS_GATE","Required news/calendar gate is unavailable or blocked.","بوابة الأخبار أو التقويم المطلوبة غير متاحة أو محظورة."))
                if not market.get("eligible") or not market.get("open") or market.get("stale") or self.broker.is_simulation:
                    reasons.append(self._protocol_reason("MARKET_GATE","Verified broker market eligibility, session and fresh quote are required.","يلزم تأهيل السوق وجلسة مفتوحة وسعر حديث من الوسيط الفعلي."))
                if variant and not self.scalping_state.get(variant,{}).get("progress",{}).get("entries_allowed"):
                    reasons.append(self._protocol_reason("SCALP_GOAL_GATE","Scalp session goal or uncertain progress stopped new entries.","هدف جلسة السكالب أو غموض تقدمها أوقف الدخول الجديد."))
                proposal=None
                if not reasons:
                    try:
                        proposal=self._strict_proposal(symbol,tf,evaluation,cards,gate,now,variant)
                        matrix=copy.deepcopy(proposal["decision_matrix"])
                    except (ValueError,KeyError,TypeError) as exc:
                        reasons.append(self._protocol_reason("NET_RR_OR_POLICY_GATE",str(exc),"فشل فحص العائد الصافي أو سياسة التنفيذ؛ لا يسمح بالدخول."))
                identity=proposal["id"] if proposal else digest([symbol,tf,candidate["formation_id"],confluence.PROTOCOL_REVISION,"SCALP" if variant else "BASE",variant])
                result["ranked"].append({"card_id":identity,"strategy_id":"four_school_confluence","symbol":symbol,
                    "timeframe":tf,"side":{"LONG":"BUY","SHORT":"SELL"}[candidate["side"]],"score":0,
                    "eligible":bool(proposal),"reason_codes":[r["code"] for r in reasons],"reasons":[r["ar"]+" ("+r["en"]+")" for r in reasons]})
                if proposal:result["proposals"].append(proposal)
            if reasons:matrix["passed"]=False
            matrix["status"]="READY" if actionable and not reasons else "CONTEXT" if tf in ready and not actionable else "WAIT"
            display_reasons=reasons
            if tf in ready and not actionable and not reasons:
                display_reasons=[self._protocol_reason("OPPOSITION_CONTEXT","This timeframe supplies fresh opposing-context checks; the priority lane proposes M1 only.","هذا الفريم يوفر فحص التعارض الحديث؛ مسار الأولوية يقترح فريم الدقيقة فقط.")]
            elif actionable and not reasons:
                display_reasons=[self._protocol_reason("CONFLUENCE_READY","Current causal confluence and net reward/risk passed for a Demo forward experiment; no success or daily-profit guarantee.","اجتاز التقاطع السببي الحالي والعائد الصافي لفحص Demo أمامي؛ دون ضمان النجاح أو الربح اليومي.")]
            result["decision_matrices"][tf]=matrix;result["protocol_reasons"][tf]=display_reasons
        result["reasons"]=[r["ar"]+" ("+r["en"]+")" for rows in result["protocol_reasons"].values() for r in rows]
        if result["proposals"]:
            best=result["proposals"][0];result.update(decision=best["side"],expires_at=best["expires_at"],reasons=[best["reason"]])
        return result

    def _analyze_symbol(self,symbol,force_quant=False):
        if self.settings.get("decision_protocol")=="multi_school_v1":return self._multi_analyze_symbol(symbol)
        all_cards=[];info=self.broker.symbol(symbol);bars_by_tf={}
        for tf in DECISION_TIMEFRAMES:
            context=self._context(symbol,tf)
            bars=self.broker.bars(symbol,tf,_analysis_bar_count(tf))
            bars_by_tf[tf]=bars
            # Broker/context reads may span a completed-bar boundary. The
            # analysis clock must follow those reads, never precede the data.
            now=self.clock()
            cards=analyze_all(symbol,tf,bars,now,context);self._observe_rules(cards);all_cards.extend(cards)
            if self.chart.get("symbol")==symbol and self.chart.get("timeframe")==tf:
                self.chart={"symbol":symbol,"timeframe":tf,"bars":bars,"cards":cards,"as_of":now}
        self.cards_by_symbol[symbol]=all_cards
        self.cache.put("cards:"+account_key(self.broker.account())+":"+symbol,all_cards)
        row=self.scanner.rows[symbol];session=self.broker.session(symbol);calendar=self.broker.calendar()
        # A quote read after five analyses is naturally newer than their start
        # time. All decision matrices and the news gate share this later clock.
        tick=self.broker.tick(symbol);now=self.clock()
        self.scanner.rows[symbol]["last_analysis"]=now
        gate=self.news.gate(info,calendar,self.broker.is_simulation,now)
        market={"eligible":row["eligible"],"open":session.get("open",False),"stale":not 0<=now-tick["time"]<=15,
                "spread":tick["ask"]-tick["bid"],"tick":tick}
        if self.settings.get("decision_protocol")=="four_school_v1":
            evaluations={tf:confluence.evaluate(symbol,tf,bars,now,info["trade_tick_size"],quote=tick) for tf,bars in bars_by_tf.items()}
            result=self._strict_decision(symbol,evaluations,all_cards,gate,now,market)
            self.decisions[symbol]=result
            self._audit("COMMITTEE_DECISION",{"symbol":symbol,"decision":result["decision"],"reasons":result["reasons"],"protocol_revision":confluence.PROTOCOL_REVISION,"ranked":result["ranked"]})
            if not self.chart["symbol"]:
                self.chart={"symbol":symbol,"timeframe":"H1","bars":bars_by_tf["H1"],"cards":[c for c in all_cards if c["timeframe"]=="H1"],"as_of":now}
            if self.chart.get("symbol")==symbol:self.chart["committee"]=result
            self._rank();return
        config=self._quant_config(symbol)
        for card in all_cards:
            if card.get("status")!="READY" or not card.get("actionable"):continue
            key=f"{symbol}:{card['timeframe']}:{card['strategy_id']}"
            certificate=self.quant_results.get(key)
            if certificate and (self.generation,key) not in self.pending_quant and not self._certificate_valid(certificate,symbol,card["timeframe"],card["strategy_id"],config):
                # Expiry is a request to refresh evidence, not a permanent veto
                # that prevents the scheduler from ever requesting it again.
                self.quant_results.pop(key,None)
        research_policy={"validation_policy":self.settings.get("validation_policy","historical")}
        result=decide(all_cards,self.quant_results,gate,now,market,research_policy)
        missing_quant="strategy lacks eligible chronological cost-adjusted broker OOS evidence"
        viable={r["card_id"] for r in result.get("ranked",[])
                if set(r.get("reason_codes",[])) <= {missing_quant}}
        history_by_tf={}
        for card in all_cards:
            if card.get("status")!="READY" or not card.get("actionable"):continue
            if not force_quant and (research_policy["validation_policy"]=="forward_demo" or card["id"] not in viable):continue
            tf=card["timeframe"];strategy=card["strategy_id"];key=f"{symbol}:{tf}:{strategy}"
            if (self.generation,key) in self.pending_quant:continue
            if not force_quant and self._certificate_valid(self.quant_results.get(key,{}),symbol,tf,strategy):continue
            if tf not in history_by_tf:history_by_tf[tf]=self.broker.bars(symbol,tf,10000)
            self._request_quant(symbol,tf,strategy,history_by_tf[tf])
        # A cache hit may have supplied the missing certificate synchronously.
        # Apply it in this decision cycle instead of waiting for a universe scan.
        result=decide(all_cards,self.quant_results,gate,now,market,research_policy)
        by_id={c["id"]:c for c in all_cards}
        for proposal in result.get("proposals",[]):
            card=by_id.get(proposal["id"],{})
            if card.get("rule_revision"):proposal["rule_revision"]=card["rule_revision"]
            if card.get("chart_features"):
                # Preserve entry-time features; a later chart must never label
                # or rewrite the evidence attached to this execution intent.
                proposal["chart_features"]=json.loads(json.dumps(card["chart_features"],allow_nan=False))
            proposal["market_regime"]=(card.get("market_regime") or {}).get("name","UNKNOWN")
        result.update(symbol=symbol,news_gate=gate)
        self.decisions[symbol]=result
        self._audit("COMMITTEE_DECISION",{"symbol":symbol,"decision":result["decision"],"reasons":result["reasons"],"ranked":result.get("ranked",[])})
        if not self.chart["symbol"]:
            tf="H1";bars=self.broker.bars(symbol,tf,_analysis_bar_count(tf))
            self.chart={"symbol":symbol,"timeframe":tf,"bars":bars,"cards":[c for c in all_cards if c["timeframe"]==tf],"as_of":now,"committee":result}
        self._rank()

    def _rank(self):
        now=self.clock();rows=[]
        for symbol,decision in self.decisions.items():
            proposals={p["id"]:p for p in decision.get("proposals",[]) if p["expires_at"]>now}
            ranked=decision.get("ranked",[])
            if decision.get("decision_protocol")=="four_school_v1":
                by_tf={r.get("timeframe"):r for r in ranked}
                for tf,matrix in decision.get("decision_matrices",{}).items():
                    record=by_tf.get(tf,{})
                    proposal=proposals.get(record.get("card_id"))
                    reasons=decision.get("protocol_reasons",{}).get(tf,[])
                    rows.append({**record,"symbol":symbol,"timeframe":tf,"decision":proposal["side"] if proposal else "WAIT",
                        "eligible":bool(proposal),"score":0,"proposal":proposal,"intent_id":proposal["id"] if proposal else None,
                        "expires_at":proposal["expires_at"] if proposal else decision["expires_at"],"as_of":decision["as_of"],
                        "decision_protocol":"four_school_v1","decision_matrix":copy.deepcopy(matrix),
                        "protocol_reasons":copy.deepcopy(reasons),"reasons":[r["ar"] for r in reasons]})
                continue
            if not ranked:
                rows.append({"symbol":symbol,"decision":decision["decision"],"eligible":False,"score":0,"reasons":decision["reasons"],"as_of":decision["as_of"]})
            for r in ranked:
                proposal=proposals.get(r["card_id"])
                rows.append({**r,"decision":r["side"] if proposal else "REJECT","proposal":proposal,
                    "intent_id":proposal["id"] if proposal else None,"expires_at":proposal["expires_at"] if proposal else decision["expires_at"],"as_of":decision["as_of"]})
        self.opportunities=sorted(rows,key=lambda r:(not r.get("eligible",False),-r.get("score",0),r["symbol"]))
        for r in self.opportunities:
            if r.get("proposal") and r["proposal"]["id"] in self.attempted:
                r.update(attempted=True,risk_result=self.attempted[r["proposal"]["id"]])
        self.manual={r["proposal"]["id"]:r["proposal"] for r in self.opportunities if r.get("proposal") and not r.get("attempted")}

    def _fresh_proposal(self,proposal):
        if self.settings.get("decision_protocol")=="multi_school_v1" or proposal.get("decision_protocol")=="multi_school_v1":
            return self._multi_fresh_proposal(proposal)
        if self.settings.get("decision_protocol")=="four_school_v1" or proposal.get("decision_protocol")=="four_school_v1":
            return self._strict_fresh_proposal(proposal)
        p=copy.deepcopy(proposal);symbol=p["symbol"];now=self.clock();tick=self.broker.tick(symbol);info=self.broker.symbol(symbol)
        news=self.news.gate(info,self.broker.calendar(),self.broker.is_simulation,now)
        if not news["ok"]:raise ValueError("؛ ".join(news["reasons"]))
        if now>=p["expires_at"]:raise ValueError("انتهت صلاحية الاقتراح")
        strategy_id=p.get("strategy_id");tf=p.get("timeframe")
        certificate=self.quant_results.get(f"{symbol}:{tf}:{strategy_id}",{})
        forward_trial=(self.settings.get("validation_policy")=="forward_demo" and p.get("validation_policy")=="forward_demo" and p.get("signal_validated") is True)
        if strategy_id not in REGISTRY or REGISTRY[strategy_id]["coverage"]!="IMPLEMENTED":raise ValueError("Unimplemented strategy cannot execute")
        if not forward_trial and (not certificate.get("qualified") or not self._certificate_valid(certificate,symbol,tf,strategy_id)):
            raise ValueError("دليل التحقق الكمي منتهي أو تغيرت نسخته أو تكاليفه؛ أعد التحقق")
        if self.broker.is_simulation:raise ValueError("نتائج المحاكاة لا تمنح أهلية تنفيذ على الوسيط")
        quote=tick["ask"] if p["side"]=="BUY" else tick["bid"]
        zone=p.get("entry_zone")
        if not zone or not zone[0]<=quote<=zone[1]:raise ValueError("السعر خارج منطقة الدخول")
        grid=info["trade_tick_size"]
        # Round away from entry conservatively; risk is recalculated after rounding.
        p["sl"]=round((math.floor(p["sl"]/grid) if p["side"]=="BUY" else math.ceil(p["sl"]/grid))*grid,10)
        p["tp"]=round((math.ceil(p["tp"]/grid) if p["side"]=="BUY" else math.floor(p["tp"]/grid))*grid,10)
        p["qualified"]=not forward_trial;p["news_ok"]=True;p["entry"]=quote;p["news_gate"]=news
        return p

    def _strict_fresh_proposal(self,proposal):
        """Re-evaluate closed structure without changing its stop or target."""
        p=copy.deepcopy(proposal);symbol=p["symbol"];tf=p["timeframe"];now=self.clock()
        if (self.settings.get("decision_protocol")!="four_school_v1" or
                self.settings.get("validation_policy")!="forward_demo" or p.get("validation_policy")!="forward_demo"):
            raise ValueError("Current four-school forward Demo authorization is required")
        if p.get("protocol_revision")!=confluence.PROTOCOL_REVISION or p.get("strategy_id")!="four_school_confluence":
            raise ValueError("Four-school protocol or strategy changed")
        self.risk.validate_protocol_certificate(p)
        if now>=p["expires_at"]:raise ValueError("انتهت صلاحية الاقتراح")
        if self.broker.is_simulation:raise ValueError("نتائج المحاكاة لا تمنح أهلية تنفيذ على الوسيط")
        variant=self._scalp_variant(tf)
        if ((variant is None and p.get("execution_style")!="BASE") or
                (variant is not None and (p.get("execution_style")!="SCALP" or p.get("scalp_variant")!=variant))):
            raise ValueError("Original execution style or scalp policy changed")
        if variant:
            settings=self.settings["scalping"][variant]
            if (p.get("scalp_policy_revision")!=scalping.POLICY_REVISION or
                    p.get("execution_policy_revision")!=scalping.POLICY_REVISION or
                    p.get("requested_risk_percent")!=settings["risk_percent"] or
                    p.get("requested_min_reward_risk")!=settings["min_reward_risk"] or
                    p.get("requested_profit_percent")!=settings.get("profit_percent")):
                raise ValueError("Original scalp risk or execution policy changed")
            self._scalp_entry_guard(p)
        elif p.get("execution_policy_revision")!=confluence.PROTOCOL_REVISION:
            raise ValueError("Original base execution policy changed")
        # Read every closed-bar book before taking the execution quote. Slow
        # reads must not turn a valid fresh quote into a future-dated quote, nor
        # give opposing timeframes a different quote or decision clock.
        bars_by_tf={chart_tf:self.broker.bars(symbol,chart_tf,_analysis_bar_count(chart_tf))
                    for chart_tf in DECISION_TIMEFRAMES}
        info=self.broker.symbol(symbol);session=self.broker.session(symbol);calendar=self.broker.calendar()
        tick=self.broker.tick(symbol);now=self.clock()
        if now>=p["expires_at"]:raise ValueError("انتهت صلاحية الاقتراح أثناء تحديث البيانات")
        gate=self.news.gate(info,calendar,self.broker.is_simulation,now)
        if not gate.get("ok") or gate.get("blackout"):raise ValueError("؛ ".join(gate.get("reasons",["News/calendar gate refused"])))
        row=self.scanner.rows.get(symbol,{}) if self.scanner else {}
        if not session.get("open") or not row.get("eligible") or not 0<=now-tick["time"]<=15:
            raise ValueError("Fresh broker market/session gate refused")
        evaluation=confluence.evaluate(symbol,tf,bars_by_tf[tf],now,info["trade_tick_size"],quote=tick)
        candidate=evaluation.get("candidate")
        if evaluation.get("status")!="READY" or not candidate or not evaluation.get("execution_ready"):
            raise ValueError("Four-school formation is no longer ready: "+"; ".join(evaluation.get("reason_codes",[])))
        if (candidate["formation_id"]!=p.get("formation_id") or
                {"LONG":"BUY","SHORT":"SELL"}[candidate["side"]]!=p["side"] or
                candidate["stop"]!=p["sl"] or candidate["target"]!=p["tp"] or
                candidate["entry_zone"]!=p["entry_zone"]):
            raise ValueError("Original formation, structural stop or nearest liquidity target changed")
        if self._formation_used(symbol,tf,candidate["formation_id"],p["id"]):
            raise ValueError("Original formation already owns another execution style intent")
        for other_tf in DECISION_TIMEFRAMES:
            if other_tf==tf:continue
            other=confluence.evaluate(symbol,other_tf,bars_by_tf[other_tf],now,info["trade_tick_size"],quote=tick)
            if (other.get("status")=="READY" and other.get("candidate") and
                    other["candidate"]["side"]!=candidate["side"]):
                raise ValueError("Ready opposing ICT confluence on another timeframe")
        p.update(entry=candidate["entry"],data_time=candidate["data_time"],input_snapshot_hash=candidate["input_snapshot_hash"],
            decision_matrix=copy.deepcopy(evaluation["matrix"]),news_ok=True,news_gate=gate,qualified=False)
        self._seal_and_preview(p)
        if self.clock()>=p["expires_at"]:raise ValueError("انتهت صلاحية الاقتراح أثناء فحص التنفيذ")
        return p

    def _trade_candidates(self,fast_only=False):
        if not self.executor or self.executor.status().get("mode")!="AUTO_DEMO" or self.executor.status().get("entries_paused"):return
        for row in self.opportunities:
            p=row.get("proposal")
            if not p or row.get("attempted"):continue
            if self._fast_enabled() and self._priority_yield_requested():return
            if fast_only:
                if self._priority_yield_requested():return
                if p.get("execution_style")!="SCALP" or p.get("scalp_variant")!="fast" or p.get("timeframe")!="M1":continue
            try:
                self._scalp_entry_guard(p)
                p=self._fresh_proposal(p)
                result=self.executor.execute(p)
                row["risk_result"]=result
                row["attempted"]=True
                self.attempted[p["id"]]=result
                # One qualified attempt per cycle. Repeated intent stays deduplicated in SQLite.
                if result.get("approved"):
                    if (self.settings.get('fast_profit_protection') and p.get('execution_style')=='SCALP'
                            and p.get('scalp_variant')=='fast'):
                        try:row['post_fill_management']=self.executor.manage()
                        except Exception as exc:
                            logging.getLogger(__name__).exception("Handled boundary failure")
                            self._audit('POST_FILL_MANAGEMENT_ERROR',{'symbol':p['symbol'],'reason':str(exc)})
                    break
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                row["risk_result"]={"approved":False,"reasons":[str(exc)]}

    def _performance(self,intents):
        if not self.broker:return {"rows":[]}
        deals=self.broker.deals(int(self.clock()//86400)*86400)
        if deals is None:raise ValueError("سجل التدفقات المالية غير متاح")
        records=cashflow_records(deals,intents)
        owners={i["id"]:i for i in intents if i["kind"]=="ENTRY"}
        groups={}
        for intent in intents:
            if intent["kind"]!="ENTRY":continue
            p=intent["payload"].get("proposal",{})
            key=(p.get("strategy_id","unknown"),p.get("symbol","unknown"))
            groups.setdefault(key,{"strategy":key[0],"symbol":key[1],"gross":0.,"costs":0.,"net":0.,"closed_deals":0,"simulation":self.broker.is_simulation})
        for record in records:
            if not record["owner_id"]:continue
            p=owners[record["owner_id"]]["payload"].get("proposal",{})
            row=groups[(p.get("strategy_id","unknown"),p.get("symbol","unknown"))]
            row["gross"]+=record["gross"];row["costs"]+=record["costs"];row["net"]+=record["net"]
            row["closed_deals"]+=record["kind"]=="TRADE" and record["deal"].get("entry") in (1,2,3)
        result=list(groups.values())
        for row in result:
            row.update(trades=row["closed_deals"],realized_pnl=row["gross"],gross_pnl=row["gross"],net_pnl=row["net"])
        # Drawdown uses only confirmed realized cashflows; no inferred equity curve.
        flows=[]
        for record in sorted(records,key=lambda r:(r["deal"].get("time_msc",r["deal"].get("time",0)*1000),r["deal"].get("ticket",0))):
            if record["owner_id"]:flows.append(record["net"])
        equity=peak=drawdown=0.
        for flow in flows:
            equity+=flow;peak=max(peak,equity);drawdown=max(drawdown,peak-equity)
        return {"rows":result,"period":"UTC day","simulation":self.broker.is_simulation,
                "closed_trades":sum(r["closed_deals"] for r in result),"net_realized":sum(r["net"] for r in result),
                "realized_net":sum(r["net"] for r in result),"costs":-sum(r["costs"] for r in result),"max_drawdown":drawdown,
                "unattributed_costs":sum(max(0.,-r["net"]) for r in records if r["kind"]!="TRADE" and not r["owner_id"]),
                "cost_uncertainty":cost_uncertainties(records,intents),
                "drawdown_scope":"محقق خلال اليوم؛ لا يشمل مسار Equity داخل الصفقة"}

    def _sync_learning_scope(self,key):
        """Never display or label one account's evidence under another identity."""
        if key==self.learning_account:return
        changed=self.learning_account is not None
        if changed:
            if self.executor:self.executor.deactivate("تغير حساب MT5؛ يلزم تفويض الحساب الجديد")
            self._invalidate_research()
            self.context_cache={};self.partner_catalog=None
            self.settings={};self.quant_results={};self.cards_by_symbol={};self.decisions={};self.opportunities=[];self.manual={};self.deep_queue=[];self.attempted={}
            self.chart={"symbol":"","timeframe":"H1","bars":[],"cards":[]}
            self.risk=RiskManager(self.broker,self.store)
            self.executor=Executor(self.broker,self.store,self.risk,self.clock)
            self.scanner=UniverseScanner(self.broker,self.clock)
            self.scanner.begin();self.last_scan=self.clock();self.status="READ_ONLY"
        self.learning_account=key;self.last_learning=0
        self.learning_state=self.learner.snapshot(key)
        if self.library_error:self.learning_state.update(mode="REFERENCE_UNAVAILABLE",error=self.library_error)
        with self.store.lock:
            saved=self.store.db.execute("SELECT payload FROM financial_scenarios WHERE account=? ORDER BY created DESC LIMIT 1",(key,)).fetchone()
        self.valuation=json.loads(saved[0])["result"] if saved else {}

    def _observe_rules(self,cards):
        if not self.learner:return
        try:self.learner.observe(account_key(self.broker.account()),cards,self.clock())
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            self.learning_state={**self.learning_state,"error":str(exc)}
            self._audit("LEARNING_ERROR",{"reason":str(exc)})

    def _update_learning(self,force=False):
        if not self.learner or not self.broker:return
        now=self.clock()
        try:
            key=account_key(self.broker.account());self._sync_learning_scope(key)
            if not force and now-self.last_learning<60:return
            self.last_learning=now
            intents=self.store.intents(key)
            entries=[i for i in intents if i["kind"]=="ENTRY"]
            since=max(0,min((i["created"] for i in entries),default=now)-60)
            deals=self.broker.deals(since)
            after=account_key(self.broker.account())
            if after!=key:
                self._sync_learning_scope(after)
                raise ValueError("Account changed during learning history fetch; evidence discarded")
            if deals is None:raise ValueError("Broker learning history unavailable")
            self.learner.ingest(key,intents,deals,now,self.broker.is_simulation)
            self.learning_state=self.learner.snapshot(key)
            if self.library_error:self.learning_state.update(mode="REFERENCE_UNAVAILABLE",error=self.library_error)
            # A research mirror is useful to humans and offline tools, but file
            # failure must never interrupt reconciliation or position management.
            try:
                from .learning_journal import persist
                self.learning_state['persistence']=persist(self.learner,key,self.data/'learning-memory',now,
                                                         evaluation=copy.deepcopy(self.learning_state))
                self._last_learning_file_error=None
            except Exception as persistence_error:
                logging.getLogger(__name__).exception("Handled boundary failure")
                self.learning_state['persistence']={'ok':False,'error':str(persistence_error),'mode':'SHADOW_ONLY'}
                if getattr(self,'_last_learning_file_error',None)!=str(persistence_error):
                    self._audit('LEARNING_FILE_ERROR',{'reason':str(persistence_error)})
                self._last_learning_file_error=str(persistence_error)
            self.learning_state["updated_at"]=now
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            self.learning_state={**self.learning_state,"error":str(exc)}
            self._audit("LEARNING_ERROR",{"reason":str(exc)})

    def _export_knowledge(self):
        from .learning import knowledge_export_sources
        if not self.learner or not self.broker:raise ValueError("اتصل بمصدر البيانات لحفظ ذاكرة التعلم")
        verified_learning_reference=_verified_learning_export_reference(self.root)
        self._update_learning(force=True)
        key=account_key(self.broker.account());payload=self.learner.export(key)
        for field in ("error","mode","updated_at","persistence"):
            if field in self.learning_state:payload["evaluation"][field]=self.learning_state[field]
        payload["schools"]=self.knowledge
        payload["current_rules"]=list(self.rule_library.values())
        payload["source_archive"],source_files=knowledge_export_sources(self.root,payload["reference"]+payload["current_rules"])
        if (self.root/"docs/knowledge/multi-school-reference.json").exists():
            from .multischool import MODULES
            payload["multi_school_reference"]=self._load_multi_reference()
            for name in MODULES:source_files["multi-school-source/"+name]=(self.root/"src/nexus"/name).read_bytes()
        valuation_reference=self.root/"docs/knowledge/valuation-reference.json"
        if valuation_reference.exists():payload["valuation_reference"]=json.loads(valuation_reference.read_text(encoding="utf-8"))
        if verified_learning_reference is not None:
            payload["learning_reference"]=verified_learning_reference
        reference=self._load_execution_reference()
        if reference:payload["execution_reference"]=reference
        else:payload["execution_reference_error"]=self.execution_reference_error
        self._execution_tables()
        with self.store.lock:
            payload["financial_scenarios"]=[json.loads(row[0]) for row in self.store.db.execute("SELECT payload FROM financial_scenarios WHERE account=? ORDER BY created",(key,))]
            payload["school_reference_versions"]=[json.loads(row[0]) for row in self.store.db.execute("SELECT payload FROM school_reference_versions ORDER BY revision")]
            payload["execution_reference_versions"]=[json.loads(row[0]) for row in self.store.db.execute("SELECT payload FROM execution_reference_versions ORDER BY revision")]
        target=self.data/"knowledge-exports";target.mkdir(exist_ok=True)
        stamp=datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        path=target/("Quant-Trading-AI-knowledge-learning-"+stamp+".zip")
        with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("knowledge-learning.json",json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False))
            if self.learning_state.get('persistence',{}).get('ok'):
                from .learning_journal import read_snapshot
                mirror=read_snapshot(self.data/'learning-memory',key)
                bundle.writestr('learning-state.json',json.dumps(mirror,ensure_ascii=False,indent=2,allow_nan=False))
            for member,blob in sorted(source_files.items()):bundle.writestr(member,blob)
            bundle.writestr("readme.txt","Local rule reference, current school catalog, verified shared dependency sources and observational results; no account credentials. Source files are inert review material, not dynamically executed. Check source_archive.complete and source_archive.missing in knowledge-learning.json: legacy dependencies may be unavailable. Source coverage does not mean a school is complete. Evaluations do not modify live code or risk. Prior to promotion require cost-adjusted chronological tests and Demo review.")
        complete=payload["source_archive"]["complete"]
        self._audit("KNOWLEDGE_EXPORTED",{"path":str(path),"rules":len(self.rule_library),"source_archive_complete":complete,"missing_sources":len(payload["source_archive"]["missing"])})
        message="حُفظ مرجع المدارس وذاكرة التعلم محليًا" if complete else "حُفظ مرجع المدارس وذاكرة التعلم؛ بعض ملفات المصدر التاريخية غير متاحة ومُبيّنة في التصدير"
        return {"ok":True,"path":str(path),"source_archive_complete":complete,"missing_sources":len(payload["source_archive"]["missing"]),"message":message}

    def _publish(self):
        # A transient MT5 IPC failure must not erase the evidence needed to
        # diagnose it.  Keep the last broker-backed snapshot, while replacing
        # coordinator-owned fields (cards, research, scan and audit journal)
        # with their current in-memory/SQLite values below.
        with self.view_lock:
            previous=self._view
        view=self._empty_state();view.update(status=self.status,error=self.error,last_update=self.last_update,chart=self.chart,
            settings=self.settings,opportunities=self.opportunities,cards=[c for cards in self.cards_by_symbol.values() for c in cards],
            quant_results=list(self.quant_results.values()))
        if self.broker:
            execution=self.executor.status() if self.executor else {}
            view.update(simulation=self.broker.is_simulation,mode=execution.get("mode","READ_ONLY"),execution=execution,
                        scan=self.scanner.snapshot() if self.scanner else view["scan"])
            if self.store:
                # These reads do not depend on a healthy terminal connection.
                view["events"]=self.store.recent_audit(150)
                view["intents"]=self.store.intents()
            try:
                account=self.broker.account();terminal=self.broker.terminal();key=account_key(account)
                if self.learner:
                    self._sync_learning_scope(key)
                    view.update(learning=self.learning_state,valuation=self.valuation,chart=self.chart,settings=self.settings,
                                opportunities=self.opportunities,cards=[c for cards in self.cards_by_symbol.values() for c in cards],quant_results=list(self.quant_results.values()))
                account["type"]={0:"Demo",1:"Contest",2:"Real"}.get(account.get("trade_mode"),"UNKNOWN") if type(account.get("trade_mode")) is int else "UNKNOWN"
                intents=self.store.intents(key)
                view.update(simulation=self.broker.is_simulation,account=account,terminal=terminal,
                    mode=self.executor.status().get("mode","READ_ONLY"),execution=self.executor.status(),scan=self.scanner.snapshot(),
                    positions=self.broker.positions(),orders=self.broker.orders(),intents=intents,
                    events=self.store.recent_audit(150),performance=self._performance(intents),
                    news=self.news.snapshot(self.broker.calendar(),self.broker.is_simulation))
                if self.risk.settings:
                    view["risk"]=self.risk.snapshot(self.clock())
                else:
                    day=self.store.get_day(key,self.clock())
                    view["risk"]={**(day or {}),"configured":False,"note":"حدود اليوم السابق تظل محفوظة؛ أعد التفويض لحساب النتائج الحالية."}
                view["scalping"]=self._refresh_scalping()
            except Exception as exc:
                logging.getLogger(__name__).exception("Handled boundary failure")
                # Preserve the last successfully observed broker values for
                # incident review.  DATA_ERROR/data_stale make their age clear;
                # current cards, quant results, scan and journal stay current.
                for field in ("account","terminal","positions","orders","performance","news","risk"):
                    if previous.get(field) is not None:
                        view[field]=previous[field]
                view["error"]=str(exc);view["status"]="DATA_ERROR";view["data_stale"]=True
        # A revoked executor must never retain a successful-looking coordinator
        # status. Keep terminal/data errors and explicit user stop states intact.
        if view["status"] in ("AUTO_DEMO","MANUAL_DEMO") and view.get("mode")=="READ_ONLY":
            view["status"]="READ_ONLY"
            self.status="READ_ONLY"
        # Detach all actor-owned mutable values once. This preserves the exact
        # public JSON schema and every card without a Python recursive walk.
        raw=self._encode_view(view);published=json.loads(raw)
        with self.view_lock:
            self._view=published;self._json_view_ref=published;self._json_view_bytes=raw

    def _loop(self):
        try:self._run_loop()
        finally:
            with self._action_result_lock:self.running=False
            self._reject_pending_actions()

    def _run_loop(self):
        while self.running:
            try:
                fast=False
                try:
                    payload,future=self.commands.get(timeout=.01 if self._fast_enabled() else .5)
                except queue.Empty:payload=future=None
                if payload:
                    if not self._claim_worker_step(future):
                        self._settle_action(future,error=ValueError("الخدمة توقفت قبل تنفيذ الإجراء؛ لم يُنفذ"))
                    else:
                        try:
                            result=self._action(payload)
                            self._settle_action(future,result=result)
                        except Exception as exc:
                            logging.getLogger(__name__).exception("Handled boundary failure")
                            # Complete the request even if writing its audit fails.
                            self._settle_action(future,error=exc)
                            self.error=str(exc);self._audit("ACTION_REJECTED",{"action":payload["action"],"reason":str(exc)})
                        except BaseException:
                            # A terminated worker cannot certify the outcome of
                            # already-started I/O. Never invite a command replay.
                            self._settle_action(future,error=RuntimeError("توقف العامل قبل تأكيد نتيجة الإجراء؛ لا تُعد إرساله تلقائيًا"))
                            raise
                # Claim the next broker/research cycle only after command
                # handling. A shutdown command must not begin another cycle.
                if not self._claim_worker_step():break
                if self.broker:
                    now=self.clock()
                    try:
                        terminal=self.broker.terminal()
                    except Exception as exc:
                        if not self._recover_mt5_connection(exc):
                            raise
                        terminal=self.broker.terminal()
                    if not terminal.get("connected"):
                        self.executor.deactivate("انقطاع الاتصال؛ يلزم مطابقة الحساب وإعادة التفعيل")
                        self.status="DISCONNECTED";self.error="انقطاع MT5. الدخول الجديد متوقف."
                    else:
                        if self.learner:self._sync_learning_scope(account_key(self.broker.account()))
                        # Reconciliation is read-only and also runs after an
                        # ambiguous response/restart; it never reactivates auth.
                        self.executor.reconcile()
                        if self.status=="DISCONNECTED":
                            # A recovered terminal stays fail-closed, but the UI
                            # must no longer claim the terminal is disconnected.
                            self.status=self.executor.status().get("mode","READ_ONLY")
                            self.error=""
                            self._audit("CONNECTION_RESTORED_READ_ONLY",{"mode":self.status})
                        if self.executor.status().get("mode") in ("AUTO_DEMO","MANUAL_DEMO"):
                            self.executor.manage()
                        fast=self._fast_enabled()
                        if fast:
                            ready=self._run_fast_batch()
                            if not self._priority_yield_requested():
                                self._fast_scan_step()
                                if not ready:
                                    try:self._fast_background_step()
                                    except Exception as exc:
                                        logging.getLogger(__name__).exception("Handled boundary failure")
                                        self._fast_background_job=None
                                        self._audit("ANALYSIS_ERROR",{"lane":"BACKGROUND","reason":str(exc)})
                                if not self._priority_yield_requested():
                                    self._collect_quant();self._trade_candidates()
                                    if self.clock()-self.last_learning>=FAST_BACKGROUND_SECONDS:self._update_learning()
                        else:
                            if self.scanner.queue:
                                self.scanner.step(8)
                                if self.scanner.snapshot()["complete"]:
                                    self.deep_queue=[r["symbol"] for r in self.scanner.candidates(len(self.scanner.rows))]
                            elif not self.deep_queue and now-self.last_deep>=60:
                                if now-self.last_scan>=300:
                                    self.scanner.begin();self.last_scan=now
                                else:
                                    self.deep_queue=[r["symbol"] for r in self.scanner.candidates(len(self.scanner.rows))]
                            if self.deep_queue and not self.scanner.queue:
                                symbol=self.deep_queue.pop(0)
                                try:self._analyze_symbol(symbol)
                                except Exception as exc:
                                    logging.getLogger(__name__).exception("Handled boundary failure")
                                    self._audit("ANALYSIS_ERROR",{"symbol":symbol,"reason":str(exc)})
                                self.last_deep=now
                            self._collect_quant();self._trade_candidates();self._update_learning()
                        self.last_update=self.clock()
                if (not fast or not self._priority_yield_requested()) and self.clock()-self.news.last_attempt>=900:self.news.refresh()
                if fast and (self._priority_yield_requested() or self._fast_monotonic()-self._fast_publish_at<FAST_PUBLISH_SECONDS):
                    self._publish_fast_controls()
                else:
                    self._publish()
                    if fast:self._fast_publish_at=self._fast_monotonic()
            except Exception as exc:
                self.error=str(exc);self.status="DISCONNECTED" if isinstance(exc,BrokerError) else "ERROR"
                if self.executor:self.executor.deactivate("تعذر تحقق العمليات أو المخاطر: "+str(exc))
                LOG.exception("coordinator failure")
                self._publish()
                time.sleep(.5)

    def _diagnostics(self):
        state=self.snapshot();account=state.get("account") or {}
        if account:account["login"]="***"+str(account.get("login",""))[-4:];account.pop("name",None)
        # No session token, broker password or terminal credentials are stored.
        target=self.data/"diagnostics";target.mkdir(exist_ok=True)
        stamp=datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        report=target/("Quant-Trading-AI-diagnostics-"+stamp+".zip")
        events=state.get("events") or []
        error_history=[e for e in events if str(e.get("kind",e.get("event",""))).upper() in
                  ("ERROR","ANALYSIS_ERROR","ACTION_REJECTED","QUANT_ERROR","LEARNING_ERROR","LEARNING_FILE_ERROR")]
        active_errors=[]
        if state.get("error"):
            active_errors.append({"event":"CURRENT_STATE_ERROR","at":state.get("last_update"),"payload":{"reason":str(state["error"])}})
        if (state.get("learning") or {}).get("error"):
            active_errors.append({"event":"CURRENT_LEARNING_ERROR","at":state.get("last_update"),"payload":{"reason":str(state["learning"]["error"])}})
        persistence=(state.get('learning') or {}).get('persistence',{})
        if persistence.get('ok') is False:
            active_errors.append({'event':'CURRENT_LEARNING_FILE_ERROR','at':state.get('last_update'),
                                  'payload':{'reason':str(persistence.get('error','Learning mirror unavailable'))}})
        learning_mirror=None
        if persistence.get('ok') and getattr(self,'learning_account',None):
            try:
                from .learning_journal import read_snapshot
                learning_mirror=read_snapshot(self.data/'learning-memory',self.learning_account)
            except Exception as mirror_error:
                logging.getLogger(__name__).exception("Handled boundary failure")
                active_errors.append({'event':'CURRENT_LEARNING_FILE_ERROR','at':state.get('last_update'),
                                      'payload':{'reason':str(mirror_error)}})
        if (state.get("knowledge") or {}).get("error"):
            active_errors.append({"event":"CURRENT_KNOWLEDGE_ERROR","at":state.get("last_update"),"payload":{"reason":str(state["knowledge"]["error"])}})
        errors=active_errors+error_history
        decisions=[e for e in events if e.get("event")=="COMMITTEE_DECISION"]
        cards=state.get("cards") or []
        card_status_counts={}
        diagnostic_cards=[]
        for card in cards:
            strategy_id=str(card.get("strategy_id") or card.get("registry_id") or card.get("strategy") or "unknown")
            status=str(card.get("status") or "UNKNOWN")
            key=strategy_id+":"+status
            card_status_counts[key]=card_status_counts.get(key,0)+1
            diagnostic_cards.append({k:card.get(k) for k in
                ("strategy_id","school","symbol","timeframe","coverage","status","quality","direction",
                 "data_time","expires_at","data_requirements","news_requirements","conditions_missing","gaps")})
        blocking_reason_counts={}
        for event in decisions:
            payload=event.get("payload") or {}
            reasons=payload.get("reason_codes") or payload.get("reasons") or []
            for reason in reasons:
                key=str(reason)
                blocking_reason_counts[key]=blocking_reason_counts.get(key,0)+1
        terminal=state.get("terminal") or {}
        scan=state.get("scan") or {}
        market_exclusion_reason_counts={}
        for row in scan.get("rows") or []:
            if not row.get("checked") or row.get("eligible"):
                continue
            reasons=row.get("reasons") or []
            if isinstance(reasons,str):
                reasons=[reasons]
            for reason in reasons:
                key=str(reason)
                market_exclusion_reason_counts[key]=market_exclusion_reason_counts.get(key,0)+1
        calendar=((state.get("news") or {}).get("calendar") or {})
        execution=state.get("execution") or {}
        current_blockers=[]
        if state.get("error"):
            current_blockers.append({"code":"current_state_error","message":str(state["error"])})
        if not terminal.get("connected"):
            current_blockers.append({"code":"terminal_disconnected","message":"MT5 terminal is not connected"})
        if terminal.get("connected") and terminal.get("trade_allowed") is not True:
            current_blockers.append({"code":"terminal_algo_trading_disabled","message":"MT5 Algo Trading permission is disabled"})
        if terminal.get("tradeapi_disabled") is True:
            current_blockers.append({"code":"terminal_trade_api_disabled","message":"MT5 Python/API trading is disabled"})
        if calendar.get("ok") is not True:
            current_blockers.append({"code":"bridge_or_calendar_unavailable","message":str(calendar.get("reason") or "Bridge calendar data is unavailable")})
        if execution.get("entries_paused"):
            current_blockers.append({"code":"entries_paused","message":str(execution.get("reason") or "New entries are paused")})
        if scan.get("complete") and scan.get("eligible")==0:
            current_blockers.append({"code":"no_eligible_symbols","message":"Completed market scan found no eligible symbols"})
        scan_summary={key:scan.get(key) for key in
                      ("discovered","checked","eligible","excluded","complete","cycle","cycle_started","cycle_finished")}
        summary={
            "schema":"nexus-ai-diagnostics-v1",
            "app_name":state.get("app_name"),"app_version":state.get("version"),
            "generated_at_utc":datetime.now(UTC).isoformat(),
            "mode":state.get("mode"),
            "status":state.get("status"),
            "error":state.get("error"),
            "data_stale":bool(state.get("data_stale")),
            "connected":bool((state.get("terminal") or {}).get("connected")),
            "scan":scan_summary,
            "positions":len(state.get("positions") or []),
            "orders":len(state.get("orders") or []),
            "current_blockers":current_blockers,
            "errors":errors,
            "active_errors":active_errors,
            "error_history":error_history,
            "errors_scope":"errors combines active_errors and historical audit entries. Historical entries are not proof of a current fault; inspect active_errors and current_blockers for the current snapshot.",
            "recent_decisions":decisions[:50],
            "blocking_reason_counts":dict(sorted(blocking_reason_counts.items(),key=lambda item:(-item[1],item[0]))),
            "market_exclusion_reason_counts":dict(sorted(market_exclusion_reason_counts.items(),key=lambda item:(-item[1],item[0]))),
            "recent_events":events[:150],
            "strategy_coverage":state.get("coverage") or [],
            "card_status_counts":dict(sorted(card_status_counts.items())),
            "cards_total":len(diagnostic_cards),
            "cards_included":len(diagnostic_cards),
            "cards_truncated":False,
            "cards":diagnostic_cards,
            "quant_results":state.get("quant_results") or [],
            "learning":state.get("learning") or {},
            "fast_scheduler":state.get("fast_scheduler") or {},
            "knowledge":state.get("knowledge") or {},
            "note":"AI-readable local report. No automatic upload. Review before sharing.",
        }
        with zipfile.ZipFile(report,"w",zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("state.json",json.dumps(state,ensure_ascii=False,indent=2,allow_nan=False))
            bundle.writestr("ai-report.json",json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False))
            if learning_mirror is not None:
                bundle.writestr('learning-state.json',json.dumps(learning_mirror,ensure_ascii=False,indent=2,allow_nan=False))
            bundle.writestr("readme.txt","Local diagnostics. Account number masked in summary. Audit may contain tickets and account identity. Review before sharing. No automatic upload.")
            if self.store:
                # SQLite backup API produces a consistent copy while WAL is active.
                backup_path=target/("snapshot-"+stamp+".sqlite3")
                destination=sqlite3.connect(str(backup_path))
                with self.store.lock:self.store.db.backup(destination)
                destination.close();bundle.write(backup_path,"journal.sqlite3");backup_path.unlink()
            log=self.data/"nexus.log"
            if log.exists():bundle.write(log,"nexus.log")
        return {"ok":True,"message":"جُمعت ملفات التشخيص محليًا. لا ترفع تلقائيًا. راجع أرقام الحساب والتذاكر قبل مشاركتها.","path":str(report)}
