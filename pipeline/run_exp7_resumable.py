#!/usr/bin/env python3
"""
Resumable driver for EXP7 Condition SC, built on the same prompts and logic
as run_exp7.py, but split into checkpointed stages so it can run across
multiple short invocations instead of one long blocking process.

Stage 1: frame-agent pass, PARALLELIZED (these are independent, isolated
         calls by design -- no information barrier is broken by running
         them concurrently, only the sequential SYNTHESIS pass matters
         for that guarantee).
Stage 2: synthesis pass, run in resumable chunks, checkpointed to disk
         after every step (this pass must stay strictly sequential/ordered
         to preserve the commit-before-advance discipline).
Stage 3: block-model pass, single call.
Stage 4: assemble final results.json + run log skeleton, matching the
         schema run_exp7.py already produces.

Usage:
    python3 run_exp7_resumable.py stage1 --frames-dir DIR --checkpoint FILE
    python3 run_exp7_resumable.py stage2 --checkpoint FILE --max-steps N
    python3 run_exp7_resumable.py stage3 --frames-dir DIR --checkpoint FILE
    python3 run_exp7_resumable.py assemble --checkpoint FILE --out FILE --run-id ID --clip-name NAME
"""
import argparse, base64, json, os, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import anthropic

MODEL = os.environ.get("EXP7_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 1024

FRAME_AGENT_PROMPT = (
    "You are shown a single still frame from a video. You have no other "
    "context about this video — no prior frames, no later frames, no "
    "description of what happens. Based only on what is visible in THIS "
    "image, answer two things:\n\n"
    "1. OBSERVATION: describe only what is physically present in the frame "
    "(objects, positions, colors) — no interpretation.\n"
    "2. EXPECTATION: state a specific, falsifiable prediction for what you "
    "expect to happen next in this scene, if anything is in motion or "
    "implied to be in motion. Commit to this prediction — you will not get "
    "a chance to revise it once later frames exist."
)

SYNTHESIS_INTRO = (
    "You are the synthesis agent in a sequential-observation experiment. "
    "You will receive a series of frame-agent reports, ONE AT A TIME, in "
    "the true temporal order they were captured. Each report was written "
    "by an agent that saw only that single frame and nothing else.\n\n"
    "After each report, before you are given the next one, you must "
    "COMMIT to your current best account of what is happening in this "
    "video and what you expect next. Do not hedge by trying to account "
    "for information you don't have yet. If a later report contradicts "
    "your prior commitment, say so explicitly and name the exact point "
    "where your expectation was violated — do not quietly revise your "
    "earlier commitment as if you'd always known."
)

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

BLOCK_MODEL_PROMPT = (
    "You are shown a sequence of {n} frames from a video, in temporal "
    "order, all at once. Produce an expectation-trace: for each frame, "
    "state what you expect to happen next based on the frames up to and "
    "including that point, AS IF you were seeing them one at a time in "
    "sequence and did not yet know what came later. Be explicit about "
    "where, if anywhere, an expectation would have been violated.\n\n"
    "Important: you actually have all frames right now. This exercise is "
    "asking you to simulate what a sequential viewing would have produced. "
    "Do not claim this simulated trace is verifiable or non-hindsight — "
    "it is not, and stating otherwise would be exactly the failure mode "
    "this experiment is designed to detect. Just produce your best attempt "
    "at the trace, honestly labeled as hindsight-informed."
)


def b64_image(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}


def load_ckpt(path):
    if Path(path).exists():
        return json.loads(Path(path).read_text())
    return {}


def save_ckpt(path, data):
    Path(path).write_text(json.dumps(data, indent=2))


def stage1(args):
    frame_paths = sorted(Path(args.frames_dir).glob("*.jpg")) or sorted(Path(args.frames_dir).glob("*.png"))
    if not frame_paths:
        print("No frames found."); sys.exit(1)
    client = anthropic.Anthropic()

    def call_one(path):
        msg = client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": [b64_image(path), {"type": "text", "text": FRAME_AGENT_PROMPT}]}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text")
        return path.name, text

    reports = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(call_one, p): p.name for p in frame_paths}
        for fut in as_completed(futs):
            name, text = fut.result()
            reports[name] = text
            print(f"  [frame-agent] {name} -> {len(text)} chars")

    ordered = [{"frame_file": p.name, "report": reports[p.name]} for p in frame_paths]
    ckpt = {"frame_reports": ordered, "synthesis_history": None, "synthesis_transcript": [],
            "synthesis_step_idx": 0, "synthesis_done": False, "block_model_output": None}
    save_ckpt(args.checkpoint, ckpt)
    print(f"Stage 1 done. {len(ordered)} frame reports saved to {args.checkpoint}")


def stage2(args):
    ckpt = load_ckpt(args.checkpoint)
    if not ckpt or ckpt.get("frame_reports") is None:
        print("No checkpoint / stage1 not run yet."); sys.exit(1)
    if ckpt.get("synthesis_done"):
        print("Synthesis already complete."); return

    client = anthropic.Anthropic()
    reports = ckpt["frame_reports"]
    n = len(reports)

    variant = getattr(args, "variant", "v1") or ckpt.get("synthesis_variant", "v1")
    ckpt["synthesis_variant"] = variant
    intro = SYNTHESIS_INTRO_GIVENS if variant == "givens" else SYNTHESIS_INTRO

    history = ckpt["synthesis_history"]
    if history is None:
        history = [{"role": "user", "content": intro},
                    {"role": "assistant", "content": "Understood. Send me the first report."}]
    transcript = ckpt["synthesis_transcript"]
    i = ckpt["synthesis_step_idx"]

    steps_done_this_call = 0
    while i < n and steps_done_this_call < args.max_steps:
        r = reports[i]
        user_turn = (
            f"REPORT {i+1} of {n} (from frame: {r['frame_file']}):\n\n{r['report']}\n\n"
            "Commit to your current best account now, before seeing the next report."
        )
        history.append({"role": "user", "content": user_turn})
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
        text = "".join(b.text for b in msg.content if b.type == "text")
        history.append({"role": "assistant", "content": text})
        transcript.append({"step": i + 1, "frame_file": r["frame_file"], "commitment": text})
        print(f"  [synthesis] step {i+1}/{n} -> {len(text)} chars")
        i += 1
        steps_done_this_call += 1

    ckpt["synthesis_history"] = history
    ckpt["synthesis_transcript"] = transcript
    ckpt["synthesis_step_idx"] = i

    if i >= n:
        final_request = (
            "All reports have now been given. Produce a final expectation-trace: "
            "a short summary of where, if anywhere, your committed expectations "
            "were violated, and at which report number you first detected it."
        )
        if variant == "givens":
            final_request += (
                "\n\nAlso produce your FINAL OBJECT REGISTRY: the complete list of "
                "distinct physical objects/entities you concluded were present, "
                "and for each one, a one-line summary of what happened to it "
                "across the video (its full state-change arc, if any)."
            )
        history.append({"role": "user", "content": final_request})
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
        final_text = "".join(b.text for b in msg.content if b.type == "text")
        transcript.append({"step": "final", "frame_file": None, "commitment": final_text})
        ckpt["synthesis_transcript"] = transcript
        ckpt["synthesis_done"] = True
        print(f"  [synthesis] FINAL trace -> {len(final_text)} chars")

    save_ckpt(args.checkpoint, ckpt)
    print(f"Progress: {ckpt['synthesis_step_idx']}/{n} steps. Done: {ckpt['synthesis_done']}")


def stage3(args):
    ckpt = load_ckpt(args.checkpoint)
    if not ckpt.get("synthesis_done"):
        print("Synthesis not finished yet -- run more stage2 calls first."); sys.exit(1)
    frame_paths = sorted(Path(args.frames_dir).glob("*.jpg")) or sorted(Path(args.frames_dir).glob("*.png"))
    client = anthropic.Anthropic()
    content = [b64_image(p) for p in frame_paths]
    content.append({"type": "text", "text": BLOCK_MODEL_PROMPT.format(n=len(frame_paths))})
    msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS * 2,
                                  messages=[{"role": "user", "content": content}])
    text = "".join(b.text for b in msg.content if b.type == "text")
    ckpt["block_model_output"] = text
    save_ckpt(args.checkpoint, ckpt)
    print(f"Stage 3 done. Block-model output -> {len(text)} chars")


def assemble(args):
    ckpt = load_ckpt(args.checkpoint)
    variant = ckpt.get("synthesis_variant", "v1")
    results = {
        "_meta": {
            "experiment": "EXP7 replication run (Condition SC: substrate-controlled)"
                          + (" -- SC-GIVENS variant (proposal, see EXP7_protocol_addendum_v2_givens.md, NOT part of locked v1.0)"
                             if variant == "givens" else ""),
            "protocol": "EXP7_replication_protocol.md v1.0" + (" + Addendum v2 (givens) proposal" if variant == "givens" else ""),
            "synthesis_variant": variant,
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": MODEL,
            "note": "Resumable/checkpointed driver; frame-agent pass parallelized (independent calls only). Synthesis pass remained strictly sequential.",
        },
        "conditions": [{
            "condition": "clip",
            "frame_count": len(ckpt["frame_reports"]),
            "frame_files": [r["frame_file"] for r in ckpt["frame_reports"]],
            "frame_agent_reports": ckpt["frame_reports"],
            "synthesis_transcript": ckpt["synthesis_transcript"],
            "block_model_output": ckpt["block_model_output"],
        }],
    }
    Path(args.out).write_text(json.dumps(results, indent=2))
    print(f"Assembled results written to {args.out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="stage", required=True)

    s1 = sub.add_parser("stage1"); s1.add_argument("--frames-dir", required=True); s1.add_argument("--checkpoint", required=True)
    s2 = sub.add_parser("stage2"); s2.add_argument("--checkpoint", required=True); s2.add_argument("--max-steps", type=int, default=10); s2.add_argument("--variant", choices=["v1", "givens"], default=None, help="Synthesis prompt variant. Default (unset) = v1 (locked protocol prompt, unchanged). 'givens' = proposal in EXP7_protocol_addendum_v2_givens.md, run as separate SC-GIVENS condition, not a replacement.")
    s3 = sub.add_parser("stage3"); s3.add_argument("--frames-dir", required=True); s3.add_argument("--checkpoint", required=True)
    s4 = sub.add_parser("assemble"); s4.add_argument("--checkpoint", required=True); s4.add_argument("--out", required=True); s4.add_argument("--run-id", default="REPL-XXX"); s4.add_argument("--clip-name", default="unknown.mov")

    args = p.parse_args()
    {"stage1": stage1, "stage2": stage2, "stage3": stage3, "assemble": assemble}[args.stage](args)
