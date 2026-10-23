# 0.7.16 — 2026-10-23

- Move the executor state to the top bar, expose its reason accessibly, and remove the duplicate status from the lower trading panel.
- Label the home decision card as the best-opportunity preview and direct users to the full opportunities list.
- Add static and browser regressions for the single top status, error detail, and preview count. No school rules, account limits, or order permissions changed.
- Keep the independent Demo limit form editable while the sender is stopped; corrupt execution status still blocks starting the sender. When status is unreadable and the sender may still be running, fail closed on limit edits until execution state is confirmed.

# 0.7.15 — 2026-10-23

- Fixed Demo-integrated layout in the actual desktop: keep the scan and decision row intact and stretch the status/control panel to the full content width after the account strip.
- Extended the integrated-state viewport matrix to verify the execution panel is contained, full width, and ordered after account cards.
- Presentation-only repairs; no account, limit, authorization, strategy, or broker-order behavior changed.

# 0.7.14 — 2026-10-23

- Fixed the real Demo-integrated dashboard state: scan and decision cards stay in a full-width responsive grid row while the separate legacy controls grid is hidden.
- Added regression checks for the integrated state at mobile, tablet, laptop, desktop, and wide desktop sizes in Arabic/English and all themes.
- Presentation-only repair. No account, order, risk, strategy, or execution permission changed.

# 0.7.13 — 2026-10-23

- Fixed the overview scan/decision cards collapsing into narrow implicit grid columns at tablet widths. The overview now uses a normal-flow page layout and explicitly stacks both cards below 900 CSS pixels.
- Added browser geometry checks at 375, 768, 1024, 1440, and 1920 CSS pixels in Arabic and English, across all six themes.
- No API credentials, trading settings, model rules, risk limits, or execution permissions changed.

# 0.7.12 — 2026-10-23

- Add the Neural AI command-center theme with a restrained network background, clearer account/scan/trading cards, and right-side mobile navigation through 900px.
- Keep the existing six theme choices and preserve server-provided values; migrate the default theme preference once for existing installations.
- Serve the new stylesheet through the local same-origin static allowlist with an explicit CSS MIME type; cover it with a server regression test.
- Capture browser screenshots on the Neural theme. No trading/model/risk behavior or account permissions changed.

# 0.7.11 — 2026-10-23

- Keep the complete intent ledger in SQLite, but publish a compact account-scoped projection to routine UI/API state: all unresolved intents and the latest 150 terminal intents, with total/omitted counts.
- Stop publishing account intents or audit rows before broker account identity is verified; preserve only the last verified, scoped projection during a terminal outage.
- Add an account ownership column to the audit table with a compatible migration that recovers explicit ownership from existing payloads without changing audit payload contents.
- Targeted regressions cover compact payloads, retained active intents, account audit isolation, database migration compatibility, and reconciliation payload stability.
- No strategy, cost, risk limit, authorization, or trading policy changed. The installed desktop remains 0.7.10 until the 0.7.11 packaged smoke passes.

# 0.7.10 — 2026-10-23

- Put market scan and the trading decision first on the dashboard, followed by compact account cards and controls.
- Reduce the primary navigation to the daily workflow; keep news, school references and audit in an accessible secondary menu.
- Add current-page semantics and keyboard/browser regression checks for the reordered dashboard and secondary navigation.
- No strategy, risk rule, trading permission, or external API authority changed.

# 0.7.8 — 2026-10-22

- When the dedicated Demo sender is stopped or its published state is stale, keep the connected, identity-matched Demo account and broker positions visible in READ_ONLY mode.
- Keep risk/performance from the stopped sender unavailable instead of showing stale figures; block every execution action and label the old sender state as stale.
- Added regression coverage for stale sender status, Demo identity matching and read-only fallback.

# 0.7.7 — 2026-10-22

- Bound dashboard state publication to 100 recent model cards while retaining full per-model activity counts and complete diagnostics from the in-memory evidence.
- Projected quantitative research results to the fields used by the UI, excluding large per-trade backtest traces from routine polling.
- Added regressions for bounded payloads and retained diagnostic completeness. Full pytest, integration, and isolated browser checks pass.
- Desktop deployment remains pending; no trading executor was started and no broker orders were sent.

# 0.7.0 — 2026-10-18

- Fix rapid Escape/reopen confirmation race and trap Tab inside confirmation.
- Add per-school/context training three-sigma drift display; focusable scroll region.
- Persist authorization/settings audit before granting in-memory authority.
- Add explicit market-entry/resampling diagnostics without lowering costs.
- Add declared-native >=5000-candle CSV edge research gate, no trading authority.
- Package existing learner with account-isolated proposal queue, shadow sandbox,
  drift monitor and one-cycle daily CLI. No automatic live mutation.
- Preserve versioned58-model configuration, histories, account separation and
  existing financial limits. No additional models.

Open: original contiguous M5/H1 datasets, sufficient real heldout samples,
provider-calibrated slippage, hosted CI evidence and complete human accessibility
assessment. No10/10 certification or economic profit claim.
# 0.7.5 candidate — multi-provider research bridge

- Added on-demand research connectors for Massive Forex aggregates, Frankfurter daily EUR/USD reference rates, BLS CPI and World Bank US GDP growth.
- Added a dedicated research-source panel in the news/economy screen with provenance, last-received time and per-provider status.
- Massive requires `NEXUS_MASSIVE_API_KEY`; no key was found in the current environment. Provider failures stay isolated and do not enter the execution path.
- Candidate source only. No tests, packaging, desktop deployment, or live Demo execution performed for this change.

# 0.7.6 candidate

- Add opt-in multi-provider LLM shadow commentary for Gemini, Groq, and OpenRouter.
- Add strict input/output schemas, endpoint allowlisting, no-redirect HTTPS, request bounds, and explicit no-execution authority.
- Add an Arabic UI panel and provider setup/privacy documentation. No provider credentials or live calls included.
# 0.7.9 — packaged API TLS repair

- Include certifi's root CA bundle in the Windows build so HTTPS research connectors can validate public API certificates.
- Make release validation fail if the packaged CA bundle is absent or incomplete.
- Keep external research advisory-only; broker MT5 remains the only execution quote/order authority. No Demo executor was enabled.

