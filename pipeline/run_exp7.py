#!/usr/bin/env python3
"""
EXP7 -- Replication Runner for H5 (Condition SC: Substrate-Controlled)
(see EXP7_replication_protocol.md v1.0 and sco_research_memory_v3_1.json)

WHY THIS SCRIPT NOW MATTERS MORE THAN IT DID AT FIRST DRAFT
-------------------------------------------------------------
Run 1 (2026-07-10, logged as REPL-000) ran the sequential arm on ChatGPT
and the spacetime arm on Gemini - a real result, but Condition CS
(Cross-Substrate), confounded by architecture. This script runs BOTH
arms on the SAME model (whatever ANTHROPIC_API_KEY points to), which is
exactly Condition SC from the replication protocol - the version that
actually isolates delivery-mode (sequential vs. all-at-once) as the only
variable. This is the run that can confirm or kill Finding B cleanly.

WHAT THIS SCRIPT ACTUALLY DOES
-------------------------------
For a single clip's extracted frame set, it:

  1. Runs N independent FRAME-AGENT calls, one per frame. Each call is a
     completely fresh API request with NO conversation history and NO
     other frames in context - only that single image. This is a real
     information barrier, not a role the model plays inside one context:
     each frame-agent is architecturally incapable of having seen any
     other frame, because no other frame is ever sent to it.

  2. Runs a SYNTHESIS AGENT that receives the frame-agent reports ONE AT
     A TIME, in temporal order, inside a single growing conversation. At
     each step it is asked to commit to a current best account BEFORE
     the next report is revealed. This preserves sequential discipline
     at the synthesis layer too (the joint D5 flags as most likely to
     fail if built carelessly).

  3. Runs a BLOCK-MODEL (spacetime) comparison call: a single fresh
     request with ALL frames attached at once, asked to produce the same
     kind of output. Same model as step 1-2 - this is what makes the run
     Condition SC rather than Condition CS.

  4. Saves full transcripts (every prompt and every response) to JSON,
     so the run is itself auditable - not just the conclusion, but the
     actual exchange that produced it.

  5. Prints a pre-filled skeleton matching exp7_run_log_template.json,
     so results can be pasted into the accumulating exp7_run_log.json
     without re-deriving the structure by hand each time.

WHAT THIS SCRIPT DOES NOT DO
-----------------------------
It does not score event_accuracy or detail_accuracy against ground
truth. Per the replication protocol Section 5 (blinding), a human must
write the ground-truth sentence BEFORE reading either transcript, then
score both arms against it. Automating that judgment inside this script
would defeat the blinding procedure the protocol exists to enforce.

SETUP
-----
    pip install anthropic --break-system-packages
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 run_exp7.py --frames-dir /path/to/exp7_frames

Expects a directory structure like:
    exp7_frames/
        authentic/  F1_before.png F2_entering.png ... F7_rest.png
        violated/   F1_before.png F2_entering.png ... F7_rest.png

Frame files are read in sorted filename order — name them so sorted
order equals temporal order (F1_, F2_, ... as already done for you).
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Missing dependency. Run: pip install anthropic --break-system-packages")
    sys.exit(1)

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


def run_frame_agents(client: anthropic.Anthropic, frame_paths: list[Path]) -> list[dict]:
    """One fresh, isolated call per frame. No shared context between calls."""
    reports = []
    for path in frame_paths:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{
                "role": "user",
                "content": [b64_image(path), {"type": "text", "text": FRAME_AGENT_PROMPT}],
            }],
        )
        text = "".join(block.text for block in msg.content if block.type == "text")
        reports.append({"frame_file": path.name, "report": text})
        print(f"  [frame-agent] {path.name} -> {len(text)} chars")
        time.sleep(0.3)
    return reports


def run_synthesis_agent(client: anthropic.Anthropic, reports: list[dict]) -> list[dict]:
    """Single growing conversation, but reports are revealed one at a time,
    with a commitment requested after each before the next is shown."""
    history = [{"role": "user", "content": SYNTHESIS_INTRO}]
    history.append({"role": "assistant", "content": "Understood. Send me the first report."})

    transcript = []
    for i, r in enumerate(reports, start=1):
        user_turn = (
            f"REPORT {i} of {len(reports)} (from frame: {r['frame_file']}):\n\n"
            f"{r['report']}\n\n"
            "Commit to your current best account now, before seeing the next report."
        )
        history.append({"role": "user", "content": user_turn})
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
        text = "".join(block.text for block in msg.content if block.type == "text")
        history.append({"role": "assistant", "content": text})
        transcript.append({"step": i, "frame_file": r["frame_file"], "commitment": text})
        print(f"  [synthesis] step {i}/{len(reports)} -> {len(text)} chars")
        time.sleep(0.3)

    history.append({
        "role": "user",
        "content": (
            "All reports have now been given. Produce a final expectation-trace: "
            "a short summary of where, if anywhere, your committed expectations "
            "were violated, and at which report number you first detected it."
        ),
    })
    msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
    final_text = "".join(block.text for block in msg.content if block.type == "text")
    transcript.append({"step": "final", "frame_file": None, "commitment": final_text})
    print(f"  [synthesis] final trace -> {len(final_text)} chars")
    return transcript


def run_block_model(client: anthropic.Anthropic, frame_paths: list[Path]) -> str:
    """Single fresh call, all frames attached at once."""
    content = []
    for path in frame_paths:
        content.append(b64_image(path))
    content.append({"type": "text", "text": BLOCK_MODEL_PROMPT.format(n=len(frame_paths))})
    msg = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS * 2,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    print(f"  [block-model] -> {len(text)} chars")
    return text


def run_condition(client: anthropic.Anthropic, label: str, frames_dir: Path) -> dict:
    frame_paths = sorted(frames_dir.glob("*.png")) or sorted(frames_dir.glob("*.jpg"))
    if not frame_paths:
        raise FileNotFoundError(f"No frames found in {frames_dir}")

    print(f"\n=== Condition: {label} ({len(frame_paths)} frames) ===")

    print("-- Frame-agent pass --")
    frame_reports = run_frame_agents(client, frame_paths)

    print("-- Synthesis-agent pass --")
    synthesis_transcript = run_synthesis_agent(client, frame_reports)

    print("-- Block-model pass --")
    block_output = run_block_model(client, frame_paths)

    return {
        "condition": label,
        "frame_count": len(frame_paths),
        "frame_files": [p.name for p in frame_paths],
        "frame_agent_reports": frame_reports,
        "synthesis_transcript": synthesis_transcript,
        "block_model_output": block_output,
    }


def print_run_log_skeleton(run_id: str, clip_file: str, cond_result: dict) -> None:
    """Print a pre-filled skeleton matching exp7_run_log_template.json fields,
    so results can be pasted into exp7_run_log.json without re-deriving the
    structure. Scoring fields are left as TODO - per the replication protocol
    Section 5, a human must write ground_truth_event and ground_truth_detail
    BEFORE reading the transcripts below, then fill in event_accuracy /
    detail_accuracy against that pre-written sentence."""
    skeleton = {
        "run_id": run_id,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "condition": "SC",
        "clip_file": clip_file,
        "clip_duration_s": "TODO",
        "clip_structure_notes": "TODO",
        "ground_truth_event": "TODO -- write this BEFORE reading the transcripts below",
        "ground_truth_detail": "TODO -- write this BEFORE reading the transcripts below",
        "sequential_arm": {
            "substrate": MODEL,
            "delivery_method": "stateless frames one at a time via API, synthesis agent one report at a time",
            "num_frames": cond_result["frame_count"],
            "final_trace_summary": "SEE synthesis_transcript in the full results JSON -- copy final step's commitment text here",
            "event_accuracy": "TODO -- correct | partial | confabulated",
            "detail_accuracy": "TODO -- correct | not_mentioned | confabulated",
            "confidence_at_violation_point": "TODO -- read from synthesis_transcript",
        },
        "spacetime_arm": {
            "substrate": MODEL,
            "delivery_method": "all frames attached at once via API, single call",
            "final_trace_summary": "SEE block_model_output in the full results JSON",
            "event_accuracy": "TODO -- correct | partial | confabulated",
            "detail_accuracy": "TODO -- correct | not_mentioned | confabulated",
        },
        "scorer": "TODO",
        "blinded": "TODO -- true only if ground_truth was written before reading transcripts",
        "second_scorer": None,
        "second_scorer_agreement": None,
        "deviations_from_protocol": "none, or describe",
        "notes": "",
    }
    print("\n" + "=" * 70)
    print("RUN LOG SKELETON -- paste into exp7_run_log.json after scoring:")
    print("=" * 70)
    print(json.dumps(skeleton, indent=2))
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run EXP7 (Condition SC: same model, both arms) on either a "
                     "single clip's frames, or a legacy authentic/violated pair."
    )
    parser.add_argument(
        "--frames-dir", required=True,
        help="For single-clip mode: a directory of frame images directly. "
             "For legacy paired mode: a directory containing authentic/ and violated/ subfolders."
    )
    parser.add_argument(
        "--mode", choices=["single", "paired"], default="single",
        help="single = one clip, one ground-truth event (replication protocol default). "
             "paired = legacy authentic/violated comparison (original EXP7 design)."
    )
    parser.add_argument("--run-id", default="REPL-XXX", help="Run ID for the log skeleton, e.g. REPL-001")
    parser.add_argument("--clip-name", default="unknown.mov", help="Source clip filename, for the log skeleton")
    parser.add_argument("--out", default="exp7_results.json", help="Output JSON path for full transcripts")
    args = parser.parse_args()

    frames_root = Path(args.frames_dir)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY in your environment first.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    results = {
        "_meta": {
            "experiment": "EXP7 replication run (Condition SC: substrate-controlled)",
            "protocol": "EXP7_replication_protocol.md v1.0",
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": MODEL,
            "note": (
                "Both the sequential arm and the spacetime arm in this run use the "
                "SAME model, satisfying Condition SC. This is distinct from REPL-000 "
                "(run 1, 2026-07-10), which was Condition CS (ChatGPT sequential vs. "
                "Gemini spacetime) and is confounded by architecture."
            ),
        },
        "conditions": [],
    }

    if args.mode == "single":
        if not frames_root.is_dir():
            print(f"ERROR: {frames_root} not found.")
            sys.exit(1)
        cond_result = run_condition(client, "clip", frames_root)
        results["conditions"].append(cond_result)
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"\nDone. Full transcripts written to {args.out}")
        print_run_log_skeleton(args.run_id, args.clip_name, cond_result)

    else:  # paired, legacy mode
        for label in ["authentic", "violated"]:
            cond_dir = frames_root / label
            if not cond_dir.is_dir():
                print(f"WARNING: {cond_dir} not found, skipping.")
                continue
            results["conditions"].append(run_condition(client, label, cond_dir))
        Path(args.out).write_text(json.dumps(results, indent=2))
        print(f"\nDone. Full transcripts written to {args.out}")

    print("\nRead the synthesis-agent final trace and the block-model output side by")
    print("side. Per the replication protocol Section 5: write ground_truth_event and")
    print("ground_truth_detail BEFORE reading either transcript, then score against")
    print("that pre-written sentence. This script deliberately does not score for you.")


if __name__ == "__main__":
    main()
