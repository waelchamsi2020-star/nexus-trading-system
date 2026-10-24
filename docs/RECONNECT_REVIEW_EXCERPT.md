# MT5 reconnect source excerpts for external review

This file quotes the actual source at commit `74e2edc` so web viewers do not truncate long `engine.py`. It contains no runtime ledger, token, or account number. The quotes are evidence, not an instruction to auto-resume authorization.

### `src/nexus/engine.py:967-1000`

```python
967:     def _recover_mt5_connection(self, cause):
968:         """Recover a stale Python IPC binding without restoring authorization."""
969:         if not self.broker or self.broker.is_simulation or not hasattr(self.broker,"reconnect"):
970:             return False
971:         now=self.clock()
972:         if now-self.last_reconnect_attempt<5:
973:             return False
974:         self.last_reconnect_attempt=now
975:         reason="انقطع اتصال MT5 وأعيد ربطه؛ يلزم تفعيل Demo من جديد"
976:         if self.executor:self.executor.deactivate(reason)
977:         self.status="DISCONNECTED";self.error=str(cause)
978:         try:
979:             terminal=self.broker.reconnect()
980:             account=self.broker.account();key=account_key(account)
981:             self._sync_learning_scope(key)
982:             self.context_cache={};self.partner_catalog=None
983:             # Build fresh guards around the recovered broker.  In particular,
984:             # no authorization object or reserved in-memory budget survives.
985:             self.risk=RiskManager(self.broker,self.store)
986:             self.executor=Executor(self.broker,self.store,self.risk,self.clock,
987:                                    regime_routing_enabled=self.config.get("regime_routing_enabled",False))
988:             self.scanner=UniverseScanner(self.broker,self.clock)
989:             reconciliation=self.executor.reconcile(key)
990:             if not reconciliation.get("ok"):
991:                 raise BrokerError("تعذرت مطابقة سجل الوسيط بعد إعادة الاتصال: "+str(reconciliation.get("reason") or reconciliation.get("unresolved")))
992:             self._invalidate_research()
993:             self.settings={};self.quant_results={};self.cards_by_symbol={};self.decisions={};self.opportunities=[];self.manual={};self.deep_queue=[];self.attempted={}
994:             self.chart={"symbol":"","timeframe":"H1","bars":[],"cards":[],"school_analyses":[]}
995:             self.scanner.begin();self.last_scan=now
996:             self.status="READ_ONLY";self.error=""
997:             self._audit("CONNECTION_RESTORED_READ_ONLY",{"mode":"READ_ONLY","account_key":key,"terminal_connected":bool(terminal.get("connected"))})
998:             return True
999:         except Exception as exc:
1000:             logging.getLogger(__name__).exception("Handled boundary failure")
```

### `src/nexus/engine.py:1831-1853`

```python
1831:                     now=self.clock()
1832:                     try:
1833:                         terminal=self.broker.terminal()
1834:                     except Exception as exc:
1835:                         if not self._recover_mt5_connection(exc):
1836:                             raise
1837:                         terminal=self.broker.terminal()
1838:                     if not terminal.get("connected"):
1839:                         self.executor.deactivate("انقطاع الاتصال؛ يلزم مطابقة الحساب وإعادة التفعيل")
1840:                         self.status="DISCONNECTED";self.error="انقطاع MT5. الدخول الجديد متوقف."
1841:                     else:
1842:                         if self.learner:self._sync_learning_scope(account_key(self.broker.account()))
1843:                         # Reconciliation is read-only and also runs after an
1844:                         # ambiguous response/restart; it never reactivates auth.
1845:                         self.executor.reconcile()
1846:                         if self.status=="DISCONNECTED":
1847:                             # A recovered terminal stays fail-closed, but the UI
1848:                             # must no longer claim the terminal is disconnected.
1849:                             self.status=self.executor.status().get("mode","READ_ONLY")
1850:                             self.error=""
1851:                             self._audit("CONNECTION_RESTORED_READ_ONLY",{"mode":self.status})
1852:                         if self.executor.status().get("mode") in ("AUTO_DEMO","MANUAL_DEMO"):
1853:                             self.executor.manage()
```

### `src/nexus/execution.py:138-171`

```python
138:     def _connection(self):
139:         account, terminal = self.broker.account(), self.broker.terminal()
140:         key = account_key(account)
141:         if type(account.get("trade_mode")) is not int or account.get("trade_mode") != 0:
142:             raise ValueError("Permanent Demo-only guard: Real, Contest and unknown accounts are refused")
143:         if account.get("margin_mode") not in (0, 2):
144:             raise ValueError("Unknown hedging/netting accounting mode")
145:         if not terminal.get("connected") or not terminal.get("trade_allowed") or terminal.get("tradeapi_disabled") is not False:
146:             raise ValueError("Terminal disconnected or trading/API disabled")
147:         if not account.get("trade_allowed") or account.get("trade_expert") is False:
148:             raise ValueError("Account trading/expert permission disabled")
149:         return account, key
150: 
151:     def _unresolved(self, key, exclude=None):
152:         return [i for i in self.store.intents(key) if i["id"] != exclude and blocks_send(i)]
153: 
154:     def _guard(self, entry=False, exclude=None):
155:         if self.mode not in ("MANUAL_DEMO", "AUTO_DEMO") or self.authorization is None:
156:             raise ValueError("READ_ONLY: explicit Demo activation is required")
157:         try:
158:             account, key = self._connection()
159:             if key != self.authorization["account_key"]:
160:                 raise ValueError("Account, server or terminal changed")
161:             if utc_day(self.clock()) != self.authorization["day"]:
162:                 raise ValueError("UTC day changed; explicit activation is required")
163:             if self._settings_digest() != self.authorization["settings_digest"]:
164:                 raise ValueError("Authorized risk settings changed")
165:         except Exception as exc:
166:             self.deactivate(str(exc))
167:             raise
168:         if self._unresolved(key, exclude):
169:             raise ValueError("Unresolved broker result blocks every send")
170:         if entry and (self.entries_paused or self.store.day_halt(key, self.clock())):
171:             raise ValueError("New entries are stopped")
```

### `src/nexus/execution.py:209-218`

```python
209:     def deactivate(self, reason="User deactivated trading"):
210:         with self.lock:
211:             unchanged = self.mode == "READ_ONLY" and self.authorization is None and self.entries_paused and self.last_reason == str(reason)
212:             self.mode, self.entries_paused, self.authorization = "READ_ONLY", True, None
213:             self._authorized_routing_fingerprint = None
214:             self.last_reason = str(reason)
215:             if not unchanged:
216:                 self.store.audit("AUTHORIZATION_REVOKED", {"reason": self.last_reason})
217:             return {"mode": self.mode, "entries_paused": True, "reason": self.last_reason}
218: 
```

## Existing regression evidence

- `tests/test_core_integration.py::test_stale_mt5_ipc_recovers_read_only_and_revokes_old_authorization` expects READ_ONLY after a reconnect.
- `tests/test_connection_idempotency.py` verifies unchanged healthy connections preserve an existing authorization but uncertain permissions revoke it.
- Eight selected connection/recovery tests passed locally on 24 October 2026.

## Review question

First establish from runtime audit whether a real disconnect occurred or whether one `terminal_info` read briefly returned `connected=false`. Instrument both engine paths without logging secrets. Then propose a narrowly scoped fix with executable tests covering the engine loop, exceptions, account changes, unknown permissions, unresolved sends, and day changes. Do not bypass Demo-only rules or auto-restore a revoked authorization.
