# EXP7 Replication Protocol — Addendum v1

**Added 2026-07-13. This is a PROPOSAL, not an amendment.**

`EXP7_replication_protocol.md v1.0` is locked as of 2026-07-10, per its own closing line: *"Any deviation during actual runs must be recorded in that run's log, not folded silently into this document."* This addendum follows that discipline — it does not edit the locked file. It records what a future `v1.1` unlock should consider, sourced from a separate conversation (external AI critique, reconciled and logged in `sco_research_memory_v3_3.json` under `literature_grounding`, `failure_mode_taxonomy`, and `confounds`).

Until Craig explicitly decides to unlock and revise the protocol, **v1.0 governs all actual runs as written.** Nothing here should be read into current run scoring.

---

## What this adds, in one paragraph

Beyond the existing three-axis rubric (verifiability / event accuracy / detail accuracy, protocol §4), there are four named candidate failure modes worth scoring for once the reliability of the instrument itself is confirmed (see `research_memory` D9 and protocol §1–2), each with a literature anchor rather than a claim of novelty — and two confound controls the current 5-clip stimulus design doesn't yet require.

## Candidate scoring additions (see `sco_research_memory_v3_3.json` → `failure_mode_taxonomy` for full definitions)

| ID | Name | One-line check |
|----|------|-----------------|
| FM1 | Commitment inversion | Does stated confidence in a hypothesis rise even as new evidence contradicts it? |
| FM2 | Revision latency | How much contradicting evidence accumulates before the leading hypothesis actually shifts? |
| FM3 | Hypothesis recovery failure | Does a dropped early hypothesis ever get reconsidered when later evidence re-supports it? |
| FM4 | Retrospective-prospective divergence | Does the post-hoc "what told you" account match where the trace's confidence actually moved at the time? |

FM4 is flagged in the source material as the most defensible of the four — it maps most directly onto a single, well-replicated literature (hindsight bias, Fischhoff 1975) and depends least on special stimulus design. If v1.1 adopts only one addition, this is the recommended first one.

## Confound controls not yet in v1.0 §3.3

- **C1 — Self-report gaming:** current `run_exp7.py` prompts (`FRAME_AGENT_PROMPT`, `SYNTHESIS_INTRO`) have not been audited for whether they signal the test structure to the model. If a model can infer it's being checked for hindsight-softening, it may perform correct-looking uncertainty without the trace reflecting genuine belief revision either way.
- **C2 — Narrative misdirection confound:** the current 5-clip criteria (v1.0 §3.3) don't require a misdirection / no-misdirection matched pair. Without one, an FM1 (commitment inversion) finding can't be distinguished from ordinary "misleading content misled a competent reasoner."

## What this addendum does NOT propose

- It does not change the existing three-axis rubric, the N=5 sample size, the blinding procedure, or the SC/CS condition split. Those stand as locked.
- It does not claim FM1–FM4 have been observed in any run. Status for all four, as of this writing: candidate only, not yet operationalized against `exp7_run_log.json`.
- It does not resolve C1 — that requires an actual prompt audit, not yet done.

## Recommended sequencing

1. Finish instrument-reliability validation (protocol v1.0's own prerequisite, D9) before scoring for any of FM1–FM4 — a trajectory that isn't reliably reproducible isn't worth pathology-hunting in.
2. Audit `run_exp7.py` prompts against C1.
3. If Craig decides to unlock the protocol, fold FM4 in first as a fourth scoring axis, with C2's matched-pair requirement added to §3.3's stimulus criteria at the same time — the two are linked (FM1 is the mode C2 is designed to protect against misattributing).

---

**Cross-references:** `research_memory/sco_research_memory_v3_3.json` (`literature_grounding`, `failure_mode_taxonomy`, `confounds`, `Q8`); `protocol/EXP7_replication_protocol.md` (unedited, remains authoritative for all current runs).
