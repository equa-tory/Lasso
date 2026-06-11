# YouTube Downloader

Download YouTube videos and audio from the terminal.
Supports single videos, playlists with range selection, best quality mp4 and m4a audio.

---

## Folder structure

```
yt-downloader/
├── yt_download.py       main script
├── install.bat          Windows setup (run once)
├── install.sh           macOS / Linux setup (run once)
├── run_downloader.bat   double-click launcher (Windows, no install needed)
├── bin/
│   ├── yt.bat           Windows  — created by install.bat
│   └── yt               Unix     — created by install.sh
├── ffmpeg/
│   ├── ffmpeg.exe       (Windows) put ffmpeg here OR install system-wide
│   └── ffprobe.exe      (Windows) same
└── yt_dl_config.json    saved settings (auto-created on first run)
```

---

## Setup

### Windows

1. Double-click **`install.bat`**

   It will:
   - Check Python (tells you where to get it if missing)
   - Install Deno (JS runtime yt-dlp needs)
   - Detect ffmpeg in `./ffmpeg/` or install it via winget
   - Create `bin\yt.bat` and add `bin\` to your user PATH

2. Open a **new terminal** and test:
   ```
   yt --help
   ```

> **No winget?**  Install Python from https://www.python.org/downloads/ (tick *Add to PATH*),
> Deno from https://deno.land, and place ffmpeg.exe + ffprobe.exe in the `./ffmpeg/` folder.

### macOS / Linux

```bash
chmod +x install.sh
./install.sh
source ~/.bashrc   # or ~/.zshrc
yt --help
```

### No install (Windows, double-click)

Just double-click **`run_downloader.bat`** — opens the interactive menu, no PATH changes needed.

---

## Usage

### Interactive (no arguments)

```
yt
```

Walks you through each setting with saved defaults. Good for first use or changing settings.

### Command line

```
yt [range] [v|a] [url]
```

All three arguments are optional and can be in any order.
Anything not specified is taken from your last saved settings.

| Argument | Values | Example |
|---|---|---|
| range | `1-4` or single `3` | `1-4` |
| mode | `v` / `video` or `a` / `audio` | `a` |
| url | YouTube URL | `https://youtu.be/...` |

**Examples:**

```bash
yt                                        # interactive, uses saved defaults
yt 1-4                                    # items 1–4, saved mode/url/auth
yt 1-4 a                                  # items 1–4, audio (m4a)
yt 1 v https://youtu.be/abc              # item 1, video, given URL
yt a https://youtube.com/playlist?list=  # audio, full playlist
yt 3 https://youtu.be/abc               # single item 3 from a playlist
```

---

## Settings (interactive)

| Setting | What it does |
|---|---|
| URL | YouTube link — video, playlist, or Watch Later (`list=WL`) |
| Range | Which playlist items to download. `1-4` = first four, `3` = only item 3 |
| Output folder | Where files are saved |
| Mode | `1` = Video mp4 · `2` = Audio m4a |
| Auth | Which browser's cookies to use (needed for private playlists and best quality) |
| Auto-update | Whether to update yt-dlp on every startup |

All answers are saved as defaults for the next run.

---

## Auth / quality

| Choice | Quality | Private playlists |
|---|---|---|
| Chrome / Firefox / Edge cookies | Best available | ✓ Yes |
| No auth | Typically 1080p | ✗ Public only |

For Watch Later (`list=WL`) or any private playlist, browser cookies are required.
The script will warn and offer to switch automatically.

> Tip: close Firefox completely before running if you get "database is locked" errors.

---

## ffmpeg

ffmpeg is required to merge separate video and audio streams (needed for 1080p+).

**Windows:** Place `ffmpeg.exe` and `ffprobe.exe` in the `./ffmpeg/` folder next to the script.
The script detects them automatically — no PATH changes needed.

**macOS / Linux:** Install via package manager (`brew install ffmpeg` / `sudo apt install ffmpeg`).

---

## Troubleshooting

**"yt" command not found**
Re-run the install script and open a new terminal window.

**"No JS runtime found"**
Install Deno: `winget install DenoLand.Deno` — then restart the terminal.

**Downloads at 360p instead of 1080p, or "format not available"**
The `yt-dlp-youtube-oauth2` plugin may be installed and interfering.
Remove it: `pip uninstall yt-dlp-youtube-oauth2 -y`
The script also removes it automatically on startup.

**"blocked in your country"**
That video is geo-restricted. The script skips it and continues with the rest.

**Slow startup**
Answer `n` to the auto-update question — or set `"auto_update": false` in `yt_dl_config.json`.
