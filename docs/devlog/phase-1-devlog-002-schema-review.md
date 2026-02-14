# Phase 1 Devlog: Task 002 Schema Review

**Date:** 2026-02-14
**Task:** Agent Task 002 - Case Definition Schema
**Status:** Complete with bug fixes applied

---

## Overview

Agent Task 002 created the foundational schema infrastructure for Satori Internal Affairs: the formal contract between Anamnesis (LLM-powered case generation) and Satori (deterministic game engine). The deliverables included:

- **JSON Schema** (`schemas/case-definition.schema.json`): Draft 2020-12 schema, 660+ lines
- **Pydantic Models** (`packages/satori/src/satori/models/case_definition.py`): Python validation layer, 425 lines
- **Example Case** (`cases/example-neurocysticercosis.json`): Hand-written 12-node case (Maria Santos)
- **Test Suite** (`packages/satori/tests/test_case_schema.py`): 13 validation tests

All acceptance criteria met: tests pass, ruff passes, mypy passes.

---

## Schema Review: Verdict

**Overall:** Solid execution. The structural bones are right. The agent followed the spec faithfully on field names, types, nesting, and layer separation. The node-graph architecture with OR-of-ANDs activation logic, flag-based dependencies, and timer-based progression is correctly implemented.

**Issues Found:** Six observations ranging from "fix before committing" to "note for Satori implementation."

---

## Critical Issues (Fixed)

### Issue 1: Node 08 Flag Timing Bug

**Problem:** Node `node_08_wrong_treatment_steroids` had `starts_active: true` with `on_activate` immediately setting the `wrong_treatment_steroids` flag. This meant the flag was set at case start, which would prematurely satisfy Node 07's second activation path (`flag_set: wrong_treatment_steroids`).

**Why it matters:** The flag should only be set when the player actually prescribes steroids (on reveal), not when the case loads (on activate).

**Fix applied:**
```json
// Before: Flag set on activation (case start)
"activation": {
  "starts_active": true,
  "on_activate": [
    {"type": "set_flag", "target": "wrong_treatment_steroids"}
  ]
}

// After: Flag set on reveal (player action)
"activation": {
  "starts_active": true
},
"effects": {
  "on_reveal": [
    {"type": "set_flag", "target": "wrong_treatment_steroids"}
  ]
}
```

The node remains available from case start (starts_active: true), but the flag only sets when the player takes the action.

---

### Issue 2: Node 12 Missing Diagnostic Path

**Problem:** Node `node_12_husband_diego` was intended to provide an alternate diagnostic path. The architecture doc specified: "If NOT dietary_history_taken: provides an alternate path to undercooked_pork_exposure." The implementation only set `family_engaged` and `sunday_meals_known` — it didn't set `undercooked_pork_exposure`.

**Why it matters:** Diego is a redundant pathway design pattern. If the player talks to the husband before asking Maria about diet, Diego mentions the Sunday pork meals. Without setting the diagnostic flag, talking to Diego is relationally scored but doesn't help diagnostically.

**Fix applied:**
```json
"effects": {
  "on_reveal": [
    {"type": "set_flag", "target": "family_engaged"},
    {"type": "set_flag", "target": "sunday_meals_known"},
    {"type": "set_flag", "target": "undercooked_pork_exposure"}  // Added
  ]
}
```

This makes Diego a valid alternate path to the diagnosis. Whether it's conditional on `dietary_history_taken` being absent doesn't matter for Phase 1 (Satori treats flags as set/not-set; setting an already-set flag is a no-op).

---

### Issue 3: Pydantic Extra Fields Validation

**Problem:** The example case JSON includes a top-level `_comment` field for documentation. The JSON Schema doesn't explicitly define it, and Pydantic v2 forbids extra fields by default, so validation would fail.

**Why it matters:** The spec requested `_comment` for self-documentation. We need to either explicitly allow it or configure Pydantic to ignore unknown fields.

**Fix applied:**
```python
from pydantic import BaseModel, ConfigDict, Field

class CaseDefinition(BaseModel):
    """Complete medical mystery case definition."""

    model_config = ConfigDict(extra="ignore")  // Added

    id: UUID = Field(..., description="Unique identifier for this case")
    # ... rest of model
```

This allows the JSON to include metadata or comments that Pydantic will silently ignore during validation. The core contract fields are still validated strictly.

---

## Design Observations (Noted but Acceptable)

### Observation A: `neurocysticercosis_suspected` Flag Eliminated

**The spec said:** Node 05 (dietary history) should conditionally set `neurocysticercosis_suspected` if eosinophilia is also set. Node 09 (thigh X-ray) and Node 10 (correct treatment) should activate based on this intermediate flag.

**What was implemented:** The `neurocysticercosis_suspected` flag was never introduced. Instead:
- Node 09 activates on: `(undercooked_pork_exposure AND lesion_found) OR (eosinophilia AND lesion_found)`
- Node 10 activates on: `(diagnosis_confirmed) OR (undercooked_pork_exposure AND eosinophilia)`

**Why it's fine:** The intermediate flag concept was absorbed into direct condition paths. This is architecturally sound — fewer flags, same behavior. It eliminates a layer of indirection without losing functionality.

**Learning:** Intermediate "suspicion" flags are useful for narrative nodes (e.g., a doctor's internal thought bubble), but for pure activation logic, direct condition paths are cleaner.

---

### Observation B: ActionType Not a Formal Enum

**The spec said:** Define `ActionType` as a formal enum with 12 canonical values (`history_general`, `history_focused`, `physical_exam_general`, `order_labs`, etc.).

**What was implemented:**
- `RevealRule.action` is typed as `Optional[str]`
- `action_costs` is typed as `dict[str, TimeCost]`
- The example case uses an action + subcategory pattern: `"action": "order_imaging", "subcategory": "ct_head"`

**Why it's fine:** The flat enum doesn't capture how actions actually work in practice. The action costs already use mixed granularity (`order_imaging` vs. `order_imaging_xray` as separate keys). The action + subcategory pattern is more flexible and better suited to the domain.

**Learning:** The spec's ActionType enum was over-constrained. Real medical actions have natural hierarchies (order_labs:cbc, order_imaging:ct_head). The string + subcategory pattern accommodates this. We'll formalize the canonical base action types when building the Satori engine in Ho 02, but keeping them as validated strings rather than a rigid enum is the right call.

---

### Observation C: Node 10 Activation Paths Differ from Spec

**The spec said:** Node 10 (correct treatment) activates when `diagnosis_confirmed` OR `neurocysticercosis_suspected`.

**What was implemented:**
```json
"paths": [
  {"conditions": [{"type": "flag_set", "target": "diagnosis_confirmed"}]},
  {"conditions": [
    {"type": "flag_set", "target": "undercooked_pork_exposure"},
    {"type": "flag_set", "target": "eosinophilia"}
  ]}
]
```

**Why it's fine:** The second path requires `undercooked_pork_exposure AND eosinophilia` instead of `neurocysticercosis_suspected`. This is functionally equivalent (those were the two flags that would have set the intermediate flag anyway). It's mechanically correct OR-of-ANDs logic, and it allows the player to start treatment without going through Node 05 if they get both flags independently.

**Learning:** The OR-of-ANDs activation system is working as designed. Direct condition paths are clearer than intermediate flags when the flag is purely a conjunction of other flags.

---

## Implementation Process

### Initial Creation
The agent correctly:
1. Created comprehensive JSON Schema with `$defs` for all component types
2. Mirrored the schema in Pydantic models using `StrEnum` (Python 3.11+)
3. Hand-wrote a realistic 12-node example case demonstrating:
   - Timer-based nodes (Node 06: headache progression with 3 stages)
   - Auto-reveal nodes (Node 07: seizure crisis, Node 11: patient death)
   - Multiple diagnostic paths (Node 05 direct, Node 12 via family)
   - Wrong treatment path (Node 08: steroids causing rebound)
   - Patient death outcome (Node 11: activated if crisis timer expires)
4. Created 13 validation tests covering:
   - Schema validation
   - Referential integrity (flags, nodes)
   - Metadata completeness
   - Error handling

### Validation Issues Discovered
Initial test run revealed:
- Empty `conditions` arrays in `starts_active` nodes (min_length=1 constraint violated)
- Missing `action` field in auto-reveal nodes (was required, changed to Optional)

These were not bugs in the example case — they exposed over-constrained schema design:
1. **Empty conditions with starts_active:** A node that starts active doesn't need activation conditions. The schema should allow `paths` to be optional when `starts_active: true`.
2. **Auto-reveal nodes needing action:** Auto-reveal nodes don't have a player action. The `action` field should be optional when `auto_reveal: true`.

**Fixes applied to schema:**
- Made `ActivationRule.paths` optional (None allowed when starts_active)
- Made `RevealRule.action` optional (None allowed when auto_reveal)
- Updated test code to handle `None` checks for `node.activation.paths`

### Code Quality
After fixes:
- All 13 tests pass
- Ruff linting passes (after updating line-length to 120 and switching to StrEnum)
- Mypy type checking passes (strict mode)

---

## Architectural Learnings

### 1. The OR-of-ANDs Pattern Works
The activation system (`paths: list[ConditionPath]` where each path is AND-joined, paths are OR-joined) is expressive and understandable. The example case uses it correctly:
- Simple OR: `[path1, path2]` → "activate if path1 OR path2"
- Simple AND: `[{conditions: [a, b, c]}]` → "activate if a AND b AND c"
- Complex: `[{conditions: [a, b]}, {conditions: [c, d]}]` → "activate if (a AND b) OR (c AND d)"

### 2. Flags Are Better Than Intermediate States for Pure Logic
The elimination of `neurocysticercosis_suspected` shows that intermediate flags should be reserved for narrative or UI purposes. For pure activation logic, directly expressing the condition is clearer.

### 3. Timer Nodes Are Silent Progressors
Node 06 (headache_progression) demonstrates the silent timer pattern:
- No reveal rule (never shown to player)
- Stages at 60, 120, 150 minutes changing vitals
- `on_expire` activates the crisis node
- Pause condition: `correct_treatment_started`

This is elegant. The timer runs invisibly, manifesting only through vital sign changes and eventual crisis.

### 4. Auto-Reveal for Unavoidable Events
Nodes 07 (seizure crisis) and 11 (patient death) use `auto_reveal: true`. These aren't player discoveries — they're deterministic outcomes of game state. The auto-reveal pattern is correct for time-driven or consequence-driven events.

### 5. Multiple Paths to Same Information
Node 05 (Maria's dietary history) and Node 12 (Diego's family engagement) both lead to `undercooked_pork_exposure`. This redundancy is intentional design:
- Players who ask the right question get direct path
- Players who engage family get alternate path
- Relational outcome rewards talking to Diego even if diagnostically redundant

This is good scenario design: reward curiosity without punishing focused play.

---

## Summary of Changes

### Files Created
- `schemas/case-definition.schema.json` (661 lines)
- `packages/satori/src/satori/models/case_definition.py` (427 lines)
- `cases/example-neurocysticercosis.json` (791 lines)
- `packages/satori/tests/test_case_schema.py` (266 lines)

### Files Modified
- `packages/satori/pyproject.toml` (added pydantic>=2.0.0, updated line-length to 120)

### Bugs Fixed (Post-Review)
1. **Node 08:** Moved `wrong_treatment_steroids` flag from `on_activate` to `effects.on_reveal`
2. **Node 12:** Added `undercooked_pork_exposure` to `effects.on_reveal`
3. **CaseDefinition:** Added `model_config = ConfigDict(extra="ignore")`

### Commits
- `a1f80f5`: feat(schema): case definition schema and example case
- `aa2f7cc`: chore: remove test placeholder (replaced by comprehensive test suite)
- (pending): fix: correct flag timing and diagnostic paths in example case

---

## Next Steps

### For Ho 02 (Satori Engine Implementation)
1. **Formalize Action Types:** Document canonical base action types and subcategories. Build validation that checks action strings against known types without requiring a rigid enum.

2. **Implement Flag System:** The engine needs a `GameState` that tracks:
   - Set flags (set[str])
   - Active nodes (set[str])
   - Revealed nodes (set[str])
   - Node timers (dict[str, Timer])

3. **Implement Condition Evaluator:** Function that takes a `Condition` and `GameState` and returns bool. The OR-of-ANDs logic sits one layer above this.

4. **Timer System:** Needs to support:
   - Stage-based effects
   - Pause conditions (re-evaluate every tick)
   - Acceleration (modify_timer effect)

5. **Effect Executor:** Function that takes an `Effect` and mutates `GameState`. Needs to handle:
   - Flag operations (set, clear)
   - Node activation
   - Timer modification
   - Action locking/unlocking
   - Vital sign changes

### For Anamnesis (Case Generation)
1. The schema is the contract. Anamnesis must generate valid JSON against this schema.
2. Consider using the Pydantic models directly in Anamnesis to validate generated cases before writing to disk.
3. The example case is a reference implementation — Anamnesis should study its patterns.

---

## Reflection

This was a foundational task executed well. The agent delivered a working schema, validated it against a realistic example case, and caught validation issues early through comprehensive testing. The three bugs found in review were all subtle timing/logic issues, not structural problems.

The schema strikes a good balance between constraint and flexibility. It's strict enough to catch malformed cases (missing required fields, invalid references) but flexible enough to accommodate the natural variability of medical scenarios (action subcategories, optional narrative hooks, timer stage counts).

The example case is pedagogically valuable — it demonstrates timer-based progression, patient death paths, wrong treatment consequences, and multiple diagnostic routes. Future case authors will have a clear reference.

The node-graph architecture feels right. The separation between activation (when a node becomes live) and reveal (when the player discovers it) is crucial. The flag-based dependency system is simple but powerful.

**Ready to build the engine.**
