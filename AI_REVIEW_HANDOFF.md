# ملاحظة للمراجع الآلي | AI reviewer handoff

Snapshot version: 0.7.16. Review the current code, not historical release claims. First read `docs/53-integrated-candidate-development.md`, `docs/39-comprehensive-model-development-spec.md`, and `docs/50-quality-acceptance-program.md`. Then inspect `src/nexus/committee.py`, `engine.py`, `risk.py`, `execution.py`, `store.py`, `specialists.py`, `config/`, and related tests.

Requested design to assess: H4 (or higher) provides directional context; M15 confirms structure; a completed M1 candle generates the entry trigger. Do not change live policy without chronological, after-spread/commission/slippage tests. Preserve fail-closed risk controls, broker identity checks, audit history, and shadow-only learning. Findings must include file/line, reproducer, impact, and minimal safe patch.

Do not infer trading profitability. The desktop release is READ_ONLY and broker execution status must be checked independently. n8n is not integrated; suitable future use is report/alert/research orchestration only, without broker credentials.
