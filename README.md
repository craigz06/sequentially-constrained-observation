# Sequentially Constrained Observation (EXP7 / H5)

**Author:** Craig C. Cline
**Location:** Clyde, North Carolina
**Site:** seeitwith.org

---

## The Question

Can sequential, commitment-before-advance observation produce a **verifiable, non-hindsight record** that a full-context ("spacetime") observer structurally cannot produce — even given the same model and equal or greater compute?

This is **H5**, tested by **EXP7**. It is a narrower, more specific claim than the related situated-cognition work in [`spatial-query-rig`](https://github.com/craigz06/spatial-query-rig) (does *grounding in a known place* improve answers?). EXP7 asks a different question: does *when information arrives* — one frame at a time with a forced commitment, vs. all at once — change what an AI can honestly claim to have known before the outcome. Related family of ideas, not the same experiment. Keeping them in separate repos on purpose, so results from one are never accidentally pooled with the other.

---

## Related Work

This experiment is the operational descendant of the J-M Effect white paper — the hypothesis that sequential frame delivery produces a temporal "snap," the same cognitive operation as stereo depth snap but on the time axis.

- **White paper:** J-M Effect v4.5 (Zenodo, published April 22, 2026) — [DOI: 10.5281/zenodo.19697860](https://doi.org/10.5281/zenodo.19697860)
- **Related repository:** [`spatial-query-rig`](https://github.com/craigz06/spatial-query-rig) — tests whether grounding observation in a fixed, calibrated space (via camera-to-floor-plan homography) adds verifiable structure, as distinct from the delivery-order question tested here

---

## The Method

For each clip, three passes:

1. **Frame-agent pass** — N independent, stateless API calls, one per frame. Each call sees exactly one image, no history, no other frames. A real information barrier, not a role the model plays.
2. **Synthesis pass** — a single growing conversation. Frame-agent reports are revealed one at a time, in true temporal order. Before each next report, the model must commit to its current best account. Revisions are only allowed as *explicit, named* violations of a prior commitment — never quietly absorbed.
3. **Block-model (spacetime) pass** — one single call, all frames attached at once, asked to simulate what a sequential trace would have looked like. Explicitly labeled hindsight-informed, not verifiable.

Two conditions:

- **SC (Substrate-Controlled)** — both arms on the same model. Isolates delivery mode as the only variable. This is the condition that actually tests H5.
- **CS (Cross-Substrate)** — sequential on one model, spacetime on another. Kept separate, never pooled with SC when evaluating H5.

Full design, scoring rubric, and pre-registered success/failure criteria: [`protocol/EXP7_replication_protocol.md`](https://github.com/craigz06/sequentially-constrained-observation/blob/main/protocol/EXP7_replication_protocol.md).

---

## Status

5 runs logged as of 2026-07-12 (REPL-000 through REPL-003b). See [`logs/exp7_run_log.json`](https://github.com/craigz06/sequentially-constrained-observation/blob/main/logs/exp7_run_log.json) for the full accumulating record, including notes and protocol deviations per run. *(Update this date whenever a new run is logged.)*

Current state honestly: mixed and still open. Full-confabulation failures have occurred on *both* arms in some runs (not what H5 predicts). A frame-extraction gap was caught and diagnosed mid-project (fps=5 sampling missed the actual contact frame in one clip entirely — see REPL-003 vs REPL-003b). Correcting extraction measurably changed model output at the frame that mattered, but did not yet produce a fully confirmed result. Not yet at N=5 SC clips; this is early.

---

## Getting Started

To run the pipeline yourself, start with [`SETUP.md`](https://github.com/craigz06/sequentially-constrained-observation/blob/main/SETUP.md) for environment setup, then [`session_start.md`](https://github.com/craigz06/sequentially-constrained-observation/blob/main/session_start.md) for how to begin a session.

---

## Repository Structure

- `protocol/` — the locked replication protocol and run-log schema
- `logs/` — the accumulating run log (`exp7_run_log.json`), the actual data the protocol's criteria get evaluated against
- `pipeline/` — `run_exp7.py` (single-pass runner) and `run_exp7_resumable.py` (checkpointed driver for clips too large to run in one pass — parallelizes the independent frame-agent calls, keeps the synthesis pass strictly sequential)
- `clips/` — source video clips used in logged runs
- `research_memory/` — snapshot of the broader project research memory, included for context since EXP7 draws on hypotheses (H1, H5, H6) and prior decisions (D5, D7, D9) documented there. Not EXP7-exclusive — covers the wider project.

---

*The instrument states what it sees.
The analyst has the final word.*
