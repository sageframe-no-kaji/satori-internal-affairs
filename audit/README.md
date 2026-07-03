# Audit — FABLE REVIEW remediation

This folder tracks the remediation work arising from the full-codebase review of 2026-07-03 ([FABLE-REVIEW-2026-07-03.md](FABLE-REVIEW-2026-07-03.md)), conducted at HEAD `e42884d`.

The review found the architecture sound and all four boundaries holding, with debt concentrated in three places: a case-authoring blocker silently reshaping every playthrough (C-1), a verification stack that declares strictness it isn't executing (C-3), and a determinism guarantee that holds within a process but not across processes (C-2).

## How this folder relates to the Kamae chain

These are audit-remediation agent tasks, not hos. Per the forward-only principle, none of them reopen closed hos — they respond to what the review surfaced, in the current build slot. Where a task touches a design decision the Kamae chain hasn't made (survivable crisis, diegetic timers, OPTIMAL window), the task stops and surfaces rather than deciding. The spike's output is a decision memo for a thinking conversation; decisions flow back into the chain from there.

## Task ledger

| # | Task | Est. | Status | Commits |
|---|------|------|--------|---------|
| S1 | [Verification-stack repair](agent-task-2026-07-03-s1-verification-stack-repair.md) | ~2.5h | complete | `21d21ae`, `6142001`, `35ef368` |
| S2 | [Case repair + regression harness](agent-task-2026-07-03-s2-case-repair-regression-harness.md) | ~2h | complete | `e9af5e5` |
| S3 | [Determinism hardening + event contract](agent-task-2026-07-03-s3-determinism-hardening.md) | ~1.5h | complete | `b19114e` |
| SP | [Emergency-mode design spike](agent-task-2026-07-03-sp-emergency-mode-design-spike.md) | ~1h | complete | `2341965` → [decision memo](emergency-mode-decision-memo.md) |
| S4 | [Frontend ataxia fixes + narrator guard](agent-task-2026-07-03-s4-frontend-ataxia-narrator-guard.md) | ~1h | complete | `844a42d`, `1973887` |

Execution order: S1 → S2 → S3 → SP → S4. S1 first because every later task's green light is meaningless until the gate actually gates. S2 before any further playtesting. SP feeds P2-H05; S4's narrator guard precedes P2-H08.

Update the ledger (status + commit hashes) as tasks complete.

## Deferred beyond this audit

Named in §7 of the report: llm-client provider test coverage (folds into P2-H08), session-store TTL/lock (hosting phase), UD-3–UD-6 focus work (batch into P2-H03), environment reproducibility / uv migration (own infrastructure ho), frontend test framework, pyright config reconciliation, dead-endpoint cleanup.
