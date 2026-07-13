#!/usr/bin/env python3
"""
Motion-adaptive frame extraction for EXP7.

Replaces manual "notice the missed frame, go back and fix it" with an
automatic first pass: compute a motion-diff profile across the whole
clip, flag high-motion windows (same sigma-threshold pattern as DCI's
D7 motion trigger), and sample DENSELY inside those windows while
staying coarse everywhere else. This is what REPL-003b did by hand
after the fact -- this script does it by default, before any model
call, so a fast discrete event (a strike, a snap) doesn't fall between
two sampled frames the way it did in REPL-003.

WHAT THIS DOES NOT DO
----------------------
Does not call any model. Pure ffmpeg + numpy frame analysis. Output is
a directory of correctly time-ordered JPEG frames plus a manifest.json
describing what was sampled where and why -- feed the frame directory
straight into run_exp7_resumable.py afterward.

USAGE
-----
    pip install numpy pillow --break-system-packages
    python3 extract_frames_motion_adaptive.py --video clip.mov --out-dir frames_out

    # tune if needed:
    python3 extract_frames_motion_adaptive.py --video clip.mov --out-dir frames_out \\
        --baseline-fps 5 --dense-fps 20 --sigma 3.0 --pad-seconds 0.15
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def ffprobe_info(video_path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,width,height",
        "-show_entries", "format=duration",
        "-of", "json", video_path,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    stream = d["stream" if "stream" in d else "streams"][0] if "streams" in d else d["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    native_fps = float(num) / float(den)
    duration = float(d["format"]["duration"])
    return {"native_fps": native_fps, "duration": duration,
            "width": stream["width"], "height": stream["height"]}


def extract_analysis_frames(video_path: str, tmp_dir: Path, analysis_fps: float) -> list[float]:
    """Cheap, small, grayscale frames purely for motion scoring. Returns list of timestamps."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(tmp_dir / "a%05d.png")
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"fps={analysis_fps},scale=320:-1,format=gray",
        "-y", pattern,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    frames = sorted(tmp_dir.glob("a*.png"))
    timestamps = [i / analysis_fps for i in range(len(frames))]
    return frames, timestamps


def compute_motion_scores(frame_paths: list[Path]) -> np.ndarray:
    """Mean absolute pixel difference between consecutive frames, normalized 0-1."""
    arrs = [np.asarray(Image.open(p), dtype=np.float32) for p in frame_paths]
    scores = [0.0]  # first frame has no prior frame to diff against
    for i in range(1, len(arrs)):
        diff = np.abs(arrs[i] - arrs[i - 1]).mean() / 255.0
        scores.append(diff)
    return np.array(scores)


def find_motion_windows(scores: np.ndarray, timestamps: list[float], sigma: float, pad_s: float, min_gap_s: float) -> list[tuple]:
    """Threshold = mean + sigma*std, same pattern as DCI's D7 motion trigger.
    Returns merged, padded (start, end) windows in seconds."""
    mean, std = scores.mean(), scores.std()
    threshold = mean + sigma * std
    flagged = [timestamps[i] for i, s in enumerate(scores) if s > threshold]

    if not flagged:
        return []

    windows = []
    start = flagged[0]
    prev = flagged[0]
    for t in flagged[1:]:
        if t - prev > min_gap_s:
            windows.append((max(0, start - pad_s), prev + pad_s))
            start = t
        prev = t
    windows.append((max(0, start - pad_s), prev + pad_s))
    return windows, threshold, mean, std


def extract_frame_at(video_path: str, t: float, out_path: Path):
    cmd = [
        "ffmpeg", "-ss", f"{t:.4f}", "-i", video_path,
        "-vf", "scale=1024:-1,format=yuv420p",
        "-frames:v", "1", "-q:v", "3",
        "-y", str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--baseline-fps", type=float, default=5.0, help="Sampling rate OUTSIDE motion windows")
    ap.add_argument("--dense-fps", type=float, default=20.0, help="Sampling rate INSIDE motion windows")
    ap.add_argument("--analysis-fps", type=float, default=15.0, help="Rate for the cheap motion-scoring pass")
    ap.add_argument("--sigma", type=float, default=3.0, help="Motion threshold: mean + sigma*std (matches DCI D7)")
    ap.add_argument("--pad-seconds", type=float, default=0.15, help="Padding added around each detected motion window")
    ap.add_argument("--min-gap-seconds", type=float, default=0.3, help="Merge flagged points closer than this into one window")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    tmp_dir = out_dir / "_analysis_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] Probing {args.video} ...")
    info = ffprobe_info(args.video)
    print(f"      native_fps={info['native_fps']:.1f}  duration={info['duration']:.2f}s  "
          f"size={info['width']}x{info['height']}")

    print(f"[2/5] Extracting analysis frames at {args.analysis_fps}fps ...")
    frame_paths, timestamps = extract_analysis_frames(args.video, tmp_dir, args.analysis_fps)
    print(f"      {len(frame_paths)} analysis frames")

    print(f"[3/5] Computing motion scores ...")
    scores = compute_motion_scores(frame_paths)
    result = find_motion_windows(scores, timestamps, args.sigma, args.pad_seconds, args.min_gap_seconds)
    if not result:
        windows, threshold, mean, std = [], None, scores.mean(), scores.std()
        print(f"      No motion above threshold detected (mean={mean:.4f}, std={std:.4f}). "
              f"Falling back to uniform baseline_fps sampling for the whole clip.")
    else:
        windows, threshold, mean, std = result
        print(f"      mean={mean:.4f} std={std:.4f} threshold={threshold:.4f} (mean + {args.sigma}*std)")
        print(f"      {len(windows)} motion window(s) detected:")
        for w in windows:
            print(f"        t={w[0]:.3f}s -> t={w[1]:.3f}s  (duration {w[1]-w[0]:.3f}s)")

    print(f"[4/5] Building merged sample timestamp list ...")
    duration = info["duration"]

    def in_any_window(t):
        return any(w[0] <= t <= w[1] for w in windows)

    baseline_times = set(np.arange(0, duration, 1.0 / args.baseline_fps).round(4))
    dense_times = set()
    for (ws, we) in windows:
        n = max(2, int((we - ws) * args.dense_fps))
        dense_times.update(np.linspace(ws, we, n).round(4))

    # drop baseline samples that fall inside a motion window -- dense sampling supersedes them there
    baseline_times = {t for t in baseline_times if not in_any_window(t)}
    all_times = sorted(baseline_times | dense_times)
    all_times = [t for t in all_times if t <= duration]
    print(f"      {len(baseline_times)} baseline + {len(dense_times)} dense = {len(all_times)} total frames")

    print(f"[5/5] Extracting final frames at full quality ...")
    manifest = {"video": args.video, "native_fps": info["native_fps"], "duration": duration,
                "sigma": args.sigma, "threshold": threshold, "motion_windows": windows,
                "baseline_fps": args.baseline_fps, "dense_fps": args.dense_fps, "frames": []}

    for idx, t in enumerate(all_times, start=1):
        fname = f"F{idx:03d}.jpg"
        out_path = out_dir / fname
        extract_frame_at(args.video, t, out_path)
        kind = "dense" if in_any_window(t) else "baseline"
        manifest["frames"].append({"file": fname, "timestamp_s": round(t, 4), "kind": kind})
        print(f"      {fname}  t={t:.3f}s  [{kind}]")

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    for p in tmp_dir.glob("a*.png"):
        p.unlink()
    tmp_dir.rmdir()

    print(f"\nDone. {len(all_times)} frames in {out_dir}/, manifest.json written.")
    if windows:
        print(f"Motion windows were sampled at {args.dense_fps}fps; everywhere else at {args.baseline_fps}fps.")


if __name__ == "__main__":
    main()
