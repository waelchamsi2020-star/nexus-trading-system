"""Actual broker verification. No order_send, execution authorization or trades."""
import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"src"))
from nexus.broker import MT5Broker
from nexus.engine import resources
from nexus.market import UniverseScanner
from nexus.news import NewsManager


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--terminal",default="");parser.add_argument("--bridge",default="")
    parser.add_argument("--output",default=str(root/"reports"/"actual-mt5-readonly.json"));args=parser.parse_args()
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    broker=MT5Broker(args.terminal,args.bridge)
    try:
        now=time.time();a=broker.account();t=broker.terminal();symbols=broker.symbols()
        scanner=UniverseScanner(broker);scanner.begin()
        while scanner.queue:scanner.step(16)
        scan=scanner.snapshot()
        categories={}
        for row in scan["rows"]:categories[row["category"]]=categories.get(row["category"],0)+1
        news=NewsManager(target.parent/"source-verification.sqlite3");news.refresh(blocking=True)
        representative=next((s for s in symbols if s.get("trade_mode")==4 and s.get("currency_base") and s.get("currency_profit")==a["currency"]),symbols[0])
        name=representative["name"];broker.select(name);tick=broker.tick(name);info=broker.symbol(name)
        # Calculations are read-only and do not represent a trading proposal.
        price=tick["ask"];lot=info["volume_min"];stop=price-info["trade_tick_size"]*100
        profit=broker.calc_profit("BUY",name,lot,price,stop) if stop>0 else None
        margin=broker.calc_margin("BUY",name,lot,price)
        # order_check is a broker-side validation call, never order_send. It
        # also exercises native request enums/filling policy on the real adapter.
        check_request={"action":"DEAL","symbol":name,"side":"BUY","volume":lot,"price":price,"deviation":0,"magic":0,"comment":"NEXUS_READONLY_CHECK"}
        try:
            native_request=broker._request(check_request)
            check_probe={"called":True,"type_filling":native_request["type_filling"],"result":broker.check(check_request),"order_sent":False}
        except Exception as exc:
            logging.getLogger(__name__).exception("Handled boundary failure")
            check_probe={"called":False,"error":str(exc),"order_sent":False}
        report={"type":"ACTUAL_READ_ONLY","at_utc":datetime.now(UTC).isoformat(),"started":now,"finished":time.time(),
            "connected":t["connected"],"server":a["server"],"login_masked":"***"+str(a["login"])[-4:],"account_trade_mode":a["trade_mode"],
            "account_margin_mode":a["margin_mode"],"account_currency":a["currency"],"account_is_demo":a["trade_mode"]==0,
            "broker_package_version":broker.mt5.__version__,"terminal_version":broker.mt5.version(),
            "discovered":len(symbols),"symbols_outside_market_watch_at_start":sum(not s["visible"] for s in symbols),
            "scan":{"discovered":scan["discovered"],"checked":scan["checked"],"eligible":scan["eligible"],"excluded":scan["excluded"],"complete":scan["complete"]},
            "categories":categories,"rows":scan["rows"],"calendar":broker.calendar(),
            "calculation_probe":{"symbol":name,"lot":lot,"open":price,"test_close":stop,"profit_account_currency":profit,"margin_account_currency":margin},
            "order_check_probe":check_probe,"sources":news.snapshot()["sources"],"resources":resources(),
            "orders_sent":0,"limitations":["No trading authorization granted", "No actual fills, cancellations, closures or live interruptions tested",
                "If bridge is absent all sessions remain unverified and automatic entry is ineligible",
                "Outside-Market-Watch case tested with synthetic fixture when broker had none at start"]}
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps({"report":str(target),"demo":report["account_is_demo"],"scan":report["scan"],"calculation_probe":report["calculation_probe"],"orders_sent":0},ensure_ascii=False))
        news.db.close()
    finally:broker.close()

if __name__=="__main__":main()
