#!/usr/bin/env python3
"""
YouTube Playlist Downloader — yt-dlp frontend

Usage:
  python yt_download.py              interactive mode
  yt                                 same (after install)
  yt 1-4                             items 1-4, rest from saved config
  yt 1-4 a                           items 1-4, audio (m4a)
  yt 1 v https://youtu.be/...        item 1, video, given URL
  yt a https://youtu.be/...          audio, given URL

Arguments (any order):
  RANGE    1-4 or just 3
  v/a      video (mp4) or audio (m4a)
  URL      youtube.com / youtu.be link
"""

import subprocess
import sys
import os
import re
import json
import shutil

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "yt_dl_config.json")

DEFAULT_CONFIG = {
    "url":         "",
    "range":       "1",
    "output_dir":  os.path.join(os.path.expanduser("~"), "Downloads", "yt_downloads"),
    "auth":        "2",    # Firefox
    "mode":        "1",    # video
    "auto_update": True,
}

AUTH = {
    "1": ("chrome",  "Chrome  cookies  (private playlists, best quality)"),
    "2": ("firefox", "Firefox cookies  (private playlists, best quality)"),
    "3": ("edge",    "Edge    cookies  (private playlists, best quality)"),
    "4": (None,      "No auth          (public content, typically 1080p)"),
}

MODE = {
    "1": "video",
    "2": "audio",
}


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ─── CLI arg parser ───────────────────────────────────────────────────────────

def parse_cli(argv: list[str]) -> dict | None:
    """
    Parses positional args in any order.
    Returns dict of recognised values, or None if --help was requested.
    Empty dict means 'no args' → interactive mode.
    """
    if not argv:
        return {}

    if argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    result = {}
    for arg in argv:
        a = arg.strip()
        if a.lower() in ("v", "video"):
            result["mode"] = "1"
        elif a.lower() in ("a", "audio"):
            result["mode"] = "2"
        elif re.match(r"^\d+(-\d+)?$", a):
            result["range"] = a
        elif a.startswith(("http://", "https://")):
            result["url"] = a
        else:
            print(f"  Unknown argument: {a!r}  (ignored)")
    return result


# ─── Local ffmpeg ─────────────────────────────────────────────────────────────

def setup_local_ffmpeg():
    """
    If ./ffmpeg/ffmpeg[.exe] exists next to this script, prepend that
    directory to PATH so yt-dlp subprocess picks it up automatically.
    """
    ffmpeg_dir = os.path.join(SCRIPT_DIR, "ffmpeg")
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if os.path.isfile(os.path.join(ffmpeg_dir, exe)):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
        return True
    return False


# ─── Dependencies ─────────────────────────────────────────────────────────────

def _pip(*args):
    subprocess.check_call(
        [sys.executable, "-m", "pip", *args],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

def remove_oauth2_plugin():
    """Remove yt-dlp-youtube-oauth2 if installed — it globally patches all
    YouTube extractors and requires GVS PO tokens, breaking downloads."""
    try:
        import yt_dlp_youtube_oauth2  # noqa: F401
    except ImportError:
        return
    print("  Removing OAuth2 plugin...", end=" ", flush=True)
    try:
        _pip("uninstall", "yt-dlp-youtube-oauth2", "-y")
        print("✓")
    except subprocess.CalledProcessError:
        print("✗  run:  pip uninstall yt-dlp-youtube-oauth2 -y")

def ensure_deps():
    try:
        import yt_dlp  # noqa: F401
        print("  Updating yt-dlp...", end=" ", flush=True)
    except ImportError:
        print("  Installing yt-dlp...", end=" ", flush=True)
    _pip("install", "--upgrade", "yt-dlp[default]")
    print("✓")

    try:
        import yt_dlp_ejs  # noqa: F401
        print("  Updating yt-dlp-ejs...", end=" ", flush=True)
    except ImportError:
        print("  Installing yt-dlp-ejs...", end=" ", flush=True)
    try:
        _pip("install", "--upgrade", "yt-dlp-ejs")
        print("✓")
    except subprocess.CalledProcessError:
        print("✗  (pip install yt-dlp-ejs)")

def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        src = "(./ffmpeg/)" if os.path.isfile(
            os.path.join(SCRIPT_DIR, "ffmpeg",
                         "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
        ) else "(system)"
        print(f"✓ ffmpeg {src}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠  ffmpeg not found  →  winget install Gyan.FFmpeg  or add ffmpeg.exe to ./ffmpeg/")
        return False

def check_runtime() -> tuple[str, str]:
    """Prefer Deno (yt-dlp default, no flag needed). Fall back to Node.js."""
    try:
        r   = subprocess.run(["deno", "--version"], capture_output=True, check=True)
        ver = r.stdout.decode().split("\n")[0].strip()
        print(f"✓ Deno {ver}")
        return "deno", ""
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        r    = subprocess.run(["node", "--version"], capture_output=True, check=True)
        path = shutil.which("node") or "node"
        print(f"✓ Node.js {r.stdout.decode().strip()} (explicit flag)")
        return "node", path
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠  No JS runtime  →  winget install DenoLand.Deno")
        return "", ""


# ─── Download ─────────────────────────────────────────────────────────────────

def download(url: str, start: int, end: int, out_dir: str,
             auth_key: str, mode_key: str, runtime_flag: str) -> int:
    auth_value, _ = AUTH[auth_key]
    is_audio      = MODE.get(mode_key) == "audio"
    os.makedirs(out_dir, exist_ok=True)

    cmd = [sys.executable, "-m", "yt_dlp"]

    if runtime_flag:
        cmd += ["--js-runtimes", f"node:{runtime_flag}"]

    if is_audio:
        cmd += ["-f", "bestaudio[ext=m4a]/bestaudio"]
    else:
        cmd += [
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/bestvideo[ext=mp4]+bestaudio"
            "/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
        ]

    cmd += ["--playlist-items", f"{start}-{end}"]
    cmd += ["-o", os.path.join(out_dir, "%(title)s.%(ext)s")]

    if auth_value:
        cmd += ["--cookies-from-browser", auth_value]
    cmd += ["--extractor-args", "youtube:player_client=default,-android_sdkless"]
    cmd += [
        "--retries", "6", "--fragment-retries", "10",
        "--concurrent-fragments", "4",
        "--ignore-errors", "--geo-bypass",
    ]
    cmd.append(url)

    print(f"\n  {'audio (m4a)' if is_audio else 'video (mp4)'}  ·  items {start}–{end}"
          f"  →  {os.path.abspath(out_dir)}\n")
    return subprocess.run(cmd).returncode


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ask(prompt: str, default: str) -> str:
    val = input(f"  {prompt}  [{default}]: ").strip()
    return val if val else default

def ask_yn(prompt: str, default: bool) -> bool:
    val = input(f"  {prompt}  [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not val else val.startswith("y")

def parse_range(s: str) -> tuple[int, int]:
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a.strip()), int(b.strip())
    n = int(s)
    return n, n


# ─── Startup (runs in both modes) ─────────────────────────────────────────────

def startup(cfg: dict, silent: bool = False):
    """Run checks that are always needed. Returns (has_ffmpeg, runtime_name, runtime_flag)."""
    setup_local_ffmpeg()
    remove_oauth2_plugin()
    if cfg.get("auto_update", True):
        ensure_deps()
    elif not silent:
        print("  (updates skipped)")
    has_ffmpeg             = check_ffmpeg()
    runtime_name, runtime_flag = check_runtime()
    return has_ffmpeg, runtime_name, runtime_flag


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    cli = parse_cli(sys.argv[1:])

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║        YouTube Downloader  (yt-dlp)                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    has_ffmpeg, runtime_name, runtime_flag = startup(cfg)
    has_runtime = bool(runtime_name)

    # ══════════════════════════════════════════════════════════
    #  CLI MODE  —  yt 1-4 a https://...
    # ══════════════════════════════════════════════════════════
    if cli:
        url      = cli.get("url")      or cfg.get("url", "")
        range_raw= cli.get("range")    or cfg.get("range", "1")
        mode_key = cli.get("mode")     or cfg.get("mode", "1")
        out_dir  = cfg.get("output_dir", DEFAULT_CONFIG["output_dir"])
        auth_key = cfg.get("auth", "2")

        if not url:
            sys.exit("  No URL — pass one as an argument or run without args first to save one.")

        try:
            start, end = parse_range(range_raw)
        except ValueError:
            sys.exit(f"  Bad range: {range_raw!r} — use  1-4  or  3")

        # Save any new values back to config
        save_config({**cfg, "url": url, "range": range_raw, "mode": mode_key})

        _, auth_label = AUTH.get(auth_key, ("", "?"))
        is_audio = MODE[mode_key] == "audio"
        print(f"  {'audio' if is_audio else 'video'}  ·  {start}–{end}  ·  {auth_label}")
        print(f"  {url}")
        print()

        result = download(url, start, end, out_dir, auth_key, mode_key, runtime_flag)
        print()
        print("  ✅  Done!" if result == 0 else "  ⚠   Finished with errors.")
        sys.exit(result)

    # ══════════════════════════════════════════════════════════
    #  INTERACTIVE MODE
    # ══════════════════════════════════════════════════════════
    print()
    print("  ── Settings (Enter = keep [default]) ──────────────────")
    print()

    url = ask("Playlist or video URL", cfg.get("url") or "paste here")
    if not url or url == "paste here":
        sys.exit("  No URL. Exiting.")

    range_raw = ask("Range (e.g. 1-4, or just 3)", cfg["range"])
    try:
        start, end = parse_range(range_raw)
    except ValueError:
        sys.exit("  Bad range — use  1-4  or  3")

    out_dir = ask("Output folder", cfg["output_dir"])

    print()
    print("  Output mode:")
    print(f"    1  Video  — best quality mp4{'  ◄' if cfg.get('mode','1') == '1' else ''}")
    print(f"    2  Audio  — m4a (AAC, no transcoding){'  ◄' if cfg.get('mode') == '2' else ''}")
    mode_key = ask("Choice", cfg.get("mode", "1"))
    if mode_key not in MODE:
        mode_key = "1"

    if MODE[mode_key] == "audio" and not has_ffmpeg:
        print("  ⚠  ffmpeg missing — audio may come out as webm instead of m4a")

    print()
    print("  Auth method:")
    for k, (_, label) in AUTH.items():
        print(f"    {k}  {label}{'  ◄' if k == cfg.get('auth') else ''}")
    auth_key = ask("Choice", cfg.get("auth", "2"))
    if auth_key not in AUTH:
        auth_key = "2"
    auth_value, auth_label = AUTH[auth_key]

    if "list=WL" in url and auth_value is None:
        print()
        print("  ⚠  Watch Later (list=WL) is private — no-auth will fail.")
        if ask_yn("Switch to Firefox cookies?", True):
            auth_key, auth_value, auth_label = "2", "firefox", AUTH["2"][1]

    if auth_value is not None and not has_runtime:
        print()
        print("  ⚠  Cookie mode needs a JS runtime.")
        print("     Fix: winget install DenoLand.Deno  →  restart  →  try again")
        if not ask_yn("Continue anyway?", False):
            sys.exit("  Exiting.")

    print()
    cur_upd = cfg.get("auto_update", True)
    new_upd = ask_yn(
        f"Auto-update on startup (currently {'ON' if cur_upd else 'OFF'})?", cur_upd
    )

    save_config({"url": url, "range": range_raw, "output_dir": out_dir,
                 "auth": auth_key, "mode": mode_key, "auto_update": new_upd})

    is_audio   = MODE[mode_key] == "audio"
    mode_label = "Audio (m4a)" if is_audio else f"Video (mp4{'' if has_ffmpeg else ' ⚠no ffmpeg'})"
    print()
    print("  " + "─" * 54)
    print(f"  URL      {url}")
    print(f"  Items    {start} → {end}")
    print(f"  Mode     {mode_label}")
    print(f"  Auth     {auth_label}")
    print(f"  Output   {os.path.abspath(out_dir)}")
    print(f"  Runtime  {runtime_name or '⚠ not found'}")
    print("  " + "─" * 54)
    print()
    input("  Press Enter to start…   (Ctrl+C to cancel)\n")

    result = download(url, start, end, out_dir, auth_key, mode_key, runtime_flag)

    print()
    if result == 0:
        print(f"  ✅  Done!  Files in: {os.path.abspath(out_dir)}")
    else:
        print("  ⚠   Errors occurred:")
        print("    → 'format not available' / 'n challenge failed':")
        print("         pip install --upgrade yt-dlp-ejs  then try again")
        print("    → 'blocked in your country': geo-restricted, skip it")
        print("    → Try option 4 (No auth) for public content")
        print(f"\n  Files (if any) in: {os.path.abspath(out_dir)}")

    print()
    input("  Press Enter to exit…")


if __name__ == "__main__":
    main()
