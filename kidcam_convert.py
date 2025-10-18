#!/usr/bin/env python3
"""
KidCam HEVC Converter (Auto HW Detect)
--------------------------------------
Converts kids' camera clips to Apple-friendly HEVC (.mp4) with:
- Auto-detect of Apple Silicon hardware encoder (hevc_videotoolbox)
- Fallback to software x265 when HW is unavailable
- Clear logging of which path was used
- Creation time preserved so Photos/iCloud sort correctly

Usage:
  python3 kidcam_convert.py [inputs ...] [-o OUTPUT] [--recursive] [--hw | --sw] [--verbose]

Inputs:
  Zero or more input directories or files. If none are provided, defaults to ~/Movies/KidCam_Inbox

Options:
  -o, --output OUTPUT  Output directory (used only when exactly one input is given). If omitted, defaults to <input>-out per input.
  --recursive          Recurse into subfolders
  --hw | --sw          Force encoder (otherwise auto-detect)
  --verbose            Show ffmpeg info logs (proves HW path inside ffmpeg logs)
"""

import argparse
import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path

os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

# ---------------------------
# Detection helpers
# ---------------------------

def ffmpeg_has_encoder(name: str) -> bool:
    """Return True if ffmpeg lists the given encoder."""
    try:
        out = subprocess.check_output(
            ["ffmpeg", "-hide_banner", "-v", "0", "-encoders"],
            stderr=subprocess.STDOUT,
            text=True,
        )
        return name in out
    except Exception:
        return False

def prefer_hardware_encoder() -> bool:
    """Heuristic: use HW if we're on macOS and ffmpeg has hevc_videotoolbox."""
    if platform.system() != "Darwin":
        return False
    return ffmpeg_has_encoder("hevc_videotoolbox")

def run_ffprobe(src: Path) -> dict:
    """Run ffprobe to get stream info as dict."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(src)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        return {}

def analyze_source(src: Path) -> dict:
    """Analyze source video/audio streams and return key attributes."""
    info = run_ffprobe(src)
    video_stream = None
    audio_stream = None
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    video_info = {
        "codec": video_stream.get("codec_name") if video_stream else None,
        "width": int(video_stream.get("width")) if video_stream and video_stream.get("width") else None,
        "height": int(video_stream.get("height")) if video_stream and video_stream.get("height") else None,
        "r_frame_rate": video_stream.get("r_frame_rate") if video_stream else None,
    }

    audio_info = {
        "codec": audio_stream.get("codec_name") if audio_stream else None,
        "channels": int(audio_stream.get("channels")) if audio_stream and audio_stream.get("channels") else None,
        "sample_rate": int(audio_stream.get("sample_rate")) if audio_stream and audio_stream.get("sample_rate") else None,
    }

    return {"video": video_info, "audio": audio_info}

# ---------------------------
# Conversion
# ---------------------------

SUPPORTED_EXTS = {".avi", ".mov", ".mp4", ".mjpg", ".mjpeg", ".AVI", ".MOV", ".MP4", ".MJPG", ".MJPEG"}

def convert_file(src: Path, outdir: Path, use_hw: bool, verbose: bool) -> None:
    bn = src.stem
    out_file = outdir / f"{bn}.mp4"
    if out_file.exists():
        print(f"⏩ Skip (exists): {out_file.name}")
        return

    # Preserve original mod time in metadata
    mtime_iso = datetime.fromtimestamp(src.stat().st_mtime).astimezone().isoformat()

    # Analyze source media info
    media_info = analyze_source(src)
    video = media_info.get("video", {})
    audio = media_info.get("audio", {})

    print(f"🔍 Detected video codec: {video.get('codec')}, resolution: {video.get('width')}x{video.get('height')}, framerate: {video.get('r_frame_rate')}")
    print(f"🔍 Detected audio codec: {audio.get('codec')}, channels: {audio.get('channels')}, sample rate: {audio.get('sample_rate')}")

    loglevel = "info" if verbose else "error"

    # Decide if remux or re-encode video
    # Remux if codec is already hevc (h265) and container is mp4/mov
    remux_video = False
    if video.get("codec") in ("hevc", "hevc_nvenc", "hevc_amf", "hevc_videotoolbox") and src.suffix.lower() in (".mp4", ".mov"):
        remux_video = True

    # Decide if remux or re-encode audio
    # Remux audio if AAC mono 16kHz, else re-encode audio to AAC mono 16kHz
    remux_audio = False
    if audio.get("codec") == "aac" and audio.get("channels") == 1 and audio.get("sample_rate") == 16000:
        remux_audio = True

    if remux_video and remux_audio:
        encoder_label = "remux (copy)"
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", loglevel, "-y",
            "-i", str(src),
            "-map", "0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-movflags", "+faststart",
            "-metadata", f"creation_time={mtime_iso}",
            "-metadata", f"comment=KidCam HEVC remux (copy)",
            str(out_file)
        ]
    else:
        if use_hw:
            encoder_label = "hevc_videotoolbox (HW)"
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", loglevel, "-y",
                "-i", str(src),
                "-map", "0",
                # Hardware encoder (very fast; slightly larger files vs libx265 at same visual quality)
                "-c:v", "hevc_videotoolbox",
                "-b:v", "0",               # enable quality-based mode
                "-q:v", "60",              # 45–70 typical; lower is higher quality. 60 ≈ RF ~20 feel.
                "-pix_fmt", "yuv420p",
                "-tag:v", "hvc1",          # important for Apple apps
                "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-ar", "16000",
                "-movflags", "+faststart",
                "-metadata", f"creation_time={mtime_iso}",
                "-metadata", f"comment=KidCam HEVC via hevc_videotoolbox (hardware)",
                str(out_file)
            ]
        else:
            encoder_label = "libx265 (SW)"
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", loglevel, "-y",
                "-i", str(src),
                "-map", "0",
                # Software x265 (slower; best compression efficiency)
                "-c:v", "libx265", "-crf", "20", "-preset", "slow", "-pix_fmt", "yuv420p",
                "-x265-params", "profile=main:level=4.1:high-tier=1:repeat-headers=1",
                "-tag:v", "hvc1",
                "-c:a", "aac", "-b:a", "128k", "-ac", "1", "-ar", "16000",
                "-movflags", "+faststart",
                "-metadata", f"creation_time={mtime_iso}",
                "-metadata", f"comment=KidCam HEVC via libx265 (software)",
                str(out_file)
            ]

    print(f"🎞  Converting [{encoder_label}]: {src.name} → {out_file.name}")
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Done: {out_file.name}\n")
    except subprocess.CalledProcessError:
        print(f"❌ Failed: {src.name}\n")

def main():
    ap = argparse.ArgumentParser(add_help=True)
    # Accept zero or more inputs so Shortcuts can pass multiple paths; default if none provided.
    ap.add_argument("inputs", nargs="*", help="Input directories or files. If empty, defaults to ~/Movies/KidCam_Inbox")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--hw", action="store_true", help="Force hardware encoder (hevc_videotoolbox)")
    g.add_argument("--sw", action="store_true", help="Force software encoder (libx265)")
    ap.add_argument("-o", "--output", dest="output", type=str, help="Output directory (used only when exactly one input is given). If omitted, defaults to <input>-out.")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders")
    ap.add_argument("--verbose", action="store_true", help="Verbose ffmpeg logs")
    args = ap.parse_args()

    # Resolve inputs; default to ~/Movies/KidCam_Inbox if none provided
    input_list = args.inputs if args.inputs else [str(Path.home() / "Movies" / "KidCam_Inbox")]
    inputs: list[Path] = [Path(p).expanduser().resolve() for p in input_list]

    # If exactly one input and an explicit output was provided, use it; otherwise use "<input>-out"
    explicit_outdir: Path | None = Path(args.output).expanduser().resolve() if (args.output and len(inputs) == 1) else None

    # Decide encoder
    if args.hw:
        use_hw = True
        reason = "forced by --hw"
    elif args.sw:
        use_hw = False
        reason = "forced by --sw"
    else:
        use_hw = prefer_hardware_encoder()
        reason = "auto-detected" if use_hw else "auto-detected (HW unavailable)"

    print("—— KidCam HEVC Converter —————————————————————")
    print(f"Inputs:       {', '.join(str(p) for p in inputs)}")
    if explicit_outdir:
        print(f"Output:       {explicit_outdir}  (explicit)")
    else:
        print(f"Output:       <input>-out  (auto per input)")
    print(f"Chosen mode:  {'Hardware (hevc_videotoolbox)' if use_hw else 'Software (libx265)'} — {reason}")
    if use_hw:
        print("Indicator:    You should also see 'videotoolbox' lines if running with --verbose.")
    print("———————————————————————————————————————————————\n")

    total = 0
    for inbox in inputs:
        if not inbox.exists():
            print(f"Missing input: {inbox}")
            continue

        # Determine output directory for this input
        outdir = explicit_outdir if explicit_outdir else Path(str(inbox) + "-out")
        outdir.mkdir(parents=True, exist_ok=True)

        # Gather work list
        files: list[Path] = []
        if inbox.is_file():
            if inbox.suffix in SUPPORTED_EXTS:
                files = [inbox]
        else:
            if args.recursive:
                for p in inbox.rglob("*"):
                    if p.is_file() and (p.suffix in SUPPORTED_EXTS) and not (outdir in p.parents):
                        files.append(p)
            else:
                for p in inbox.iterdir():
                    if p.is_file() and (p.suffix in SUPPORTED_EXTS) and not (outdir in p.parents):
                        files.append(p)

        if not files:
            print(f"No supported video files found under: {inbox}")
            continue

        print(f"Found {len(files)} file(s) in {inbox}. Converting to {outdir}...\n")
        for f in files:
            convert_file(f, outdir, use_hw, args.verbose)
            total += 1

    if total == 0:
        print("No files converted. Supported extensions:", ", ".join(sorted(SUPPORTED_EXTS)))
    else:
        print(f"✅ All conversions complete.")

if __name__ == "__main__":
    main()