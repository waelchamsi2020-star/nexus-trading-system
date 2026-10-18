"""Actual MT5 connection through the packaged coordinator, READ_ONLY throughout."""
import argparse
import json
import logging
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path

from smoke_service import request, session


def main():
    root=Path(__file__).resolve().parents[1]
    expected_models=len(json.loads((root/"docs/knowledge/library.json").read_text(encoding="utf-8"))["rules"])
    parser=argparse.ArgumentParser()
    parser.add_argument("--exe",default=str(root/"Windows"/"Quant Trading AI"/"Quant Trading AI.exe"))
    parser.add_argument("--terminal",required=True)
    parser.add_argument("--data-dir",required=True)
    parser.add_argument("--port",type=int,default=8769)
    parser.add_argument("--output",default=str(root/"reports"/"packaged-mt5-readonly.json"))
    args=parser.parse_args();url=f"http://127.0.0.1:{args.port}"
    child=subprocess.Popen([args.exe,"--headless","--no-connect","--port",str(args.port),"--data-dir",args.data_dir],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    report={"type":"ACTUAL_PACKAGED_READ_ONLY","at_utc":datetime.now(UTC).isoformat(),"gui_visual_verified":False,"trading_activation_requested":False,"orders_sent_to_mt5":0}
    token=None
    try:
        for attempt in range(60):
            if child.poll() is not None:raise RuntimeError(f"Packaged process exited before startup ({child.returncode})")
            try:token=session(url);break
            except Exception:
                logging.getLogger(__name__).exception("Handled boundary failure")
                time.sleep(.25)
        if token is None:raise RuntimeError("Packaged service did not become ready")
        result=request(url,token,{"action":"connect","terminal_path":args.terminal})
        if not result.get("ok"):raise RuntimeError(str(result))
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            state=request(url,token,timeout=60)
            assert state["mode"]=="READ_ONLY", "Read-only mode must remain enforced"
            if state.get("account") and state["scan"]["complete"]:break
            time.sleep(.5)
        account=state.get("account") or {}
        assert state.get('execution_reference',{}).get('verified') is True, 'Packaged execution reference must match bundled source'
        report['execution_reference_verified']=True
        assert account.get("trade_mode")==0, "Actual Demo account required"
        assert state["scan"]["complete"] and state["scan"]["discovered"]>0
        assert state["scan"]["checked"]==state["scan"]["discovered"]
        assert not state.get("intents"), "Read-only startup must not create trading intents"
        chart_result=request(url,token,{"action":"chart","symbol":"EURUSD","timeframe":"H1"})
        assert chart_result.get("ok"), chart_result
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=request(url,token)
            chart=state.get("chart") or {}
            if chart.get("symbol")=="EURUSD" and len(chart.get("cards",[]))==expected_models:break
            time.sleep(.5)
        assert len(chart.get("cards",[]))==expected_models, "All registered models must analyze actual MT5 bars"
        assert state["app_name"]=="Quant Trading AI"
        assert len(state["knowledge"]["schools"])==58
        assert state["learning"]["library_rules"]==expected_models and not state["learning"]["error"]
        assert all(len(c.get('rule_revision',''))==64 for c in chart['cards'])
        report.update(school_references=58,rule_versions=expected_models,actual_cards_versioned=True)
        assert all(c["coverage"]=="IMPLEMENTED" for c in chart["cards"])
        assert not state.get("intents") and state["mode"]=="READ_ONLY"
        report["actual_chart_models"]=[{k:c.get(k) for k in ("strategy_id","version","status")} for c in chart["cards"]]
        report.update(connected=True,mode=state["mode"],server=account.get("server"),account_login_masked="***"+str(account.get("login"))[-4:],account_is_demo=True,
            scan={k:state["scan"][k] for k in ("discovered","checked","eligible","excluded","complete")},read_only_no_intents=True)
        request(url,token,{"action":"shutdown"});child.wait(timeout=15)
        assert child.returncode==0
        report.update(passed=True,exit_code=child.returncode)
    except Exception as exc:
        report.update(passed=False,error=str(exc));raise
    finally:
        if child.poll() is None:
            try:
                if token:request(url,token,{"action":"shutdown"})
                child.wait(timeout=10)
            except Exception:
                logging.getLogger(__name__).exception("Handled boundary failure")
                child.terminate();child.wait(timeout=5)
        target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
