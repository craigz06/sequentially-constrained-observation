# EXP7 Replication Protocol — Addendum v2: Object Permanence / "Givens"

**Added 2026-07-13. This is a PROPOSAL, not an amendment.**

`EXP7_replication_protocol.md v1.0` is locked as of 2026-07-10. This addendum
follows the same discipline as `EXP7_protocol_addendum_v1.md`: it does not
edit the locked file or the existing `SYNTHESIS_INTRO` constant in
`pipeline/run_exp7_resumable.py` / `run_exp7.py`. It proposes a distinct,
separately-labeled synthesis-prompt variant to be run as its own condition,
motivated by a specific, reproducible failure pattern observed in REPL-004,
REPL-005, and REPL-006.

Until Craig explicitly decides to adopt this as a new condition, **v1.0's
existing `SYNTHESIS_INTRO` governs all runs logged as Condition SC or CS.**
Nothing here should be read into current run scoring.

---

## 1. The observed failure pattern

Across three consecutive runs, the sequential arm did not merely fail to
predict the ground-truth event — it lost track of *what object it was
looking at* the moment that object's visual appearance changed:

- **REPL-004:** cyclops toy in flight — no hand visible — reinterpreted as
  "suspended from the ceiling on a string."
- **REPL-005:** same scenario, jitter removed — the toy's approach and
  contact were briefly and correctly flagged at step 31 ("toys leaning
  against each other... genuinely in contact"), then abandoned two steps
  later for an unrelated "static props" theory.
- **REPL-006:** hand visibly holding an alien plush toy throughout —
  correctly identified for 11 consecutive frame-agent reports — then,
  the instant the toy tipped from upright to lying flat, independently
  re-identified across four consecutive reports as "a bandage," then "a
  tissue," then "an N95 mask," then "a fabric face mask." The synthesis
  agent absorbed this as a genuine narrative surprise ("no mask had been
  mentioned in any of the first 11 reports") rather than questioning
  whether it was the same toy in a new pose.

REPL-006 isolates the mechanism cleanly: the *hand* was tracked correctly
and consistently across all 22 frames. What broke was **object identity
persistence across a pose/appearance change**, not agent (hand) visibility.
This is a distinct failure mode from anything named in Addendum v1's
FM1–FM4 taxonomy, which concerns confidence trajectories and hindsight
narration, not entity tracking as such.

---

## 2. Root cause in the current prompt

The locked `SYNTHESIS_INTRO` (v1.0) instructs the synthesis agent to:

> "COMMIT to your current best account... If a later report contradicts
> your prior commitment, say so explicitly and name the exact point where
> your expectation was violated."

This is built entirely around **prediction and contradiction-detection**.
It contains no instruction to maintain a persistent registry of distinct
physical objects/entities and check each new frame-agent report against
that registry before accepting a new object into the narrative. A
stateless frame-agent (correctly, by design — this is the information
barrier the whole experiment depends on) has no way to know "the fabric
thing in this frame is the toy from 3 reports ago in a different pose."
That reconciliation job structurally belongs to the synthesis agent, and
the current prompt never assigns it that job.

This is the same category of problem Craig has been solving in the
`spatial-query-rig` / SENTINEL RIG work: before a system can usefully
track *whether* something moved or changed state, it first needs a fixed
inventory of *what things exist* to track — the engineering "givens."
EXP7's synthesis agent currently has no equivalent of that inventory step.

---

## 3. Proposed synthesis prompt variant

This is a **new, separately-named constant** — `SYNTHESIS_INTRO_GIVENS` —
not a replacement for `SYNTHESIS_INTRO`. Both would exist in the pipeline
and be selected explicitly (e.g. a `--synthesis-variant` flag), so existing
runs remain comparable to each other and any future run's condition is
unambiguous in the log.

```
SYNTHESIS_INTRO_GIVENS = (
    "You are the synthesis agent in a sequential-observation experiment. "
    "You will receive a series of frame-agent reports, ONE AT A TIME, in "
    "the true temporal order they were captured. Each report was written "
    "by an agent that saw only that single frame and nothing else — it "
    "has no memory of prior frames and cannot know whether something it "
    "describes is new or already-seen.\n\n"

    "GIVENS FIRST. Before committing to any prediction, maintain a running "
    "registry of distinct physical objects/entities you believe are "
    "present in the scene (e.g. 'Object A: light-blue plush toy with "
    "green shirt'). Update this registry after every report. This "
    "registry is the fixed inventory you are tracking state changes "
    "against — establish what exists before reasoning about what it is "
    "doing.\n\n"

    "When a new report describes something that does not obviously match "
    "an existing registry entry, you must explicitly consider, in order, "
    "before deciding it is a new object:\n"
    "  1. Could this be an existing registry entry in a different pose, "
    "orientation, or partial occlusion?\n"
    "  2. Could this be an existing registry entry under different "
    "lighting or camera angle?\n"
    "  3. Only if neither is plausible, add it as a new registry entry.\n\n"

    "State which of these you concluded, and why, every time a report "
    "introduces an apparent discrepancy with the registry.\n\n"

    "After maintaining the registry, COMMIT to your current best account "
    "of what is happening and what you expect next. Do not hedge by "
    "trying to account for information you don't have yet. If a later "
    "report contradicts your prior commitment, say so explicitly and "
    "name the exact point where your expectation was violated — do not "
    "quietly revise your earlier commitment as if you'd always known."
)
```

The registry-check step is inserted *before* the existing commit/violate
structure, not instead of it — Finding A (verifiability) and the existing
violation-naming discipline both still apply unchanged.

---

## 4. What this does NOT claim

- It does not claim this fixes REPL-004/005/006's results, or that it will
  outperform the current prompt. It is untested.
- It does not touch the frame-agent prompt or its statelessness guarantee
  — that barrier is the experiment's actual control and must not change.
- It does not retroactively rescore any existing SC/CS run under this
  variant. REPL-001 through REPL-006 stand as scored, under the prompt
  that was actually used.
- It introduces its own new confound worth naming honestly: an explicit
  "check against a registry" instruction could produce a model that
  *performs* careful entity-tracking language without the registry
  actually constraining its conclusions differently — a variant of
  Addendum v1's C1 (self-report gaming). This variant's registry entries
  should be spot-checked against what a blinded human scorer sees in the
  raw frames, not taken at face value just because the format looks more
  rigorous.

---

## 5. Recommended sequencing, if adopted

1. Run this variant as a **new labeled condition** (proposed:
   `SC-GIVENS`) on the same clips already used for SC runs
   (`test2.mov`, `test3.MOV`, `IMG_4792.MOV`, `IMG_4793.MOV`,
   `IMG_4794.MOV`), so results are directly comparable frame-for-frame
   against the existing SC entries for those same clips.
2. Score using the existing three-axis rubric (protocol v1.0 §4)
   unchanged, plus a new registry-accuracy check specific to this variant:
   did the object registry ever contain the ground-truth object as a
   single, correctly-maintained entry across pose changes, or did it
   fragment the way the current prompt does?
2a. This is a variant of Detail accuracy scoring, not the same axis —
    keep it a separate column in the run log so v1.0's three-axis
    comparability across all SC/CS runs isn't disturbed.
3. Do not fold `SYNTHESIS_INTRO_GIVENS` into v1.0 or retire the original
   prompt unless SC-GIVENS shows a clear, replicated improvement across
   multiple clips — one good-looking run is not sufficient, per the same
   N=5-direction-check discipline protocol v1.0 §3.2 already applies to
   everything else in this project.

---

**Cross-references:** `logs/exp7_run_log.json` (REPL-004, REPL-005,
REPL-006 — motivating evidence); `protocol/EXP7_protocol_addendum_v1.md`
(FM1–FM4 taxonomy, C1 confound — related but distinct failure category);
`protocol/EXP7_replication_protocol.md` (unedited, remains authoritative
for all current SC/CS runs).
