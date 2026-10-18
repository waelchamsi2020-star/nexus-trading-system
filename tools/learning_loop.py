"""One daily shadow cycle from an explicit account export; never connects to MT5."""
import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from nexus.learning.drift_monitor import monitor_schools
from nexus.learning.proposals import ProposalStore
from nexus.learning.sandbox import evaluate_proposal


def run_cycle(document, db_path, evidence_path, day):
    date.fromisoformat(day)
    account=document['account_key']
    store=ProposalStore(db_path,account)
    try:
        monitors=monitor_schools(document.get('schools',[]));results=[]
        for row in monitors:
            if not row['alert']:continue
            candidate=next((x for x in document.get('candidates',[]) if
                            (x['school_id'],x['revision'],x['symbol'],x['timeframe'])==
                            (row['school_id'],row['revision'],row['symbol'],row['timeframe'])),None)
            identity=hashlib.sha256(json.dumps([account,day,row],sort_keys=True).encode()).hexdigest()
            pid=store.create_proposal('DRIFT_REVIEW',row,{'review_required':True,'candidate':candidate},evidence_path,identity)
            try:
                result=evaluate_proposal({'id':pid},candidate['paired_heldout'] if candidate else [])
            except (ValueError, TypeError, KeyError, ArithmeticError, RuntimeError) as exc:
                # A partial evaluation cannot become a research approval or leak partial metrics.
                # A failed rejection write still propagates; no authority is granted.
                result={'status':'REJECT_SANDBOX_ERROR','error_type':type(exc).__name__,
                        'execution_authority':False,'live_mutation':False}
            # Passing the sandbox leaves PENDING for explicit research review.
            # It never grants live authority or applies proposed values.
            if result['status'].startswith('REJECT'):store.reject_proposal(pid,result['status'])
            results.append({'id':pid,'sandbox':result})
        return {'day':day,'mode':'SHADOW_ONLY','monitors':monitors,'proposals':results,
                'execution_authority':False,'live_mutation':False,'account_partitions':1}
    finally:store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--db',type=Path,required=True)
    parser.add_argument('--day',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=run_cycle(json.loads(args.input.read_text(encoding='utf-8')),args.db,args.input,args.day)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(report))
