"""Evidence-bound readiness ledger. No broker connection or trading authority.

This deliberately issues no numerical score or profitability certification.
Missing/stale evidence remains a gap even when another gate passes.
"""
import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


def assess(root):
    root=Path(root);reports=root/'reports';checks=[]
    def gate(id,status,ar,en,**details):
        checks.append(dict(id=id,status=status,description_ar=ar,description_en=en,**details))
    def read(name):
        path=reports/name
        if not path.is_file():return None
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            return data if isinstance(data,dict) else None
        except (OSError,ValueError,TypeError):return None
    def sources_current(report):
        hashes=report.get('source_hashes')
        if not isinstance(hashes,dict) or not hashes:return False
        # Report paths are untrusted: hash only immediate source module names.
        for name,expected in hashes.items():
            if not isinstance(name,str) or '/' in name or '\\' in name or not name.endswith('.py'):return False
            file=root/'src/nexus'/name
            if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:return False
        return True
    def count(value):
        return value if isinstance(value,int) and not isinstance(value,bool) and value>=0 else 0
    invariant=read('rule-invariants.json')
    fresh=bool(invariant and sources_current(invariant))
    invariant_ok=bool(fresh and invariant.get('passed') is True and not invariant.get('failed_checks') and
                      type(invariant.get('orders_sent')) is int and invariant.get('orders_sent')==0 and count(invariant.get('evaluations'))>0 and
                      count(invariant.get('future_data_checks'))>=count(invariant.get('evaluations')))
    gate('synthetic_invariants','PASS' if invariant_ok else 'GAP',
         'سلامة المخرجات ورفض الشموع المستقبلية على العينات الاصطناعية',
         'Synthetic output invariants and future-bar abstention',source_current=fresh,
         evaluations=count(invariant.get('evaluations')) if invariant else 0)
    models=invariant.get('per_model',[]) if fresh else []
    models=models if isinstance(models,list) else []
    unexercised=[x.get('id') for x in models if isinstance(x,dict) and
                (not isinstance(x.get('statuses'),dict) or count(x['statuses'].get('READY'))==0)]
    gate('entry_branch_evidence','GAP',
         'يلزم دليل مستقل لحالات الدخول الصاعدة والهابطة والإبطال لكل نموذج؛ الانتظار ليس اختبار دخول',
         'Independent buy, sell and invalidation fixtures are required per model; waiting is not entry coverage',
         generated_sample_models_without_ready=unexercised,
         scope='generated audit samples only; existing unit fixtures require a separate per-model mapping')
    broker=read('mt5-rule-review.json');broker_fresh=bool(broker and sources_current(broker))
    broker_ok=bool(broker_fresh and broker.get('account_mode')=='DEMO' and type(broker.get('orders_sent')) is int and broker.get('orders_sent')==0 and
                   count(broker.get('evaluations'))>0 and broker.get('data_errors')==[])
    gate('broker_history_read','PASS' if broker_ok else 'GAP',
         'قراءة تاريخ شموع الوسيط دون إرسال أوامر؛ لا تثبت جودة الدخول',
         'Read-only broker history evaluation; not entry-quality proof',source_current=broker_fresh,
         evaluations=count(broker.get('evaluations')) if broker else 0)
    gate('profitability_after_costs','NOT_ESTABLISHED',
         'لم تعتمد هذه المراجعة تفوقاً زمنياً مستقلاً بعد جميع تكاليف التنفيذ',
         'This assessment establishes no independent chronological cost-adjusted trading edge')
    gate('live_policy_promotion','REQUIRES_REVIEW',
         'نجاح الاختبارات لا يغير قواعد القرار أو حدود المال أو يمنح صلاحية التنفيذ',
         'Passing tests cannot change live rules, financial limits or execution authority')
    files={name:hashlib.sha256((reports/name).read_bytes()).hexdigest()
           for name in ('rule-invariants.json','mt5-rule-review.json') if (reports/name).is_file()}
    return {'schema': 1,'report_type': 'EVIDENCE_BOUND_READINESS','created_at_utc': datetime.now(UTC).isoformat(),
                'checks': checks,'evidence_file_sha256': files,'score': None,'all_schools_complete': False,
                'institutional_readiness_certified': False,'profitability_proven': False,'orders_sent': 0,
                'technical_invariants_passed': invariant_ok,'broker_read_audit_passed': broker_ok}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    result=assess(args.root)
    output=args.root/'reports/readiness-assessment.json';output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('technical_invariants_passed','broker_read_audit_passed','institutional_readiness_certified','orders_sent')}))
