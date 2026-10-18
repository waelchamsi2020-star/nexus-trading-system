"""Non-browser headless packaged-service smoke test. No MT5 orders are sent."""
import argparse
import json
import logging
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


def session(url):
    with urllib.request.urlopen(url,timeout=5) as response:raw=response.read().decode("utf-8")
    return re.search(r'<meta name="nexus-token" content="([^"]+)">',raw).group(1)


def request(url,token,payload=None,*,timeout=20):
    headers={"X-Nexus-Token":token,"Content-Type":"application/json"}
    path="/api/action" if payload is not None else "/api/state"
    data=json.dumps(payload).encode("utf-8") if payload is not None else None
    try:
        with urllib.request.urlopen(urllib.request.Request(url+path,headers=headers,data=data),timeout=timeout) as response:result=json.load(response)
        if not result.get('queued'):return result
        request_id=result.get('request_id','')
        if re.fullmatch('[0-9a-f]{32}',request_id) is None:
            raise RuntimeError('Queued action lacks a tracking ID; do not replay it')
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            time.sleep(.4)
            with urllib.request.urlopen(urllib.request.Request(url+'/api/action-result?id='+request_id,headers=headers),timeout=20) as response:
                receipt=json.load(response)
            if receipt.get('ok') is False:raise RuntimeError(receipt.get('error','Action result unavailable; do not replay'))
            if receipt.get('status')=='PENDING':continue
            if receipt.get('status')!='COMPLETE' or not isinstance(receipt.get('result'),dict):
                raise RuntimeError('Invalid action completion; do not replay')
            return receipt['result']
        raise RuntimeError('Action completion tracking timed out; do not replay it')
    except urllib.error.HTTPError as exc:
        detail=exc.read(4096).decode("utf-8",errors="replace")
        raise RuntimeError(f"API HTTP {exc.code}: {detail}") from exc


def main():
    root=Path(__file__).resolve().parents[1]
    expected_models=len(json.loads((root/"docs/knowledge/library.json").read_text(encoding="utf-8"))["rules"])
    parser=argparse.ArgumentParser();parser.add_argument("--exe",default=str(root/"Windows"/"Quant Trading AI"/"Quant Trading AI.exe"));parser.add_argument("--port",type=int,default=8767)
    parser.add_argument("--data-dir",required=True);parser.add_argument("--output",default=str(root/"reports"/"packaged-service-smoke.json"))
    args=parser.parse_args();url=f"http://127.0.0.1:{args.port}"
    command=[args.exe,"--headless","--no-connect","--port",str(args.port),"--data-dir",args.data_dir]
    child=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    report={"type":"PACKAGED_HEADLESS_SMOKE","at_utc":datetime.now(UTC).isoformat(),"gui_visual_verified":False,"orders_sent_to_mt5":0}
    token=None
    try:
        for attempt in range(40):
            if child.poll() is not None:raise RuntimeError(f"Packaged service exited ({child.returncode}) before initialization")
            try:token=session(url);break
            except Exception:
                logging.getLogger(__name__).exception("Handled boundary failure")
                time.sleep(.25)
        if not token:raise RuntimeError("Packaged service did not become ready")
        with urllib.request.urlopen(url+"/i18n.js",timeout=5) as response:
            assert "NEXUS_I18N" in response.read().decode("utf-8")
        report["bilingual_asset_served"]=True
        state=request(url,token);assert state["mode"]=="READ_ONLY" and state["account"] is None
        report["initial_read_only"]=True
        request(url,token,{"action":"simulation"})
        for attempt in range(40):
            state=request(url,token)
            if state.get("simulation") and state["scan"]["complete"]:break
            time.sleep(.25)
        assert state["simulation"] and state["scan"]["complete"]
        assert state["scan"]["discovered"]==6 and state["scan"]["checked"]==6
        report["synthetic_scan"]=state["scan"];report["simulation_clearly_marked"]=True
        verified_timeframes=[]
        for timeframe in ("M1","M5","H1","D1","MN1"):
            request(url,token,{"action":"chart","symbol":"GOLD#","timeframe":timeframe})
            for attempt in range(20):
                state=request(url,token)
                if state.get("chart",{}).get("symbol")=="GOLD#" and state["chart"].get("timeframe")==timeframe:break
                time.sleep(.25)
            assert state["chart"]["timeframe"]==timeframe and len(state["chart"]["cards"])==expected_models and len(state["chart"]["bars"])>=100
            verified_timeframes.append(timeframe)
        report["chart_cards"]=len(state["chart"]["cards"]);report["embedded_assets_served"]=True
        report["timeframes_verified"]=verified_timeframes
        assert len(state["knowledge"]["schools"])==58
        assert state['app_name']=='Quant Trading AI'
        assert state["learning"]["library_rules"]==expected_models
        exported=request(url,token,{"action":"knowledge_export"})
        assert exported.get("ok") and Path(exported["path"]).exists()
        report["school_references"]=58;report["learning_export_verified"]=True
        valued=request(url,token,{'action':'fundamental_analyze','data':{'model':'pv','asset':'SYNTHETIC_FIXTURE','source':'Packaged smoke synthetic fixture','currency':'USD','as_of':2000,'published_at':1000,'discount_rate':.1,'cashflows':[110]}})
        assert valued.get('ok') and abs(valued['valuation']['present_value']-100)<1e-9
        assert not valued['valuation']['execution_authority']
        report['local_valuation_verified']=True
        second=subprocess.run(command,check=False,capture_output=True,timeout=15)
        report["second_instance_exit_code"]=second.returncode
        assert second.returncode!=0
        report["same_process_guard_verified"]=True
        request(url,token,{"action":"diagnostics"})
        report["local_diagnostics_action"]=True
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
        output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8");print(json.dumps({k:v for k,v in report.items() if k!="synthetic_scan"},ensure_ascii=False))

if __name__=="__main__":main()
