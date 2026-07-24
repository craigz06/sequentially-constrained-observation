#!/usr/bin/env python3
"""
extract_frames_manual_roi.py

Extracts every frame in a human-identified frame-number range (the dense
ROI window), plus coarser baseline-fps sampling across the rest of the clip.
Replaces automated motion detection entirely -- built in response to
REPL-011's diagnosed extraction gaps (ROI blindness, fps resolution missing
a fast/small-amplitude event). The human watches the clip, scrubs to find
the frame numbers spanning the event, and tells the script directly.

Usage:
    python3 pipeline/extract_frames_manual_roi.py \
        --video clips/truvia.mov \
        --out-dir frames_out_truvia \
        --dense-frame-start 59 \
        --dense-frame-end 94 \
        --baseline-fps 5

--dense-frame-start / --dense-frame-end are frame NUMBERS (at the clip's
native fps) identified by scrubbing the clip. Every frame in this range is
extracted, full quality, no gaps -- true frame-by-frame coverage.

--baseline-fps controls sampling for the rest of the clip, outside the
dense range. Default 5fps, same as the motion-adaptive script's default.

Output structure (frame naming, manifest.json) matches the other two
extraction scripts in this repo, so results stay comparable across all
three extraction methods.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def ffprobe_info(video_path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    native_fps = float(num) / float(den)
    duration = float(data["format"]["duration"])
    width = int(stream["width"])
    height = int(stream["height"])
    return {
        "native_fps": native_fps,
        "duration": duration,
        "width": width,
        "height": height,
    }


def build_frame_list(
    native_fps: float,
    duration: float,
    dense_start: int,
    dense_end: int,
    baseline_fps: float,
) -> list[tuple[int, str]]:
    """Returns sorted list of (frame_number, kind) tuples, kind in {'dense','baseline'}.
    Dense: every frame number in [dense_start, dense_end], inclusive.
    Baseline: frame numbers at baseline_fps spacing across the whole clip,
    with any that fall inside the dense range dropped (dense supersedes)."""
    total_frames = int(round(duration * native_fps))

    dense_frames = list(range(dense_start, dense_end + 1))
    dense_set = set(dense_frames)

    baseline_frames = []
    if baseline_fps > 0:
        step = native_fps / baseline_fps
        f = 0.0
        while f < total_frames:
            fn = int(round(f))
            if fn not in dense_set:
                baseline_frames.append(fn)
            f += step

    combined = [(f, "dense") for f in dense_frames] + [(f, "baseline") for f in baseline_frames]
    combined.sort(key=lambda x: x[0])
    return combined, total_frames


def extract_frame(video_path: str, native_fps: float, frame_number: int, out_path: Path) -> None:
    timestamp = frame_number / native_fps
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp:.5f}",
        "-i", video_path,
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True, help="Path to source video clip")
    ap.add_argument("--out-dir", required=True, help="Directory to write extracted frames and manifest.json")
    ap.add_argument("--dense-frame-start", type=int, required=True, help="First frame number (native fps) of the dense ROI window")
    ap.add_argument("--dense-frame-end", type=int, required=True, help="Last frame number (native fps) of the dense ROI window, inclusive")
    ap.add_argument("--baseline-fps", type=float, default=5.0, help="Sampling rate OUTSIDE the dense window")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Probing {args.video} ...")
    info = ffprobe_info(args.video)
    print(f"      native_fps={info['native_fps']:.2f}  duration={info['duration']:.2f}s  size={info['width']}x{info['height']}")

    total_frames_est = int(round(info["duration"] * info["native_fps"]))
    if not (0 <= args.dense_frame_start <= args.dense_frame_end <= total_frames_est):
        print(f"ERROR: dense range [{args.dense_frame_start}, {args.dense_frame_end}] "
              f"is outside estimated clip range 0-{total_frames_est}")
        sys.exit(1)

    print(f"[2/3] Building frame list: dense range [{args.dense_frame_start}, {args.dense_frame_end}] "
          f"+ baseline at {args.baseline_fps}fps elsewhere ...")
    frame_list, total_frames = build_frame_list(
        info["native_fps"], info["duration"],
        args.dense_frame_start, args.dense_frame_end,
        args.baseline_fps,
    )
    n_dense = sum(1 for _, k in frame_list if k == "dense")
    n_baseline = sum(1 for _, k in frame_list if k == "baseline")
    print(f"      {n_dense} dense + {n_baseline} baseline = {len(frame_list)} total frames "
          f"(clip has ~{total_frames} frames at native fps)")

    print(f"[3/3] Extracting frames ...")
    manifest_frames = []
    failed_frames = []
    for i, (frame_num, kind) in enumerate(frame_list, start=1):
        fname = f"F{i:03d}.jpg"
        out_path = out_dir / fname
        timestamp = frame_num / info["native_fps"]
        try:
            extract_frame(args.video, info["native_fps"], frame_num, out_path)
        except subprocess.CalledProcessError as e:
            print(f"      WARNING: {fname}  frame#{frame_num}  t={timestamp:.3f}s  [{kind}] "
                  f"FAILED ({e}) -- skipping, continuing with remaining frames")
            failed_frames.append({
                "file": fname,
                "source_frame_number": frame_num,
                "timestamp_s": round(timestamp, 4),
                "kind": kind,
            })
            continue
        manifest_frames.append({
            "file": fname,
            "source_frame_number": frame_num,
            "timestamp_s": round(timestamp, 4),
            "kind": kind,
        })
        print(f"      {fname}  frame#{frame_num}  t={timestamp:.3f}s  [{kind}]")

    if failed_frames:
        print(f"\n      {len(failed_frames)} frame(s) failed extraction and were skipped:")
        for ff in failed_frames:
            print(f"        {ff['file']}  frame#{ff['source_frame_number']}  t={ff['timestamp_s']:.3f}s  [{ff['kind']}]")

    manifest = {
        "source_video": args.video,
        "native_fps": info["native_fps"],
        "duration_s": info["duration"],
        "extraction_method": "manual_roi",
        "dense_frame_range": [args.dense_frame_start, args.dense_frame_end],
        "baseline_fps": args.baseline_fps,
        "note": (
            "Dense frame range was identified by a human scrubbing the source "
            "clip frame-by-frame, not by automated motion detection. Built in "
            "response to REPL-011's diagnosed extraction gaps (ROI blindness, "
            "fps resolution missing a fast/small-amplitude event)."
        ),
        "frames": manifest_frames,
        "failed_frames": failed_frames,
    }
    with open(out_dir / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(manifest_frames)}/{len(frame_list)} frames extracted to {out_dir}/, manifest.json written.")


if __name__ == "__main__":
    main()
