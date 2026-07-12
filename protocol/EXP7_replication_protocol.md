# EXP7 Replication Protocol v1.0

**Pre-registered 2026-07-10, before any replication runs.**

This document is written and locked *before* the next trial is run, specifically so that scoring criteria, sample size, and what counts as success or failure cannot drift to match whatever the data happens to show. If reality forces a deviation from this protocol, the deviation gets logged in the run record as a deviation — not silently absorbed.

---

## 1. What we are actually testing now

The first EXP7 run (2026-07-10) produced two distinct findings that this protocol treats separately, because they need different kinds of replication:

**Finding A — Verifiability (structural).** The sequential trace is auditable by construction; the spacetime trace is not. This does not need replication in the statistical sense — it's true by architecture, not by observation. It's included here only so future runs keep stating it correctly rather than letting it blur into Finding B.

**Finding B — Accuracy asymmetry (empirical, N=1, confounded).** The sequential arm (ChatGPT) was accurate; the spacetime arm (Gemini) confabulated a specific wrong event and a wrong object detail. This is what needs replication. Right now it is confounded by substrate — we don't know if this was "sequential beats spacetime" or "ChatGPT beats Gemini at this kind of task, independent of delivery mode."

**This protocol exists to test Finding B specifically, with the substrate confound removed.**

---

## 2. Primary hypothesis and pre-specified prediction

**H5 (from research memory):** Sequential, commitment-before-advance observation produces a verifiable, non-hindsight record; full-context observation cannot produce an equivalently verifiable record and is specifically vulnerable to confident confabulation under hindsight.

**Prediction this protocol tests:** When the SAME model is run in both the sequential arm and the spacetime arm (only delivery mode differing), the sequential arm will show a lower rate of confabulated (factually wrong, confidently stated) claims about discrete physical events than the spacetime arm.

**Pre-specified null result:** If the two arms show statistically indistinguishable confabulation rates when substrate is held constant, Finding B does not replicate under controlled conditions — meaning the original result was substrate-driven (a Gemini-specific tendency), not a sequential-vs-spacetime effect. This would be a real, useful, negative result, not a failure of the experiment.

---

## 3. Design

### 3.1 Substrate control (the key change from run 1)

Two conditions, run in parallel for every clip:

- **Condition SC (Substrate-Controlled):** Both arms run on the *same* model. Sequential arm = that model fed frames one at a time (stateless calls, real information barrier). Spacetime arm = that same model given the full video/frame-set at once. This isolates delivery mode as the only variable.
- **Condition CS (Cross-Substrate):** Kept as a *separate*, clearly labeled condition — sequential on Model A, spacetime on Model B (e.g., the original ChatGPT/Gemini pairing, or others). This is not discarded — cross-substrate convergence is independently interesting per the J-M white paper's existing method — but it must never be pooled with Condition SC data when assessing Finding B specifically.

Every run gets logged with an explicit `condition: SC` or `condition: CS` tag. No exceptions.

### 3.2 Sample size

**Minimum for this round: 5 clips**, each run under both Condition SC and Condition CS (10 total trials). This is not a statistically powered sample — it's a pragmatic next step sized to what's actually achievable by hand or with light automation, chosen deliberately over the trap flagged in the research memory (P6: perpetual refinement without decisive tests). 5 is enough to see whether the pattern from run 1 shows up again at all, not enough to publish a rate. If the direction still looks promising at N=5, the automation pipeline (run_exp7.py) becomes worth finishing properly for a real N.

### 3.3 Stimulus design criteria

Each clip must satisfy all of the following, to keep clips comparable to run 1 and to each other:

1. **Real footage, not AI-generated.** (Run 1's methodological lesson: synthetic footage introduces generator-artifact confounds unrelated to the hypothesis.)
2. **Locked-down camera.** No panning — camera motion contaminates motion-based event detection (this is the same bug D7 already found in DCI's trigger layer).
3. **Three-phase structure:** (a) establish a baseline/expectation, (b) hold long enough for a specific prediction to form, (c) one sharp, discrete, checkable event that violates the held expectation. Vague or gradual events (like the wave clip) are acceptable as a *secondary* category but should not be the primary 5 — discrete events give an unambiguous timestamp and an unambiguous ground-truth claim to check confabulation against.
4. **A checkable ground-truth detail** independent of the motion itself — an object with legible text/brand, a specific color, a countable quantity — something the spacetime arm could plausibly get wrong in a checkable way (this is what caught Gemini's "PILOT G2" fabrication; without a checkable detail, confabulation is harder to prove rather than merely suspect).
5. **4–12 seconds.** Long enough to have a real hold phase, short enough to keep frame counts and manual labor manageable.

### 3.4 Frame extraction procedure (reuse run 1's method)

For each clip: compute a frame-to-frame motion-diff profile first (objective, not eyeballed) to locate phase boundaries, then extract 8–12 frames concentrated around the transitions (baseline → entry → hold → event → settle), same procedure already validated in run 1 and in the earlier ball/box design.

---

## 4. Scoring rubric (pre-specified, applied identically to every run)

Each arm's final trace gets scored by a human (Craig, or a third party if available — see §5 on blinding) against three independent axes. This is deliberately not a single pass/fail — collapsing to one number is exactly the kind of premature closure the research memory's own confidence-tier discipline warns against.

| Axis | Score | Definition |
| :---- | :---- | :---- |
| **Verifiability** | Structural / Not structural | Is the trace architecturally auditable to a specific pre-outcome commitment point, or not? (This will always score "Structural" for sequential and "Not structural" for spacetime by construction — recorded for completeness, not as a variable.) |
| **Event accuracy** | Correct / Partial / Confabulated | Did the trace correctly identify *what* the discrete event was? "Partial" = got the general nature right but missed a specific detail (cf. run 1's doorway miss). "Confabulated" = asserted a specific, checkable claim that is factually false (cf. run 1's "pen snapped"). |
| **Detail accuracy** | Correct / Not mentioned / Confabulated | For the pre-planted checkable ground-truth detail (§3.3.4): did the trace get it right, not mention it at all, or state something specific and wrong? |

A run only counts as a confabulation instance if **Detail accuracy = Confabulated** or **Event accuracy = Confabulated** — not merely "vague" or "incomplete." This bar was deliberately set where run 1's actual finding cleared it easily (a specific wrong brand name, a specific wrong physical event), so the rubric isn't retrofitted to be easier than what already happened.

---

## 5. Blinding (upgrade from run 1)

Run 1 was scored by Claude (this session) with full knowledge of ground truth throughout — acceptable for a first exploratory pass, but it means the auditor was never blind. For replication:

- **Minimum bar:** whoever scores each trace should note the ground truth *before* reading the arm's output, write down the ground-truth claim in one sentence, then read the trace and mark correct/partial/confabulated against that pre-written sentence — not against an impression formed while reading.
- **Better, if feasible:** a second person (or a fresh Claude session with no memory of this conversation) scores independently from the same pre-written ground-truth sentence, and disagreements get logged rather than silently resolved by the primary scorer.

---

## 6. What counts as replication vs. non-replication

- **Replicates:** Condition SC shows confabulation in the spacetime arm on 2+ of 5 clips, with 0-1 confabulations in the matched sequential arm. (Threshold chosen to be clearly above chance/noise while staying achievable at this sample size — revisit if the automated pipeline later allows a real powered study.)
- **Does not replicate (informative negative):** Confabulation rates are similar across both arms under Condition SC. Logged as: the original result was likely substrate-specific (a ChatGPT vs. Gemini difference), not a sequential-vs-spacetime effect. This downgrades Finding B but does NOT touch Finding A (verifiability remains structurally true regardless).
- **Ambiguous:** Mixed results, small numbers making the pattern unclear. Logged honestly as ambiguous, with a recommendation to extend to the full automated sample before concluding either way.

---

## 7. Per-run documentation template

Every trial gets logged in this exact structure (matching the JSON schema in `exp7_run_log_template.json`), so results accumulate comparably:

run_id, date, condition (SC/CS), clip_file, clip_duration_s,

ground_truth_event (one sentence, written before scoring),

ground_truth_detail (one sentence, written before scoring),

sequential_arm: {substrate, full_trace_or_link, event_accuracy, detail_accuracy},

spacetime_arm: {substrate, full_trace_or_link, event_accuracy, detail_accuracy},

scorer, blinded (yes/no), deviations_from_protocol (if any), notes

---

## 8. Explicit non-goals of this round

To guard against scope creep (per P6 in the research memory — the "perpetual refinement" risk):

- This round is NOT trying to establish a publishable confabulation *rate*. N=5 per condition is a direction check, not a study.
- This round is NOT testing H1 (the original motion-coherence hypothesis) — that remains a separate, still-untested claim (Q2).
- This round is NOT trying to build the full multi-agent D5 architecture. Stateless-per-frame calls satisfy the information-barrier requirement for this purpose; the more elaborate frame-agent/synthesis-agent split can wait for a version where it's actually load-bearing.

---

**Status: LOCKED as of 2026-07-10.** Any deviation during actual runs must be recorded in that run's log, not folded silently into this document.
