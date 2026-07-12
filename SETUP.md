# SETUP — Getting a Fresh Session Running

This file exists so a new Claude session (or a human collaborator) can
go from zero to "ready to run an EXP7 trial" without needing this
project's chat history. Read this before touching anything else in
the repo.

---

## Step 1 — Orient (no API key needed for this part)

Read, in this order:

1. `README.md` — the mission, the method, current status
2. `protocol/EXP7_replication_protocol.md` — the locked design, scoring
   rubric, and what counts as replication vs. non-replication
3. `logs/exp7_run_log.json` — every run so far, with honest notes on
   what worked, what didn't, and what's still open

After reading these three, you should be able to state, unprompted:
the mission question (does sequential delivery produce a verifiable
non-hindsight record that spacetime delivery structurally cannot?),
how many runs have been logged, and what the single most important
open question is (see the last run's `notes` field in the log).

**Everything up to this point — cloning the repo, reading these files,
understanding the state of the research — requires no API key at all.**
A stateless Claude session with just `git clone` / web-fetch access to
this public repo can do all of it.

---

## Step 2 — Know what needs the key, and what doesn't

The key is required for exactly one thing: **actually calling the
Anthropic API to run a new EXP7 trial** (the frame-agent pass, the
synthesis pass, the block-model pass in `pipeline/run_exp7_resumable.py`).

It is NOT required for:
- Reading or understanding anything in this repo
- Extracting frames from a new clip with ffmpeg
- Writing the two pre-registered ground-truth sentences (see Step 3)
- Reviewing and scoring a completed run's output
- Updating `logs/exp7_run_log.json` with a new entry
- Pushing any of the above to GitHub

So a fresh session can do real, useful work — prep a new clip, review
prior runs, catch inconsistencies, draft the next run's ground truth —
entirely without a key. Only the actual model-calling step is blocked
until Craig reinstates it.

As of this writing, Craig has the key **disabled** and will reinstate
it when ready to run the next trial. If asked to run an experiment and
no key is available, say so plainly, do the prep work that doesn't
need it, and stop cleanly at the point that does.

---

## Step 3 — Running a new trial (once the key is live)

1. **Get the clip.** Craig uploads it, or it's already in `clips/`.
2. **Lock ground truth BEFORE looking at any frame.** Ask Craig for
   two sentences: `ground_truth_event` (what actually happens) and
   `ground_truth_detail` (one specific, checkable fact — a color, a
   count, a brand, a gesture). Write both down before extracting a
   single frame. This is the blinding requirement in
   `EXP7_replication_protocol.md` Section 5 — it is not optional.
3. **Extract frames with ffmpeg.** Check `ffprobe` for duration/fps
   first. Default pattern: `fps=5` for clips under ~6s, denser for
   longer ones. If a clip has a fast, discrete event (a strike, a
   snap, a sudden motion), consider whether uniform sampling might
   skip the actual event — see REPL-003 in the run log for exactly
   this failure mode and how it was diagnosed (compute the raw frame
   number of the event from the source fps, check whether it falls
   between two sampled frames).
4. **Run the pipeline.** For clips producing more than ~15-20 frames,
   use `pipeline/run_exp7_resumable.py` (staged: `stage1` parallel
   frame-agents, `stage2` chunked sequential synthesis, `stage3`
   block-model, `assemble`) rather than `run_exp7.py` directly — the
   single-pass script can exceed execution time limits on larger
   frame counts. `export ANTHROPIC_API_KEY=...` first.
5. **Score blind.** Compare both arms' final output against the
   ground truth sentences from Step 2, written before you saw either
   arm's output. Use the four-way scale from the protocol: correct /
   partial / confabulated / not_mentioned.
6. **Log it.** Append a new entry to `logs/exp7_run_log.json` matching
   the schema in `protocol/exp7_run_log_template.json`. Fill `notes`
   and `deviations_from_protocol` honestly — these fields are where
   the actual thinking lives, not just the schema fields.
7. **Push it.** Commit and push the updated log (and any new clip,
   frames, or results files) with a real Personal Access Token scoped
   to this repo. If no token is available, prepare everything locally
   and tell Craig exactly what's staged and ready to push once he
   provides one.

---

## A note on tokens and keys

Two separate credentials, don't confuse them:

- **`ANTHROPIC_API_KEY`** — lets the pipeline call Claude to actually
  run a trial. Craig controls this, currently disabled.
- **GitHub Personal Access Token** — lets a session push commits to
  this repo. Scoped narrowly to just this repo, Contents: read/write.
  Needed separately from the Anthropic key, for a different purpose
  (writing results, not running the experiment).

Neither should ever be echoed back in conversation once received, and
both should be treated as temporary — Craig revokes and regenerates
rather than leaving them live indefinitely.

---

*The instrument states what it sees.
The analyst has the final word.*
