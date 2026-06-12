#!/usr/bin/env python3
"""
YouTube Downloader — CLI / core library

Usage:
  yt                          interactive
  yt 1-4                      items 1-4, saved url/mode
  yt 1-4 a                    items 1-4, audio
  yt 1 v https://youtu.be/…   item 1, video, given url
  yt l a https://…            sync mode — download only new items

Arguments (any order, any combination):
  RANGE   1-4 or 3
  v/a     video (mp4) or audio (m4a)
  l       listen / sync mode (skip already-downloaded, uses archive file)
  URL     youtube link
"""

import subprocess, sys, os, re, json, shutil, hashlib

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "yt_dl_config.json")

DEFAULT_CONFIG = {
    "video_url":    "",
    "video_output": os.path.join(os.path.expanduser("~"), "Downloads", "yt_downloads"),
    "audio_url":    "",
    "audio_output": os.path.join(os.path.expanduser("~"), "Downloads", "yt_downloads"),
    "range":        "1",
    "auth":         "2",
    "mode":         "1",
    "auto_update":  True,
    "listen_interval": 5, # minutes between checks in listen mode
}

AUTH = {
    "1": ("chrome",  "Chrome  cookies  (private playlists, best quality)"),
    "2": ("firefox", "Firefox cookies  (private playlists, best quality)"),
    "3": ("edge",    "Edge    cookies  (private playlists, best quality)"),
    "4": (None,      "No auth          (public content, typically 1080p)"),
}

MODE = {"1": "video", "2": "audio"}


# ─── Config ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        # Migrate from old flat-url format
        if "url" in data and "video_url" not in data:
            data["video_url"] = data.pop("url", "")
        if "output_dir" in data and "video_output" not in data:
            out = data.pop("output_dir", "")
            data.setdefault("video_output", out)
            data.setdefault("audio_output", out)
        return {**DEFAULT_CONFIG, **data}
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# ─── CLI parser ───────────────────────────────────────────────────────────────

def parse_cli(argv: list) -> dict:
    """Positional args in any order. Returns {} for interactive mode."""
    if not argv:
        return {}
    if argv[0] in ("-h", "--help"):
        print(__doc__); sys.exit(0)
    result = {}
    for arg in argv:
        a = arg.strip()
        if   a.lower() in ("v", "video"):              result["mode"]   = "1"
        elif a.lower() in ("a", "audio"):              result["mode"]   = "2"
        elif a.lower() in ("l", "listen", "sync"):     result["listen"] = True
        elif re.match(r"^\d+(-\d+)?$", a):             result["range"]  = a
        elif a.startswith(("http://", "https://")):    result["url"]    = a
        else: print(f"  Unknown arg: {a!r}  (ignored)")
    return result


# ─── Local ffmpeg ─────────────────────────────────────────────────────────────

def setup_local_ffmpeg():
    ffmpeg_dir = os.path.join(SCRIPT_DIR, "ffmpeg")
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if os.path.isfile(os.path.join(ffmpeg_dir, exe)):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


# ─── Deps ─────────────────────────────────────────────────────────────────────

def _pip(*args):
    subprocess.check_call([sys.executable, "-m", "pip", *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def remove_oauth2_plugin():
    try:
        import yt_dlp_youtube_oauth2  # noqa
    except ImportError:
        return
    print("  Removing OAuth2 plugin...", end=" ", flush=True)
    try:
        _pip("uninstall", "yt-dlp-youtube-oauth2", "-y"); print("✓")
    except subprocess.CalledProcessError:
        print("✗  pip uninstall yt-dlp-youtube-oauth2 -y")

def ensure_deps():
    try:
        import yt_dlp  # noqa
        print("  Updating yt-dlp...", end=" ", flush=True)
    except ImportError:
        print("  Installing yt-dlp...", end=" ", flush=True)
    _pip("install", "--upgrade", "yt-dlp[default]"); print("✓")

    try:
        import yt_dlp_ejs  # noqa
        print("  Updating yt-dlp-ejs...", end=" ", flush=True)
    except ImportError:
        print("  Installing yt-dlp-ejs...", end=" ", flush=True)
    try:
        _pip("install", "--upgrade", "yt-dlp-ejs"); print("✓")
    except subprocess.CalledProcessError:
        print("✗  (pip install yt-dlp-ejs)")

def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        local = os.path.isfile(os.path.join(SCRIPT_DIR, "ffmpeg",
                    "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"))
        print(f"✓ ffmpeg {'(./ffmpeg/)' if local else '(system)'}")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("⚠  ffmpeg not found  →  add ffmpeg.exe to ./ffmpeg/ or winget install Gyan.FFmpeg")
        return False

def check_runtime() -> tuple:
    """Prints result and returns (name, flag)."""
    name, flag = check_runtime_silent()
    if name == "deno":   print(f"✓ Deno (default runtime)")
    elif name == "node": print(f"✓ Node.js (explicit flag)")
    else:                print("⚠  No JS runtime  →  winget install DenoLand.Deno")
    return name, flag

def check_runtime_silent() -> tuple:
    """No output — used by UI and checks."""
    try:
        subprocess.run(["deno", "--version"], capture_output=True, check=True)
        return "deno", ""
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return "node", shutil.which("node") or "node"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "", ""


# ─── Build command ────────────────────────────────────────────────────────────

def build_cmd(url: str, start: int, end: int, out_dir: str,
              auth_key: str, mode_key: str, runtime_flag: str,
              listen: bool = False) -> list:
    """
    Returns the full yt-dlp command list.
    Separated from download() so the UI can run it with Popen.
    """
    auth_value, _ = AUTH[auth_key]
    is_audio      = MODE.get(mode_key) == "audio"

    cmd = [sys.executable, "-m", "yt_dlp"]

    if runtime_flag:
        cmd += ["--js-runtimes", f"node:{runtime_flag}"]

    if is_audio:
        cmd += ["-f", "bestaudio[ext=m4a]/bestaudio"]
        cmd += [
            "--embed-thumbnail",                                 # thumbnail → cover art
            "--embed-metadata",                                  # title, date, description
            "--parse-metadata", "%(uploader)s:%(meta_artist)s", # channel  → Artist
            "--parse-metadata", "%(title)s:%(meta_album)s",     # title    → Album
        ]
    else:
        cmd += ["-f",
                "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                "/bestvideo[ext=mp4]+bestaudio"
                "/bestvideo+bestaudio/best",
                "--merge-output-format", "mp4"]

    if listen:
        # Archive file per URL so each playlist has its own history
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        archive = os.path.join(out_dir, f"_yt_archive_{h}.txt")
        cmd += ["--download-archive", archive]

    # In listen mode the archive handles "already downloaded" — no range needed.
    # In normal mode honour the user's range.
    if not listen:
        cmd += ["--playlist-items", f"{start}-{end}"]
    cmd += ["-o", os.path.join(out_dir, "%(title)s.%(ext)s")]

    if auth_value:
        cmd += ["--cookies-from-browser", auth_value]
    cmd += ["--extractor-args", "youtube:player_client=default,-android_sdkless"]
    cmd += ["--retries", "6", "--fragment-retries", "10",
            "--concurrent-fragments", "4", "--ignore-errors", "--geo-bypass"]
    cmd.append(url)
    return cmd


def listen_loop(url: str, out_dir: str, auth_key: str, mode_key: str,
                runtime_flag: str, interval_min: int = 5):
    """
    Infinite loop: check playlist every interval_min minutes.
    yt-dlp's --download-archive skips already-downloaded IDs automatically —
    only videos added since the last run are downloaded.
    Stop with Ctrl-C.
    """
    import time
    from datetime import datetime

    os.makedirs(out_dir, exist_ok=True)
    h       = hashlib.md5(url.encode()).hexdigest()[:8]
    archive = os.path.join(out_dir, f"_yt_archive_{h}.txt")
    is_audio = MODE.get(mode_key) == "audio"

    print(f"  Listening for new {'audio' if is_audio else 'video'}")
    print(f"  Playlist : {url}")
    print(f"  Archive  : {archive}")
    print(f"  Interval : every {interval_min} min")
    print(f"  Output   : {os.path.abspath(out_dir)}")
    print(f"  Ctrl-C to stop.\n")

    iteration = 0
    try:
        while True:
            iteration += 1
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}]  Check #{iteration} — scanning for new items…")

            # Full playlist scan — archive skips already-downloaded IDs
            cmd = build_cmd(url, 1, 99999, out_dir, auth_key, mode_key,
                            runtime_flag, listen=True)
            subprocess.run(cmd)

            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  [{ts}]  Done.  Next check in {interval_min} min  (Ctrl-C to stop)")

            time.sleep(interval_min * 60)

    except KeyboardInterrupt:
        print("\n\n  Stopped listening.")



def download(url, start, end, out_dir, auth_key, mode_key, runtime_flag,
             listen=False) -> int:
    os.makedirs(out_dir, exist_ok=True)
    is_audio = MODE.get(mode_key) == "audio"
    cmd = build_cmd(url, start, end, out_dir, auth_key, mode_key, runtime_flag, listen)
    print(f"\n  {'audio (m4a)' if is_audio else 'video (mp4)'}  ·  items {start}–{end}"
          f"{'  [sync]' if listen else ''}  →  {os.path.abspath(out_dir)}\n")
    return subprocess.run(cmd).returncode


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ask(prompt, default):
    val = input(f"  {prompt}  [{default}]: ").strip()
    return val if val else default

def ask_yn(prompt, default):
    val = input(f"  {prompt}  [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not val else val.startswith("y")

def parse_range(s):
    s = s.strip()
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a.strip()), int(b.strip())
    n = int(s); return n, n

def startup(cfg):
    """Always-run checks. Returns (has_ffmpeg, runtime_name, runtime_flag)."""
    setup_local_ffmpeg()
    remove_oauth2_plugin()
    if cfg.get("auto_update", True):
        ensure_deps()
    else:
        print("  (updates skipped)")
    return check_ffmpeg(), *check_runtime()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    cfg = load_config()
    cli = parse_cli(sys.argv[1:])

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║        YouTube Downloader                            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    has_ffmpeg, runtime_name, runtime_flag = startup(cfg)
    has_runtime = bool(runtime_name)

    # ── CLI mode ──────────────────────────────────────────────────────────────
    if cli:
        mode_key = cli.get("mode") or cfg.get("mode", "1")
        listen   = cli.get("listen", False)
        url_key  = "video_url"  if mode_key == "1" else "audio_url"
        out_key  = "video_output" if mode_key == "1" else "audio_output"

        url      = cli.get("url") or cfg.get(url_key, "")
        out_dir  = cfg.get(out_key, DEFAULT_CONFIG[out_key])
        auth_key = cfg.get("auth", "2")

        if not url:
            sys.exit("  No URL — pass one as argument or run without args to save one.")

        if listen:
            range_raw = f"1-{cfg.get('listen_count', 20)}"
        else:
            range_raw = cli.get("range") or cfg.get("range", "1")

        try:
            start, end = parse_range(range_raw)
        except ValueError:
            sys.exit(f"  Bad range: {range_raw!r}")

        # Save back
        save_config({**cfg, "mode": mode_key, url_key: url,
                     "range": cli.get("range", cfg.get("range", "1"))})

        _, auth_label = AUTH.get(auth_key, ("", "?"))

        if listen:
            interval = int(cfg.get("listen_interval", 5))
            listen_loop(url, out_dir, auth_key, mode_key, runtime_flag, interval)
            sys.exit(0)

        print(f"  {'audio' if mode_key=='2' else 'video'}"
              f"  ·  {start}–{end}  ·  {auth_label}")
        print(f"  {url}\n")
        sys.exit(download(url, start, end, out_dir, auth_key, mode_key, runtime_flag))

    # ── Interactive mode ──────────────────────────────────────────────────────
    print("  ── Settings (Enter = keep [default]) ──────────────────\n")

    mode_key = cfg.get("mode", "1")
    url_key  = "video_url"  if mode_key == "1" else "audio_url"
    out_key  = "video_output" if mode_key == "1" else "audio_output"

    url = ask("Playlist or video URL", cfg.get(url_key) or "paste here")
    if not url or url == "paste here":
        sys.exit("  No URL.")

    range_raw = ask("Range (e.g. 1-4, or just 3)", cfg["range"])
    try:
        start, end = parse_range(range_raw)
    except ValueError:
        sys.exit("  Bad range.")

    out_dir = ask("Output folder", cfg[out_key])

    print()
    print(f"  Output mode:")
    print(f"    1  Video  (mp4){'  ◄' if mode_key=='1' else ''}")
    print(f"    2  Audio  (m4a){'  ◄' if mode_key=='2' else ''}")
    new_mode = ask("Choice", mode_key)
    if new_mode not in MODE: new_mode = mode_key
    if new_mode != mode_key:
        # mode changed — reload url/out defaults but keep what user typed
        mode_key = new_mode
        url_key  = "video_url"  if mode_key == "1" else "audio_url"
        out_key  = "video_output" if mode_key == "1" else "audio_output"

    listen = ask_yn("Listen mode (infinite loop, download new items automatically)?", False)

    print()
    print("  Auth method:")
    for k, (_, label) in AUTH.items():
        print(f"    {k}  {label}{'  ◄' if k == cfg.get('auth') else ''}")
    auth_key = ask("Choice", cfg.get("auth", "2"))
    if auth_key not in AUTH: auth_key = "2"
    auth_value, auth_label = AUTH[auth_key]

    if "list=WL" in url and auth_value is None:
        print("\n  ⚠  Watch Later needs cookies.")
        if ask_yn("Switch to Firefox?", True):
            auth_key, auth_value, auth_label = "2", "firefox", AUTH["2"][1]

    if auth_value and not has_runtime:
        print("\n  ⚠  Cookie mode needs a JS runtime.  winget install DenoLand.Deno")
        if not ask_yn("Continue anyway?", False): sys.exit()

    cur_upd = cfg.get("auto_update", True)
    new_upd = ask_yn(f"\n  Auto-update on startup (currently {'ON' if cur_upd else 'OFF'})?", cur_upd)

    save_config({**cfg,
                 url_key: url, out_key: out_dir,
                 "range": range_raw, "mode": mode_key,
                 "auth": auth_key, "auto_update": new_upd})

    is_audio   = MODE[mode_key] == "audio"
    mode_label = f"{'Audio (m4a)' if is_audio else 'Video (mp4)'}{'' if has_ffmpeg else ' ⚠no ffmpeg'}"
    print()
    print("  " + "─"*54)
    print(f"  URL      {url}")
    print(f"  Items    {start} → {end}{'  [sync — new only]' if listen else ''}")
    print(f"  Mode     {mode_label}")
    print(f"  Auth     {auth_label}")
    print(f"  Output   {os.path.abspath(out_dir)}")
    print(f"  Runtime  {runtime_name or '⚠ not found'}")
    print("  " + "─"*54 + "\n")
    interval = int(cfg.get("listen_interval", 5))
    if listen:
        print()
        print(f"  Starting listen mode — checks every {interval} min.")
        print(f"  Add videos to your playlist from any device and they will")
        print(f"  be downloaded automatically.  Ctrl-C to stop.\n")
        listen_loop(url, out_dir, auth_key, mode_key, runtime_flag, interval)
        sys.exit(0)

    input("  Press Enter to start…   (Ctrl+C to cancel)\n")

    result = download(url, start, end, out_dir, auth_key, mode_key, runtime_flag)

    print()
    if result == 0:
        print(f"  ✅  Done!  Files in: {os.path.abspath(out_dir)}")
    else:
        print("  ⚠   Errors occurred:")
        print("    → format unavailable / n-challenge: pip install --upgrade yt-dlp-ejs")
        print("    → blocked in your country: geo-restricted, skip it")
        print("    → try option 4 (No auth) for public content")
        print(f"\n  Files (if any) in: {os.path.abspath(out_dir)}")
    print()
    input("  Press Enter to exit…")


if __name__ == "__main__":
    main()
