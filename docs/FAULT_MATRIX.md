# Fault matrix: 25 named scenarios

Synthetic brokers and isolated SQLite only. No real broker fault exercise.

| # | Fault | Status | Actual test |
|---|---|---|---|
| 1 | MT5 disconnect during send | مغطى | `tests/test_release_fault_injection.py::ReleaseFaultInjection::test_mt5_disconnect_during_send_retains_unknown_and_blocks_retry` |
| 2 | Reconciliation timeout | مغطى | `tests/test_release_fault_injection.py::ReleaseFaultInjection::test_reconciliation_timeout_preserves_reservation_and_revokes_authority` |
| 3 | Concurrent audit conflict | مغطى | `tests/test_release_fault_injection.py::ReleaseFaultInjection::test_concurrent_audit_conflict_rolls_back_both_claims_then_one_retry_wins` |
| 4 | proposals.db write failure | مغطى | `tests/test_release_fault_injection.py::ReleaseFaultInjection::test_proposals_db_write_failure_commits_neither_proposal_nor_audit` |
| 5 | Sandbox partial evaluation failure | مغطى | `tests/test_release_fault_injection.py::ReleaseFaultInjection::test_sandbox_mid_evaluation_failure_rejects_without_partial_metrics` |
| 6 | Reservation audit failure | مغطى | `tests/test_atomic_intent_audit.py::AtomicIntentAudit::test_reservation_rolls_back_when_audit_insert_fails` |
| 7 | Send-claim audit failure | مغطى | `tests/test_atomic_intent_audit.py::AtomicIntentAudit::test_send_claim_rolls_back_and_retry_is_audited_once` |
| 8 | State-transition audit failure | مغطى | `tests/test_atomic_intent_audit.py::AtomicIntentAudit::test_state_and_reserved_money_roll_back_with_failed_audit` |
| 9 | Management audit failure | مغطى | `tests/test_atomic_intent_audit.py::AtomicIntentAudit::test_management_intent_and_audit_are_atomic_and_idempotent` |
| 10 | Authorization/settings audit failure | مغطى | `tests/test_authorization_audit_failure.py::AuthorizationAuditFailure::test_authorization_and_daily_settings_audit_failure_never_grant_send_authority` |
| 11 | Kill switch despite audit failure | مغطى | `tests/test_authorization_audit_failure.py::AuthorizationAuditFailure::test_kill_switch_remains_effective_even_if_audit_write_fails` |
| 12 | Buy/sell/reservation/settings audit correlation | مغطى | `tests/test_authorization_audit_failure.py::AuthorizationAuditFailure::test_reservation_buy_sell_settings_and_rejection_have_correlated_audit` |
| 13 | Real/unknown account authorization | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_activation_rejects_real_contest_unknown_and_boolean` |
| 14 | Terminal permission loss | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_terminal_permission_failure_blocks_all_sends` |
| 15 | Stale quote/unknown calendar | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_unknown_calendar_and_stale_quote_refuse` |
| 16 | Insufficient budget/minimum lot/margin | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_minimum_lot_over_budget_and_margin_exhaustion_rejected` |
| 17 | Day rollover/open reservations | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_day_rollover_requires_activation_and_old_reservations_carry` |
| 18 | Duplicate signal after restart | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_same_signal_never_sends_twice_even_after_restart` |
| 19 | Missing reply/timeout after fill | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_none_and_timeout_after_fill_are_unknown_without_retry` |
| 20 | Crash/restart during send | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_restart_sending_is_unknown_and_prepared_is_provably_unsent` |
| 21 | Partial fill with missing terminal history | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_partial_release_waits_for_terminal_history` |
| 22 | Account switch after final check | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_account_changed_after_final_check_still_cannot_send` |
| 23 | Concurrent budget/factor allocation | مغطى | `tests/test_risk_execution.py::AtomicLedgerTests::test_independent_connections_cannot_double_spend_shared_budget_or_factor` |
| 24 | Daily loss breach/owned-only flatten | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_daily_loss_policy_flattens_only_owned_and_is_persistent` |
| 25 | Conflicting duplicate cashflow | مغطى | `tests/test_risk_execution.py::RiskExecutionTests::test_conflicting_duplicate_cashflow_ticket_cannot_be_silently_counted` |
