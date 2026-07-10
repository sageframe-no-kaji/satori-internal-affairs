# P2-H14: Frontend Test Framework

**Status:** IN PROGRESS (autonomous; audit deferral "frontend test framework", no open decisions — Vitest is the stack's default)
**Phase:** 2 (infrastructure)
**Ho:** 14
**Depends on:** P2-H10 (lockfiles committed), P2-H12 (the focus behaviors this suite pins were manual-only)

---

## Objective

The frontend gets a test harness and a meaningful starter suite. Until now every frontend behavior — including P2-H12's keyboard contract — was verified by `svelte-check` plus a manual script; behaviors had no pins. After this ho, `npx vitest run` is part of the verification stack and the commit gate.

## Decisions (defaults, recorded)

- **Vitest** — the Vite-native runner; zero-friction with the existing config. **jsdom** environment; **@testing-library/svelte** (v5, Svelte-5-aware) for component tests; **jest-dom** matchers.
- **Colocated tests** (`Component.test.ts` beside the component) — matches the src-adjacent convention Python tests don't have to follow here; the include pattern is `src/**/*.test.ts`.
- **No coverage floor yet.** The Python 90% floor is enforced by hooks; the frontend starts with a behavior-pinning suite and earns its floor once the suite has breadth. Recorded as a known gap — revisit at v0.7.
- **Store singleton:** `gameStore` is a module singleton by design; tests drive it through its public surface with `$lib/api` mocked and `reset()` between tests, rather than re-instantiating.

## Deliverables

1. `vite.config.ts` — vitest config (jsdom, setup file, svelteTesting plugin); `vitest-setup.ts` with jest-dom matchers
2. `package.json` — `test` / `test:watch` scripts; dev deps (vitest, jsdom, @testing-library/svelte, @testing-library/jest-dom)
3. Starter suite:
   - `CategoryDropdown.test.ts` — the UD-4/5 keyboard contract (open focuses first option, arrow cycling with wrap, Esc/selection return focus, disabled behavior)
   - `ActionBar.test.ts` — group rendering, locked-inline treatment, wait disabled in emergencies, one-press emergency button + focus
   - `ActiveConcernsPanel.test.ts` — sections/counts/chips, windowshade toggle, fresh-evidence highlight + auto-shade
   - `VitalsStrip.test.ts` — status thresholds → classes, SpO₂ label
   - `EmergencyBanner.test.ts` — label, countdown, alert role
   - `gameStore.test.ts` — state updates from mocked API, calm-snapshot/lockedActions logic, emergency log tagging, findings getter, reset
4. `.pre-commit-config.yaml` — vitest hook joins the gate; `Makefile` — frontend tests in `make test`

## Out of Scope

- Coverage floor (recorded above)
- E2E/browser tests (Playwright is a later conversation)
- Testing `+page.svelte` composition (needs SvelteKit runtime mocks; component + store coverage is the value)

## Verification

`npx vitest run` green; `npm run check` green; full Python stack untouched; commit exercises the new hook.

## Commit Message Template

```
test(P2-H14): frontend test framework — vitest + testing-library, starter suite
```
