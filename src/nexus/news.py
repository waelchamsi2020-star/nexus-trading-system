"""Free official feeds. Facts stay text; feed content cannot invoke code/tools."""
from __future__ import annotations

import concurrent.futures
import email.utils
import hashlib
import html
import json
import logging
import math
import re
import sqlite3
import ssl
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse

import certifi

SOURCES = [
    {"id":"fed","name":"Federal Reserve","url":"https://www.federalreserve.gov/feeds/press_all.xml",
     "currencies":["USD"],"terms_url":"https://www.federalreserve.gov/website-linking-policies.htm",
     "terms":"RSS رسمي منشور للاشتراك؛ تعرض عناوين وروابط فقط مع نسبة المصدر.","enabled":True},
    {"id":"ecb","name":"European Central Bank","url":"https://www.ecb.europa.eu/rss/press.html",
     "currencies":["EUR"],"terms_url":"https://www.ecb.europa.eu/home/disclaimer/html/index.en.html",
     "terms":"RSS رسمي منشور للاشتراك؛ حقوق المصدر محفوظة، لا إعادة نشر مقالات كاملة.","enabled":True},
    {"id":"bls","name":"Bureau of Labor Statistics","url":"https://www.bls.gov/feed/bls_latest.rss",
     "currencies":["USD"],"terms_url":"https://www.bls.gov/bls/linksite.htm",
     "terms":"مصدر حكومي رسمي؛ التوافر غير مضمون وقد يمنع الطلبات الآلية.","enabled":True},
    {"id":"boe","name":"Bank of England","url":"https://www.bankofengland.co.uk/rss/news",
     "currencies":["GBP"],"terms_url":"https://www.bankofengland.co.uk/legal",
     "terms":"الشروط تقيد بعض إعادة الاستخدام بغير التجاري؛ غير مفعل لهذه المؤسسة حتى مراجعة الترخيص.","enabled":False},
]


def parse_timestamp(value):
    if not value:
        return None
    try:
        d=email.utils.parsedate_to_datetime(value)
    except (TypeError,ValueError):
        try:
            d=datetime.fromisoformat(value)
        except ValueError:
            return None
    # Do not silently invent a timezone for an ambiguous publisher date.
    return d.timestamp() if d.tzinfo else None


def text_only(value):
    return html.unescape(re.sub(r"<[^>]*>"," ",value or "")).strip()[:1500]


def fetch_source(source, now=None):
    now=time.time() if now is None else now
    state={**source,"status":"DISABLED" if not source["enabled"] else "ERROR","received_at":now,"last_success":None}
    if not source["enabled"]:
        state["reason"]=source["terms"]
        return state,[]
    try:
        req=urllib.request.Request(source["url"],headers={"User-Agent":"NEXUS/0.1 personal Demo RSS reader","Accept":"application/rss+xml,application/xml,text/xml"})
        # Preserve TLS validation and supplement the system roots with Mozilla's
        # pinned CA bundle. Never use an unverified context on a failed source.
        context=ssl.create_default_context()
        context.load_verify_locations(cafile=certifi.where())
        with urllib.request.urlopen(req,timeout=8,context=context) as response:
            if urlparse(response.url).hostname!=urlparse(source["url"]).hostname:
                raise ValueError("إعادة توجيه خارج المصدر المعتمد")
            raw=response.read(2_000_001)
        if len(raw)>2_000_000 or b"<!ENTITY" in raw.upper() or b"<!DOCTYPE" in raw.upper():
            raise ValueError("رفض XML غير آمن أو كبير")
        root=ET.fromstring(raw)
        items=[]
        entries=root.findall(".//item") or root.findall("{http://www.w3.org/2005/Atom}entry")
        for entry in entries[:40]:
            def field(*names, entry=entry):
                for name in names:
                    e=entry.find(name)
                    if e is not None:
                        return e.text or e.attrib.get("href","")
                return ""
            title=text_only(field("title","{http://www.w3.org/2005/Atom}title"))
            link=field("link","{http://www.w3.org/2005/Atom}link")
            if urlparse(link).scheme not in ("http","https"):
                continue
            date_raw=field("pubDate","{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated")
            published=parse_timestamp(date_raw)
            items.append({"id":hashlib.sha256((source["id"]+link+date_raw).encode()).hexdigest(),
                "title":title,"facts":title,"interpretation":"قد يرتبط البيان بالعملة والسياسة النقدية. اتجاه الأثر غير مستنتج من العنوان.",
                "source":source["name"],"provider":source["name"],"url":link,"source_url":link,
                "event_time":None,"published_at":published,"received_at":now,"timezone":"UTC" if published else "UNKNOWN",
                "publisher_time":date_raw,"currencies":source["currencies"],"assets":source["currencies"],
                "previous":None,"forecast":None,"actual":None,"revision":None,
                "fresh":published is not None and -300<=now-published<=86400*30,
                "coverage":"عنوان رسمي؛ لا يمثل أخبارًا عاجلة شاملة"})
        if not items:
            raise ValueError("المصدر لم ينتج أخبارًا ذات روابط قابلة للفحص")
        state.update(status="OK",last_success=now,reason="تم الوصول والفحص",item_count=len(items))
        return state,items
    except Exception as exc:
        logging.getLogger(__name__).exception("Handled boundary failure")
        state["reason"]=str(exc)
        return state,[]


class NewsManager:
    def __init__(self, path, clock=time.time, fetcher=fetch_source, external_feeds=False):
        self.clock,self.fetcher=clock,fetcher
        self.external_feeds=bool(external_feeds)
        self.lock=threading.RLock(); self.refreshing=False; self.last_attempt=0
        self.db=sqlite3.connect(str(path),check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS cache(id TEXT PRIMARY KEY,payload TEXT)")
        saved=self.db.execute("SELECT payload FROM cache WHERE id='feeds'").fetchone()
        self.sources,self.items=(json.loads(saved[0]) if saved else ([{**s,"status":"PENDING","reason":"لم يُفحص الاتصال بعد"} for s in SOURCES],[]))
        if not self.external_feeds:
            # Old online cache is never presented as current local-only data.
            self.sources,self.items=[],[]

    def refresh(self, blocking=False):
        with self.lock:
            if not self.external_feeds:
                self.last_attempt=self.clock()
                return  # No worker, HTTP client, DNS lookup or feed fetch.
            if self.refreshing:
                return
            self.refreshing=True; self.last_attempt=self.clock()
        def run():
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                    results=list(pool.map(lambda s:self.fetcher(s,self.clock()),SOURCES))
                with self.lock:
                    self.sources=[r[0] for r in results]
                    self.items=sorted([v for r in results for v in r[1]],key=lambda v:v.get("published_at") or 0,reverse=True)
                    self.db.execute("INSERT OR REPLACE INTO cache VALUES('feeds',?)",(json.dumps([self.sources,self.items],ensure_ascii=False,allow_nan=False),));self.db.commit()
            finally:
                with self.lock:
                    self.refreshing=False
        if blocking:
            run()
        else:
            threading.Thread(target=run,name="official-rss",daemon=True).start()

    def snapshot(self, calendar=None, simulation=False):
        with self.lock:
            now=self.clock()
            sources=[{**s,"fresh":s.get("status")=="OK" and 0<=now-(s.get("last_success") or 0)<3600} for s in self.sources]
            if simulation:
                sources=[{"id":"fixture","name":"مصدر صناعي للاختبار","status":"OK","fresh":True,"currencies":["USD","EUR","GBP","JPY"],"last_success":now,"reason":"ليس مصدر أخبار حي"}]
            elif not self.external_feeds:
                calendar=calendar or {}
                fresh=bool(calendar.get("ok") and calendar.get("known") and 0<=now-calendar.get("as_of",0)<=120)
                sources=[{"id":"mt5_calendar","name":"MT5 Economic Calendar","status":"OK" if fresh else "MISSING",
                          "fresh":fresh,"last_success":calendar.get("as_of"),"currencies":[],
                          "reason":"تحليل محلي؛ التقويم من منصة الوسيط فقط؛ مصادر الإنترنت الخارجية معطلة"}]
            items=[{**item,"fresh":isinstance(item.get("published_at"),(int,float)) and
                    -300<=now-item["published_at"]<=86400*30,
                    "source_fresh":any(s.get("fresh") and s["name"]==item.get("source") for s in sources)} for item in self.items]
            return {"sources":sources,"items":[] if simulation or not self.external_feeds else items,"calendar":calendar or {},
                "data_policy":"MT5_ONLY" if not self.external_feeds else "EXTERNAL_FEEDS",
                "refreshing":self.refreshing,"coverage":{"political":False,"breaking_news":False,
                    "note":"لا تغطية شاملة للأحداث السياسية أو الأخبار العاجلة؛ انعدام خبر ليس دليلًا على انعدام حدث."}}

    def gate(self, info, calendar, simulation=False, now=None):
        now=self.clock() if now is None else now
        reasons=[]
        currencies={info.get("currency_profit"), info.get("currency_margin")}
        if info.get("currency_base") and len(info["currency_base"])==3 and info["currency_base"] not in ("XAU","XAG","XPT","XPD"):
            currencies.add(info["currency_base"])
        currencies.discard(None); currencies.discard("")
        if not currencies:
            reasons.append("لا يمكن تعيين التعرض الاقتصادي للعملات")
        if not calendar.get("ok") or not calendar.get("known") or not 0<=now-calendar.get("as_of",0)<=120:
            reasons.append("مصدر التقويم المطلوب غير متاح أو قديم")
        if calendar.get("from_utc",now+1)>now-1800 or calendar.get("to_utc",0)<now+3600:
            reasons.append("نافذة تغطية التقويم غير كافية")
        if not currencies.issubset(set(calendar.get("currencies",[]))):
            reasons.append("التقويم لا يؤكد تغطية جميع العملات المرتبطة")
        state=self.snapshot(calendar,simulation)
        feed_currencies=({c for s in state["sources"] if s.get("fresh") for c in s.get("currencies",[])}
                         if self.external_feeds else set())
        # Official RSS is contextual evidence, not a universal execution gate.
        # Each strategy declares its own ``news_requirements`` and the committee
        # compares those requirements with the coverage flags returned below.
        # Making every currency depend on a matching RSS source blocked otherwise
        # valid calendar-protected proposals (for example JPY/GBP) even though all
        # implemented strategies currently require only the broker calendar.
        # The fresh, currency-complete calendar and its event blackout remain hard
        # gates here and are checked again by RiskManager immediately before send.
        blackout=[]
        for e in calendar.get("events",[]):
            event_time=e.get("time_utc")
            if e.get("currency") in currencies and e.get("importance",0)>=3:
                if not isinstance(event_time,(int,float)) or isinstance(event_time,bool) or not math.isfinite(event_time) or event_time<=0:
                    blackout.append(e)
                    reasons.append("توقيت حدث مرتفع الأهمية غير مؤكد")
                    continue
                # Date-only events have no reliable intraday window: veto that date.
                if e.get("time_mode",0) not in (0,1,2,3):
                    blackout.append(e);reasons.append("نوع توقيت الحدث غير معروف")
                elif e.get("time_mode",0)!=0:
                    if event_time and int(event_time//86400)==int(now//86400):
                        blackout.append(e)
                elif now-1800<=event_time<=now+1800:
                    blackout.append(e)
        if blackout:
            reasons.append("فترة حظر قبل/بعد حدث مرتفع الأهمية")
        return {"ok":not reasons,"coverage":{"calendar":calendar.get("ok",False),"official_feeds":currencies.issubset(feed_currencies),"political":False},
                "blackout":bool(blackout),"events":blackout,"reasons":reasons,"currencies":sorted(currencies),"as_of":now}
