"""Create portable/source delivery archives and inventory, without user data."""
import hashlib
import importlib.metadata
import json
import re
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from build_knowledge import build as build_knowledge
from build_school_catalog import build as build_school_catalog
from export_agent_rules import export as export_agent_rules

from nexus import __version__


def validate_release():
    build_school_catalog()
    export_agent_rules(ROOT / "docs" / "agent-rules")
    build_knowledge()
    executable=ROOT/"Windows"/"Quant Trading AI"/"Quant Trading AI.exe"
    tests=(ROOT/"reports"/"unit-tests.txt").read_text(encoding="utf-8")
    count=re.search(r"Ran (\d+) tests",tests)
    if not count or not tests.rstrip().endswith("OK"):raise RuntimeError("Successful unit-test log required")
    static=(ROOT/"reports"/"ui-static-tests.txt").read_text(encoding="utf-8-sig")
    if "PASS: actual published 58-school catalog" not in static or "PASS: queued action completion" not in static or "PASS: confluence and scalp controls" not in static or 'PENDING:' in static:raise RuntimeError("Bilingual catalog, confluence/scalp controls and queued completion UI checks must pass")
    evidence={}
    invariants=json.loads((ROOT/'reports/rule-invariants.json').read_text(encoding='utf-8'))
    library=json.loads((ROOT/'docs/knowledge/library.json').read_text(encoding='utf-8'))
    if (invariants.get('passed') is not True or invariants.get('failed_checks')
            or invariants.get('source_hashes')!=library['source_hashes']
            or invariants.get('models')!=len(library['rules'])
            or len(invariants.get('timeframes',[]))!=21
            or invariants.get('future_data_checks')!=invariants.get('evaluations')):
        raise RuntimeError('Current all-model invariant evidence required')
    reviewed={(r['id'],r['version'],r['revision']) for r in invariants['per_model']}
    current={(r['id'],r['version'],r['revision']) for r in library['rules']}
    if reviewed!=current:raise RuntimeError('Rule review does not match current model versions')
    evidence['rule-invariants.json']=invariants
    broker_review=json.loads((ROOT/'reports/mt5-rule-review.json').read_text(encoding='utf-8'))
    if (broker_review.get('source_hashes')!=library['source_hashes']
            or broker_review.get('orders_sent')!=0 or broker_review.get('data_errors')
            or not broker_review.get('results')):
        raise RuntimeError('Current read-only MT5 model review required')
    for sample in broker_review['results']:
        checked={(m['strategy_id'],m['version'],m['rule_revision']) for m in sample['models']}
        if checked!=current:raise RuntimeError('Broker review model versions do not match release')
    evidence['mt5-rule-review.json']=broker_review
    for name in ("packaged-service-smoke.json","packaged-mt5-readonly.json"):
        item=json.loads((ROOT/"reports"/name).read_text(encoding="utf-8"))
        if item.get("passed") is not True:raise RuntimeError("Packaged verification failed: "+name)
        if item.get("orders_sent_to_mt5")!=0:raise RuntimeError("This release verification must remain read-only")
        evidence[name]=item
    for folder in ("ui","bridge","src"):
        for source in (ROOT/folder).rglob("*"):
            if source.is_file() and source.suffix!='.pyc':
                bundled=ROOT/"Windows"/"Quant Trading AI"/"_internal"/folder/source.relative_to(ROOT/folder)
                if not bundled.exists() or bundled.read_bytes()!=source.read_bytes():raise RuntimeError("Source/bundle asset mismatch: "+str(source))
    code=[ROOT/"launch.py",*sorted((ROOT/"src").rglob("*.py"))]
    if any(source.stat().st_mtime>executable.stat().st_mtime for source in code):raise RuntimeError("Source changed after Windows build")
    report={"created_at_utc":datetime.now(UTC).isoformat(),"unit_tests_passed":int(count.group(1)),"static_ui_passed":True,
        "exe_sha256":hashlib.sha256(executable.read_bytes()).hexdigest(),"packaged_checks":evidence,
        "source_sha256":{file.relative_to(ROOT).as_posix():hashlib.sha256(file.read_bytes()).hexdigest() for file in code},
        "final_acceptance_passed":False,"gui_visual_verified":False,"actual_trade_execution_verified":False}
    (ROOT/"reports"/"release-validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")


def collect_notices():
    folder=ROOT/"licenses";folder.mkdir(exist_ok=True)
    lines=["# Third-party notices", "", "Generated from installed distributions used for this Windows build. Component license files below retain their original wording.", "", "| Distribution | Version | Declared license |", "|---|---|---|"]
    package_names=[]
    for filename in ("requirements.txt","requirements-build.txt"):
        for line in (ROOT/filename).read_text(encoding="utf-8").splitlines():
            if "==" in line and not line.startswith("#"):package_names.append(line.split("==")[0])
    for name in sorted(set(package_names),key=str.lower):
        dist=importlib.metadata.distribution(name)
        license_text=dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See distribution files"
        license_text=" ".join(license_text.split())[:180].replace("|","/")
        lines.append(f"| {dist.metadata['Name']} | {dist.version} | {license_text} |")
        for file in dist.files or []:
            if any(part.lower().startswith(("license","copying","notice")) for part in file.parts):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    dest=folder/name/Path(*(part for part in file.parts if part not in ("..",".")));dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(source,dest)
    python_license=Path(sys.base_prefix)/"LICENSE.txt"
    if python_license.exists():shutil.copy2(python_license,folder/"PYTHON-LICENSE.txt")
    lines.extend(["", "Python runtime: "+sys.version.split()[0]+"; Python and bundled runtime component notices are in licenses/PYTHON-LICENSE.txt when provided by the runtime.", "", "MetaTrader5 connectivity requires the user's installed broker terminal. Microsoft WebView2 is a platform prerequisite; the user's installed runtime is not copied into this archive."])
    (ROOT/"THIRD-PARTY-NOTICES.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


def main():
    validate_release()
    collect_notices()
    portable=ROOT/"Windows"/"Quant Trading AI"
    if not (portable/"Quant Trading AI.exe").exists():raise RuntimeError("Build Windows package first")
    for file in ("README.md","THIRD-PARTY-NOTICES.md"):shutil.copy2(ROOT/file,portable/file)
    for folder in ("docs","reports","licenses"):
        for file in (ROOT/folder).rglob("*"):
            if file.is_file() and file.suffix not in (".sqlite3",".pyc"):
                target=portable/folder/file.relative_to(ROOT/folder);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
                if folder=="docs":
                    internal=portable/"_internal"/"docs"/file.relative_to(ROOT/folder)
                    internal.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(file,internal)
    destination=ROOT.parent
    delivery_folder=f"Quant Trading AI v{__version__}"
    binaries=destination/f"Quant-Trading-AI-v{__version__}-Windows-x64.zip";sources=destination/f"Quant-Trading-AI-v{__version__}-Source.zip"
    with zipfile.ZipFile(binaries,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for file in sorted(portable.rglob("*")):
            if file.is_file():zipped.write(file,(Path(delivery_folder)/file.relative_to(portable)).as_posix())
    with zipfile.ZipFile(sources,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for file in sorted(ROOT.rglob("*")):
            rel=file.relative_to(ROOT)
            if file.is_file() and not any(part in ("Windows","__pycache__",".venv","build-work") for part in rel.parts) and file.suffix not in (".pyc",".sqlite3"):
                zipped.write(file,(Path(delivery_folder)/rel).as_posix())
    manifest={"product":"Quant Trading AI","version":__version__,"created_at_utc":datetime.now(UTC).isoformat(),"final_acceptance_passed":False,"archives":[]}
    for file in (binaries,sources):
        with zipfile.ZipFile(file) as zipped:
            bad=zipped.testzip()
            if bad:raise RuntimeError("Archive CRC failure: "+bad)
        manifest["archives"].append({"file":file.name,"bytes":file.stat().st_size,"sha256":hashlib.sha256(file.read_bytes()).hexdigest()})
    (destination/f"Quant-Trading-AI-v{__version__}-release-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=="__main__":main()
