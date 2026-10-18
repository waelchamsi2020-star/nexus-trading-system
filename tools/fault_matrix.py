"""Run 25 named fault scenarios and derive coverage only from fresh JUnit results."""
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('MT5 disconnect during send','test_release_fault_injection','ReleaseFaultInjection','test_mt5_disconnect_during_send_retains_unknown_and_blocks_retry'),
 ('Reconciliation timeout','test_release_fault_injection','ReleaseFaultInjection','test_reconciliation_timeout_preserves_reservation_and_revokes_authority'),
 ('Concurrent audit conflict','test_release_fault_injection','ReleaseFaultInjection','test_concurrent_audit_conflict_rolls_back_both_claims_then_one_retry_wins'),
 ('proposals.db write failure','test_release_fault_injection','ReleaseFaultInjection','test_proposals_db_write_failure_commits_neither_proposal_nor_audit'),
 ('Sandbox partial evaluation failure','test_release_fault_injection','ReleaseFaultInjection','test_sandbox_mid_evaluation_failure_rejects_without_partial_metrics'),
 ('Reservation audit failure','test_atomic_intent_audit','AtomicIntentAudit','test_reservation_rolls_back_when_audit_insert_fails'),
 ('Send-claim audit failure','test_atomic_intent_audit','AtomicIntentAudit','test_send_claim_rolls_back_and_retry_is_audited_once'),
 ('State-transition audit failure','test_atomic_intent_audit','AtomicIntentAudit','test_state_and_reserved_money_roll_back_with_failed_audit'),
 ('Management audit failure','test_atomic_intent_audit','AtomicIntentAudit','test_management_intent_and_audit_are_atomic_and_idempotent'),
 ('Authorization/settings audit failure','test_authorization_audit_failure','AuthorizationAuditFailure','test_authorization_and_daily_settings_audit_failure_never_grant_send_authority'),
 ('Kill switch despite audit failure','test_authorization_audit_failure','AuthorizationAuditFailure','test_kill_switch_remains_effective_even_if_audit_write_fails'),
 ('Buy/sell/reservation/settings audit correlation','test_authorization_audit_failure','AuthorizationAuditFailure','test_reservation_buy_sell_settings_and_rejection_have_correlated_audit'),
 ('Real/unknown account authorization','test_risk_execution','RiskExecutionTests','test_activation_rejects_real_contest_unknown_and_boolean'),
 ('Terminal permission loss','test_risk_execution','RiskExecutionTests','test_terminal_permission_failure_blocks_all_sends'),
 ('Stale quote/unknown calendar','test_risk_execution','RiskExecutionTests','test_unknown_calendar_and_stale_quote_refuse'),
 ('Insufficient budget/minimum lot/margin','test_risk_execution','RiskExecutionTests','test_minimum_lot_over_budget_and_margin_exhaustion_rejected'),
 ('Day rollover/open reservations','test_risk_execution','RiskExecutionTests','test_day_rollover_requires_activation_and_old_reservations_carry'),
 ('Duplicate signal after restart','test_risk_execution','RiskExecutionTests','test_same_signal_never_sends_twice_even_after_restart'),
 ('Missing reply/timeout after fill','test_risk_execution','RiskExecutionTests','test_none_and_timeout_after_fill_are_unknown_without_retry'),
 ('Crash/restart during send','test_risk_execution','RiskExecutionTests','test_restart_sending_is_unknown_and_prepared_is_provably_unsent'),
 ('Partial fill with missing terminal history','test_risk_execution','RiskExecutionTests','test_partial_release_waits_for_terminal_history'),
 ('Account switch after final check','test_risk_execution','RiskExecutionTests','test_account_changed_after_final_check_still_cannot_send'),
 ('Concurrent budget/factor allocation','test_risk_execution','AtomicLedgerTests','test_independent_connections_cannot_double_spend_shared_budget_or_factor'),
 ('Daily loss breach/owned-only flatten','test_risk_execution','RiskExecutionTests','test_daily_loss_policy_flattens_only_owned_and_is_persistent'),
 ('Conflicting duplicate cashflow','test_risk_execution','RiskExecutionTests','test_conflicting_duplicate_cashflow_ticket_cannot_be_silently_counted'),
]


def main():
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    nodes=[f'tests/{module}.py::{cls}::{name}' for _,module,cls,name in CASES]
    command=[sys.executable,'-m','pytest','-q','-v','-o','addopts=',*nodes,'--junitxml=reports/fault-matrix.xml']
    result=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONUTF8':'1'},
                          capture_output=True,text=True,encoding='utf-8',errors='replace',check=False)
    (folder/'fault-matrix.log').write_text(result.stdout+result.stderr,encoding='utf-8')
    print(result.stdout+result.stderr,flush=True)
    tests=ET.parse(folder/'fault-matrix.xml').findall('.//testcase')
    rows=[]
    for (label,_,_,name),node in zip(CASES,nodes,strict=True):
        found=[t for t in tests if t.attrib['name']==name]
        passed=len(found)==1 and not any(found[0].find(x) is not None for x in ('failure','error','skipped'))
        rows.append({'case':label,'test':node,'status':'PASS' if passed else 'MISSING_OR_FAILED'})
    report={'utc':datetime.now(UTC).isoformat(),'scope':'25 named synthetic fault scenarios; not all possible failures',
            'command':command,'exit_code':result.returncode,'covered':sum(x['status']=='PASS' for x in rows),
            'total':len(CASES),'cases':rows,'broker_orders':'SYNTHETIC_ONLY'}
    (folder/'fault-matrix.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    lines=['# Fault matrix: 25 named scenarios', '', 'Synthetic brokers and isolated SQLite only. No real broker fault exercise.',
           '', '| # | Fault | Status | Actual test |','|---|---|---|---|']
    lines.extend(f"| {i} | {r['case']} | {'مغطى' if r['status']=='PASS' else 'ناقص'} | `{r['test']}` |" for i,r in enumerate(rows,1))
    (ROOT/'docs/FAULT_MATRIX.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'covered':report['covered'],'total':report['total'],'exit_code':result.returncode}))
    return 0 if result.returncode==0 and report['covered']==25 else 1


if __name__=='__main__':
    raise SystemExit(main())
