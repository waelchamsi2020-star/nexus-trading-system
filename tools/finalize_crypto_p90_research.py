from __future__ import annotations
import json, math, sqlite3, statistics, subprocess, time
from datetime import datetime, UTC
from pathlib import Path

CONFIG = Path(r'C:\Users\PROZO\AppData\Local\NEXUS\demo-live-20261019\config.json')
DB = CONFIG.parent / 'trades.db'
OUT = Path(r'C:\Users\PROZO\Documents\Codex\2026-09-30\files-pasted-by-the-user-nexus\work\candidate-0.6.33\outputs')
PID = 27328
START_AUDIT = 1179
PAIRS = [('BTCUSD','M15'),('BTCUSD','H1'),('ETHUSD','M15'),('ETHUSD','H1')]
REASONS = ['NO_APPROVED_H1_EXECUTION_STRATEGY', 'USD_1_AND_5_TARGETS_INCOMPATIBLE_WITH_MEASURED_CRYPTO_ATR']

def alive(pid):
    try:
        p = subprocess.run(['powershell','-NoProfile','-Command',f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | Select-Object -ExpandProperty CommandLine"],capture_output=True,text=True,timeout=10)
        cmd = p.stdout.strip()
        return bool(cmd and 'crypto_p90_four_hour.py' in cmd and '--duration 14400' in cmd)
    except Exception:
        return False

def pct(row):
    ratio = row.get('p90_spread_to_target_ratio')
    return (float(ratio)*100) if ratio is not None else None

while alive(PID):
    time.sleep(20)

conn = sqlite3.connect(DB, timeout=30)
conn.execute('PRAGMA busy_timeout=30000')
final = conn.execute("SELECT id,event,payload FROM audit WHERE event IN ('CRYPTO_P90_FOUR_HOUR_MEASUREMENT_COMPLETE','CRYPTO_P90_FOUR_HOUR_MEASUREMENT_INCOMPLETE') ORDER BY id DESC LIMIT 1").fetchone()
measurement = json.loads(final[2]) if final else None
if not measurement or measurement.get('start_audit_id') != START_AUDIT:
    sample = conn.execute("SELECT id,payload FROM audit WHERE event='CRYPTO_P90_LIVE_MEASUREMENT_SAMPLE' AND json_extract(payload,'$.start_audit_id')=? ORDER BY id DESC LIMIT 1", (START_AUDIT,)).fetchone()
    sample_payload = json.loads(sample[1]) if sample else {}
    elapsed = float(sample_payload.get('elapsed_seconds',0))
    rows=[]
    symbols=sample_payload.get('symbols',{})
    for symbol, frame in PAIRS:
        s=symbols.get(symbol,{})
        spreads=s.get('p90_spread')
        atr=s.get('frames',{}).get(frame,{}).get('median_atr_samples')
        target=1.5*atr if atr is not None else None
        ratio=(spreads/target) if spreads is not None and target else None
        rows.append({'symbol':symbol,'frame':frame,'median_spread':s.get('median_spread'),'p90_spread':spreads,'median_atr':atr,'target_1_5x_median_atr':target,'p90_spread_to_target_ratio':ratio,'stage3_pass':False,'final_status':'RESEARCH_CANDIDATE'})
    result_audit_id=None
    complete=False
else:
    rows=measurement.get('rows',[])
    elapsed=float(measurement.get('elapsed_seconds',0))
    complete=(final[1]=='CRYPTO_P90_FOUR_HOUR_MEASUREMENT_COMPLETE' and elapsed>=14400 and not measurement.get('failure'))
    result_audit_id=final[0]

by_pair={(r.get('symbol'),r.get('frame')):r for r in rows}
normalized=[]
for symbol,frame in PAIRS:
    r=by_pair.get((symbol,frame), {'symbol':symbol,'frame':frame})
    r=dict(r)
    # Honor the requested final classification; this is research-only and never enables a pair.
    r['final_status']='RESEARCH_CANDIDATE'
    r['classification_reasons']=REASONS
    r['activated']=False
    normalized.append(r)

payload={
  'source_start_audit_id':START_AUDIT,
  'measurement_result_audit_id':result_audit_id,
  'measurement_complete':complete,
  'elapsed_seconds':elapsed,
  'required_seconds':14400,
  'recorded_utc':datetime.now(UTC).isoformat(),
  'classification':'RESEARCH_CANDIDATE',
  'reasons':REASONS,
  'activation_performed':False,
  'symbols':normalized,
  'demo_account':1045864,'server':'Capital.ComMena-Demo','trade_mode':0,
  'EURUSD_7808213_touched':False,
  'authorization_id':json.loads(CONFIG.read_text(encoding='utf-8')).get('authorization_id'),
  'authorization_expiry_utc':datetime.fromtimestamp((json.loads(CONFIG.read_text(encoding='utf-8')).get('authorized_at',0)+json.loads(CONFIG.read_text(encoding='utf-8')).get('authorization_duration_seconds',0)),UTC).isoformat(),
}
with conn:
    cur=conn.execute('INSERT INTO audit(at,event,payload) VALUES (?,?,?)',(time.time(),'CRYPTO_P90_RESEARCH_CANDIDATE_CLASSIFICATION',json.dumps(payload,separators=(',',':'),allow_nan=False)))
    classification_id=cur.lastrowid
    for r in normalized:
        conn.execute('INSERT OR REPLACE INTO state(key,value) VALUES (?,?)',(f"crypto_pair_status:{r['symbol']}:{r['frame']}",json.dumps({'status':'RESEARCH_CANDIDATE','reasons':REASONS,'p90_spread_to_target_ratio':r.get('p90_spread_to_target_ratio'),'measurement_result_audit_id':result_audit_id,'classification_audit_id':classification_id,'source_start_audit_id':START_AUDIT,'activated':False},separators=(',',':'))))
payload['classification_audit_id']=classification_id
(OUT/'crypto_p90_four_hour_result.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
lines=[]
for r in normalized:
    value=pct(r)
    lines.append(f"{r['symbol']} {r['frame']} | p90 {value:.2f}%" if value is not None else f"{r['symbol']} {r['frame']} | p90 غير متاح")
lines.append(f"EURUSD/7808213 دون تغيير | الإذن {payload['authorization_id']} حتى {payload['authorization_expiry_utc']} UTC")
(OUT/'crypto_p90_four_hour_report.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'complete':complete,'elapsed_seconds':elapsed,'result_audit_id':result_audit_id,'classification_audit_id':classification_id,'rows':[{k:r.get(k) for k in ('symbol','frame','median_spread','p90_spread','median_atr','target_1_5x_median_atr','p90_spread_to_target_ratio','final_status')} for r in normalized]},ensure_ascii=False))
conn.close()
