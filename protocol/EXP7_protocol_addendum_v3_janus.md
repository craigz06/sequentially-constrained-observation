# EXP7 Replication Protocol — Addendum v3: Janus (Backward-Facing Visual Memory)

**Added 2026-07-13. This is a PROPOSAL, not an amendment.**

`EXP7_replication_protocol.md v1.0` is locked as of 2026-07-10. This addendum
follows the same discipline as Addendum v1 and v2: it does not edit the
locked file or replace the existing `SYNTHESIS_INTRO` constant. It proposes
a third, separately-labeled synthesis condition — **SC-JANUS** — motivated
by a prototype result that directly resolved the object-permanence failure
named in Addendum v2, where the v2 registry-instruction approach did not.

Until Craig explicitly decides to adopt this as a real condition, **v1.0's
existing `SYNTHESIS_INTRO` governs all runs logged as Condition SC or CS.**
Nothing here should be read into current run scoring.

---

## 1. The name, and what it does NOT mean

Named after Janus, the god who looks two directions at once — but this
variant is deliberately **one-faced, not two**. It looks backward only,
with full visual memory of everything already revealed. It has **zero**
access to anything ahead. This is the load-bearing design constraint of
the whole proposal and must never be relaxed: giving the synthesis agent
forward access (the full video, or any future frame) would collapse it
into a spacetime/block-model arm wearing a sequential disguise, destroying
Finding A (verifiability-by-construction) entirely. An earlier version of
this idea, floated in conversation, proposed attaching a full-clip
spacetime summary alongside the frame-by-frame delivery — that version was
rejected for exactly this reason before this narrower one was tested.

**What Janus adds over the locked v1.0 synthesis pass:** at each synthesis
step, the model receives the frame-agent's text report AND the actual
image for that frame, attached directly to the growing conversation.
Because the full message history is resent on every API call — the same
mechanism v1.0 already uses for the text-only trace — every previously
shown image remains visible automatically. This requires no new
architecture, only attaching an image alongside each step's text.

---

## 2. Motivating evidence: prototype result on REPL-006's clip

A one-off prototype (`janus_prototype.py`, not part of the tracked
pipeline, run outside the checkpoint schema) was run on the exact same 22
frame-agent reports and frame images as REPL-006 and REPL-007, for direct
three-way comparability. Result, at the same critical frames where both
prior conditions failed (Reports 12–15, where the alien plush toy tips
from upright to face-down):

- **v1.0 (REPL-006):** frame-agent text reports independently drifted
  from "toy" to "bandage" to "tissue" to "N95 mask" across four
  consecutive reports; the synthesis agent absorbed this as a genuine
  narrative surprise and built a false final account around a
  hallucinated mask.
- **Givens (REPL-007):** correctly shifted destination-tracking to the
  mouse and replaced confident-wrong conclusions with acknowledged
  uncertainty, but still split the toy and the "mask" into two different
  registry entities rather than recognizing them as one.
- **Janus (this prototype):** explicitly rejected the mask
  identification at the frame it first appeared, citing specific visual
  evidence not available to the text-only frame-agents: *"the frame
  agents for Frames 12 and 13 both misidentified the back of the plush
  toy as a 'white bandage'... looking at the actual images, the rounded,
  smooth white shape is clearly the back of the plush toy's head... The
  antenna wire sticking up from the top confirms this is the plush toy,
  not a mask."* Final account: the toy was "turned face-down and placed
  on the desk near the mouse... never having been placed in front of the
  monitor" — correctly identifying both the destination (mouse, not
  monitor) and the resolution (toy fell/settled near it), matching
  ground truth's causal shape without inventing a new object.

Scored against REPL-006/007's locked ground truth (hand moves alien
puppet toward mouse, puppet falls over onto mouse; alien has two eyes):
**event accuracy — correct** (first "correct" score, as opposed to
partial/confabulated, across any sequential arm on this clip in any
condition tested so far). **Detail accuracy — not_mentioned** (eyes
described only as plural "cartoon eyes," never given an explicit count,
consistent with every prior run on this clip).

---

## 3. One honest caveat from the prototype, not yet resolved

The final summary hedged more than the step-by-step reasoning did. At
steps 13–15, the model was unambiguous: *"I firmly reject [the mask
interpretation] based on visual continuity."* But the final trace
described the mask-vs-toy question as *"never definitively resolved
within the 22-frame sequence"* — walking back its own in-the-moment
confidence when asked to summarize. This is a real gap between
confidence-at-the-time and confidence-in-retrospect, worth watching
across more runs before concluding Janus reliably converts visual access
into a correctly confident final account rather than just a correctly
confident-then-hedged one. This may be its own minor variant of
Addendum v1's FM4 (retrospective-prospective divergence) — worth scoring
for explicitly once more Janus runs exist.

---

## 4. What this does NOT claim

- It does not claim this fixes every clip's confabulation, or that it
  will outperform v1.0 or Givens on stimuli where the failure mode isn't
  object-permanence-under-pose-change (e.g. REPL-001/002's total
  hallucination of objects never in frame at all — untested under Janus).
- It does not touch the frame-agent prompt or its statelessness guarantee.
  The frame-agent pass is completely unaffected and remains the real
  information barrier the whole experiment depends on.
- It does not retroactively rescore REPL-001 through REPL-007.
- It introduces a real cost worth naming plainly: token usage grows much
  faster than the text-only trace, since each step attaches a new image
  on top of an already-accumulating image history. On a 22-frame clip
  this was manageable; on REPL-005's 59-frame clip, the final synthesis
  call would carry roughly 59 images plus all prior text. Untested
  whether this causes degraded attention/performance at that scale, or
  simply higher cost — both are open questions before running Janus on
  longer clips.
- It has been validated on exactly one clip, one run, no blinding beyond
  ground truth being locked before this session began (ground truth was
  written for REPL-006 before Janus existed as an idea, so this specific
  scoring is not compromised — but this is N=1 for the Janus condition
  itself and should be treated with the same caution as any single run).

---

## 5. Recommended sequencing, if adopted

1. Wire `SYNTHESIS_INTRO_JANUS` into `pipeline/run_exp7_resumable.py` as a
   third `--variant janus` option, alongside the existing `v1` (default)
   and `givens` options — not a replacement for either.
2. Run SC-JANUS on the same clip set already used for SC (and where
   applicable, SC-GIVENS) — `test2.mov`, `test3.MOV`, `IMG_4792.MOV`,
   `IMG_4793.MOV`, `IMG_4794.MOV` — for direct per-clip comparability
   across all three conditions.
3. Score using the existing three-axis rubric unchanged, plus the same
   registry/continuity check proposed in Addendum v2 §5, adapted: did the
   final account maintain a single, correctly-identified object across
   any pose change present in the clip, and did the model's stated
   confidence at the critical frame match its stated confidence in the
   final summary (the §3 caveat above)?
4. Do not retire `SYNTHESIS_INTRO` (v1.0) or `SYNTHESIS_INTRO_GIVENS`
   unless SC-JANUS shows a clear, replicated improvement across multiple
   clips — one strong prototype result is motivating evidence, not
   sufficient evidence, per the same N=5-direction-check discipline
   applied everywhere else in this project.
5. Test on a longer clip (REPL-005's 59-frame `IMG_4793.MOV` is the
   obvious candidate) specifically to check the token-growth/attention
   concern in §4 before assuming Janus scales cleanly.

---

**Cross-references:** `logs/exp7_run_log.json` (REPL-006, REPL-007 —
motivating evidence this addendum directly responds to);
`protocol/EXP7_protocol_addendum_v1.md` (FM1–FM4 taxonomy — §3's caveat
may be a minor variant of FM4); `protocol/EXP7_protocol_addendum_v2_givens.md`
(the registry-instruction approach this supersedes in effectiveness on
the one clip tested, though not necessarily in general — both remain
live proposals); `protocol/EXP7_replication_protocol.md` (unedited,
remains authoritative for all current SC/CS runs).
