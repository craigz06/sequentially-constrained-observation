#!/usr/bin/env python3
"""
QUICK PROTOTYPE -- not part of the tracked pipeline, not committed.
Tests "Janus" (backward-facing only): at synthesis step i, the model gets
the frame-agent's text report for frame i AND the actual image for frame i,
attached to the growing conversation. Because the full history is resent
each call (same mechanism as the existing stage2), every prior frame's
image remains visible automatically -- true cumulative backward visual
context, zero access to anything ahead. If this works, we write it up
properly as Addendum v3 and wire it into run_exp7_resumable.py as a real
--variant option. Until then this is scratch.
"""
import json, base64
from pathlib import Path
import anthropic
import os

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
FRAMES_DIR = Path("frames_out_4794")
CKPT_IN = Path("runs/REPL-006_checkpoint.json")
CKPT_OUT = Path("runs/JANUS_TEST_checkpoint.json")

JANUS_INTRO = (
    "You are the synthesis agent in a sequential-observation experiment. "
    "You will receive a series of frame-agent text reports, ONE AT A TIME, "
    "in true temporal order. Each report was written by an agent that saw "
    "only that single frame and nothing else.\n\n"
    "Unlike that frame-agent, YOU will also be shown the actual image of "
    "each frame, alongside its text report, as it is revealed to you. "
    "Every image you have already been shown remains visible to you as "
    "the conversation continues -- you have full visual memory of "
    "everything already revealed. You do NOT have access to any frame "
    "that has not yet been given to you. When a new report or image "
    "seems to introduce something unfamiliar, compare it directly against "
    "the actual prior images you have already seen -- not just against "
    "the text descriptions -- before concluding it is a new object rather "
    "than something already seen in a different pose, angle, or state.\n\n"
    "After each report+image, before you are given the next one, you must "
    "COMMIT to your current best account of what is happening and what "
    "you expect next. If a later report contradicts your prior commitment, "
    "say so explicitly and name the exact point where your expectation "
    "was violated -- do not quietly revise your earlier commitment as if "
    "you'd always known."
)

def b64_image(path: Path) -> dict:
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}}

def main():
    ckpt_in = json.loads(CKPT_IN.read_text())
    reports = ckpt_in["frame_reports"]
    n = len(reports)

    client = anthropic.Anthropic()

    if CKPT_OUT.exists():
        state = json.loads(CKPT_OUT.read_text())
        history = state["history"]
        transcript = state["transcript"]
        start_i = state["next_i"]
        print(f"Resuming from step {start_i+1}")
    else:
        history = [{"role": "user", "content": JANUS_INTRO},
                   {"role": "assistant", "content": "Understood. Send me the first report and its image."}]
        transcript = []
        start_i = 0

    for i in range(start_i, n):
        r = reports[i]
        img_path = FRAMES_DIR / r["frame_file"]
        text = (
            f"REPORT {i+1} of {n} (from frame: {r['frame_file']}):\n\n{r['report']}\n\n"
            "Here is the actual image for this frame. Commit to your current "
            "best account now, before seeing the next report."
        )
        user_turn = {"role": "user", "content": [b64_image(img_path), {"type": "text", "text": text}]}
        history.append(user_turn)
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
        out_text = "".join(b.text for b in msg.content if b.type == "text")
        history.append({"role": "assistant", "content": out_text})
        transcript.append({"step": i + 1, "frame_file": r["frame_file"], "commitment": out_text})
        print(f"  [janus] step {i+1}/{n} -> {len(out_text)} chars")
        CKPT_OUT.write_text(json.dumps({"history": history, "transcript": transcript, "next_i": i + 1}, indent=2))

    if not any(t.get("step") == "final" for t in transcript):
        final_request = (
            "All reports have now been given. Produce a final expectation-trace: "
            "a short summary of where, if anywhere, your committed expectations "
            "were violated, and at which report number you first detected it. "
            "Also state plainly, in one sentence, what you now believe happened "
            "to each distinct object you tracked across the video."
        )
        history.append({"role": "user", "content": final_request})
        msg = client.messages.create(model=MODEL, max_tokens=MAX_TOKENS, messages=history)
        final_text = "".join(b.text for b in msg.content if b.type == "text")
        transcript.append({"step": "final", "frame_file": None, "commitment": final_text})
        print(f"  [janus] FINAL -> {len(final_text)} chars")
        CKPT_OUT.write_text(json.dumps({"history": history, "transcript": transcript, "next_i": n}, indent=2))

    print(f"Saved to {CKPT_OUT}")

if __name__ == "__main__":
    main()
