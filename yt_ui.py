#!/usr/bin/env python3
"""YouTube Downloader — Tkinter GUI.  Launch: python yt_ui.py"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading, queue, subprocess, sys, os

# Allow importing yt_download from same folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_download as ytd


# ─── App ──────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Downloader")
        self.geometry("720x560")
        self.minsize(620, 480)

        self._cfg   = ytd.load_config()
        self._proc  = None
        self._queue = queue.Queue()

        self._mode   = tk.StringVar(value=self._cfg.get("mode", "1"))
        self._listen = tk.BooleanVar(value=False)

        self._apply_style()
        self._build_ui()
        self._load_fields()       # fill fields from config
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Style ──────────────────────────────────────────────────────────────────
    def _apply_style(self):
        s = ttk.Style(self)
        for theme in ("vista", "winnative", "aqua", "clam", "default"):
            try: s.theme_use(theme); break
            except Exception: pass
        self.configure(bg=s.lookup("TFrame", "background") or "#f0f0f0")

    # ── Build UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        P = dict(padx=8, pady=4)

        # ── Mode row ──────────────────────────────────────────────────────────
        top = ttk.Frame(self, padding="10 8 10 0")
        top.pack(fill="x")

        ttk.Label(top, text="Mode:").pack(side="left")
        ttk.Radiobutton(top, text=" Video (mp4) ", variable=self._mode,
                        value="1", command=self._on_mode).pack(side="left", padx=2)
        ttk.Radiobutton(top, text=" Audio (m4a) ", variable=self._mode,
                        value="2", command=self._on_mode).pack(side="left", padx=2)
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=14, pady=2)
        self._cb_listen = ttk.Checkbutton(top, text="Listen mode  (infinite loop)",
                                           variable=self._listen,
                                           command=self._on_listen)
        self._cb_listen.pack(side="left")
        ttk.Label(top, text="  every").pack(side="left")
        self._interval = ttk.Entry(top, width=4)
        self._interval.insert(0, "5")
        self._interval.pack(side="left", padx=2)
        ttk.Label(top, text="min").pack(side="left")

        # ── Form ──────────────────────────────────────────────────────────────
        frm = ttk.LabelFrame(self, text="Settings", padding="8 6")
        frm.pack(fill="x", padx=10, pady=6)
        frm.columnconfigure(1, weight=1)

        def lbl(row, text):
            ttk.Label(frm, text=text).grid(row=row, column=0, sticky="e", **P)

        lbl(0, "URL")
        self._url = ttk.Entry(frm)
        self._url.grid(row=0, column=1, columnspan=2, sticky="ew", **P)

        lbl(1, "Range")
        rf = ttk.Frame(frm)
        rf.grid(row=1, column=1, sticky="w", **P)
        self._range = ttk.Entry(rf, width=9)
        self._range.pack(side="left")
        self._range_hint = ttk.Label(rf, foreground="#888",
                                      text="  1-4 or 3  (ignored in sync mode)")
        self._range_hint.pack(side="left")

        lbl(2, "Output")
        self._output = ttk.Entry(frm)
        self._output.grid(row=2, column=1, sticky="ew", **P)
        ttk.Button(frm, text="Browse…", width=8,
                   command=self._browse).grid(row=2, column=2, **P)

        lbl(3, "Auth")
        self._auth_labels = [v for _, v in ytd.AUTH.values()]
        self._auth_keys   = list(ytd.AUTH.keys())
        self._auth_var    = tk.StringVar()
        cb = ttk.Combobox(frm, textvariable=self._auth_var,
                          values=self._auth_labels, state="readonly")
        cb.grid(row=3, column=1, sticky="w", **P)
        ak = self._cfg.get("auth", "2")
        self._auth_var.set(ytd.AUTH[ak][1])

        # ── Buttons ───────────────────────────────────────────────────────────
        bf = ttk.Frame(self, padding="10 2")
        bf.pack(fill="x")
        self._btn_dl = ttk.Button(bf, text="▶  Download",
                                   command=self._start, width=14)
        self._btn_dl.pack(side="left", padx=(0, 6))
        self._btn_stop = ttk.Button(bf, text="■  Stop",
                                     command=self._stop, width=8, state="disabled")
        self._btn_stop.pack(side="left")
        ttk.Separator(bf, orient="vertical").pack(side="left", fill="y", padx=10, pady=3)
        self._btn_dlna = ttk.Button(bf, text="🖼  Fix DLNA",
                                     command=self._fix_dlna, width=12)
        self._btn_dlna.pack(side="left")
        self._status = ttk.Label(bf, text="")
        self._status.pack(side="left", padx=12)

        # ── Log ───────────────────────────────────────────────────────────────
        lf = ttk.LabelFrame(self, text="Output", padding="4 4")
        lf.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        font = ("Consolas", 9) if sys.platform == "win32" else ("Monospace", 9)
        self._log = scrolledtext.ScrolledText(
            lf, wrap="word", font=font,
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="white", relief="flat",
        )
        self._log.pack(fill="both", expand=True)
        self._log.config(state="disabled")

    # ── Field management ──────────────────────────────────────────────────────
    def _load_fields(self):
        m = self._mode.get()
        url = self._cfg.get("video_url" if m=="1" else "audio_url", "")
        out = self._cfg.get("video_output" if m=="1" else "audio_output",
                            ytd.DEFAULT_CONFIG["video_output"])
        rng = self._cfg.get("range", "1")
        self._url.delete(0, "end");    self._url.insert(0, url)
        self._range.delete(0, "end"); self._range.insert(0, rng)
        self._output.delete(0, "end"); self._output.insert(0, out)

    def _on_mode(self): self._load_fields()
    def _on_listen(self):
        dis = self._listen.get()
        self._range.config(state="disabled" if dis else "normal")
        if dis:
            self._range_hint.config(text="  (all new items — archive tracks downloads)")
            self._btn_dl.config(text="▶  Start Listening")
        else:
            self._range_hint.config(text="  1-4 or 3")
            self._btn_dl.config(text="▶  Download")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._output.get() or os.path.expanduser("~"))
        if d:
            self._output.delete(0, "end"); self._output.insert(0, d)

    def _auth_key(self):
        label = self._auth_var.get()
        for k, (_, v) in ytd.AUTH.items():
            if v == label: return k
        return "2"

    # ── Download ──────────────────────────────────────────────────────────────
    def _start(self):
        url      = self._url.get().strip()
        out_dir  = self._output.get().strip()
        mode_key = self._mode.get()
        auth_key = self._auth_key()
        listen   = self._listen.get()
        range_s  = (f"1-{self._cfg.get('listen_count', 20)}"
                    if listen else self._range.get().strip() or "1")

        if not url:
            self._log_write("⚠  No URL entered.\n"); return

        try: start, end = ytd.parse_range(range_s)
        except ValueError:
            self._log_write(f"⚠  Bad range: {range_s!r}\n"); return

        # Save to config
        url_key = "video_url"    if mode_key == "1" else "audio_url"
        out_key = "video_output" if mode_key == "1" else "audio_output"
        self._cfg.update({url_key: url, out_key: out_dir,
                          "range": self._range.get().strip(),
                          "mode": mode_key, "auth": auth_key})
        ytd.save_config(self._cfg)

        os.makedirs(out_dir, exist_ok=True)
        _, runtime_flag = ytd.check_runtime_silent()
        cmd = ytd.build_cmd(url, start, end, out_dir, auth_key, mode_key,
                            runtime_flag, listen=listen)

        self._log_clear()
        mode_str = "audio" if mode_key == "2" else "video"
        sync_str = "  [sync]" if listen else ""
        self._log_write(f"▶  {mode_str}{sync_str}  ·  {start}–{end}\n   {url}\n\n")

        self._btn_dl.config(state="disabled")
        self._btn_stop.config(state="normal")
        self._status.config(text="Downloading…", foreground="#555")

        if listen:
            try:
                interval_min = int(self._interval.get() or "5")
            except ValueError:
                interval_min = 5
            self._listen_stop = threading.Event()
            threading.Thread(target=self._run_listen,
                             args=(cmd, interval_min, out_dir, mode_key),
                             daemon=True).start()
        else:
            threading.Thread(target=self._run,
                             args=(cmd, out_dir, mode_key),
                             daemon=True).start()
        self.after(80, self._poll)

    def _run(self, cmd, out_dir, mode_key):
        import time
        t0 = time.time()
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
            )
            for line in self._proc.stdout:
                self._queue.put(line)
            self._proc.wait()
            rc = self._proc.returncode
        except Exception as e:
            self._queue.put(f"\n⚠  Could not start: {e}\n")
            rc = 1
        if mode_key != "2":  # not audio
            self._queue.put("\n")
            ytd.dlna_fix_dir(out_dir,
                             cb=lambda m: self._queue.put(m + "\n"),
                             since_mtime=t0)
        self._queue.put(("__done__", rc))

    def _run_listen(self, first_cmd, interval_min, out_dir, mode_key):
        """Infinite loop: run yt-dlp, sleep, repeat. _listen_stop signals exit."""
        import time
        from datetime import datetime
        iteration = 0
        while not self._listen_stop.is_set():
            iteration += 1
            ts = datetime.now().strftime("%H:%M:%S")
            self._queue.put(f"\n  [{ts}]  Check #{iteration} — scanning for new items…\n")
            import time
            t0 = time.time()
            try:
                self._proc = subprocess.Popen(
                    first_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                )
                for line in self._proc.stdout:
                    self._queue.put(line)
                self._proc.wait()
            except Exception as e:
                self._queue.put(f"  Error: {e}\n")

            if mode_key != "2":  # not audio
                self._queue.put("\n")
                ytd.dlna_fix_dir(out_dir,
                                 cb=lambda m: self._queue.put(m + "\n"),
                                 since_mtime=t0)
            if self._listen_stop.is_set():
                break

            ts = datetime.now().strftime("%H:%M:%S")
            self._queue.put(f"\n  [{ts}]  Done.  Next check in {interval_min} min…\n")
            # Sleep in 1-second ticks so Stop responds quickly
            for remaining in range(interval_min * 60, 0, -1):
                if self._listen_stop.is_set():
                    break
                self._queue.put(("__countdown__", remaining, interval_min))
                time.sleep(1)

        self._queue.put(("__done__", 0))

    def _poll(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__done__":
                    rc = item[1]
                    self._btn_dl.config(state="normal")
                    self._btn_stop.config(state="disabled")
                    self._btn_dl.config(text="▶  Download" if not self._listen.get()
                                        else "▶  Start Listening")
                    if rc == 0:
                        self._status.config(text="✅  Done", foreground="#2a7")
                    else:
                        self._status.config(text="⚠  Finished with errors", foreground="#c80")
                    return
                elif isinstance(item, tuple) and item[0] == "__countdown__":
                    remaining, total = item[1], item[2]
                    m, s = divmod(remaining, 60)
                    self._status.config(
                        text=f"⏳  Next check in {m}:{s:02d}  (check every {total} min)",
                        foreground="#555")
                    continue
                self._log_write(item)
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _fix_dlna(self):
        """Batch-process all existing videos in the current output folder."""
        out_dir = self._output.get().strip()
        if not out_dir or not os.path.isdir(out_dir):
            self._log_write("⚠  Output folder not found.\n")
            return
        self._log_clear()
        self._log_write(f"🖼  DLNA fix — scanning {out_dir}\n\n")
        self._btn_dlna.config(state="disabled")
        self._btn_dl.config(state="disabled")
        def _task():
            ytd.dlna_fix_dir(out_dir, cb=lambda m: self._queue.put(m + "\n"))
            self._queue.put(("__dlna_done__", 0))
        threading.Thread(target=_task, daemon=True).start()
        self.after(80, self._poll_dlna)

    def _poll_dlna(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__dlna_done__":
                    self._btn_dlna.config(state="normal")
                    self._btn_dl.config(state="normal")
                    self._status.config(text="✅  DLNA fix done", foreground="#2a7")
                    return
                if isinstance(item, str):
                    self._log_write(item)
        except queue.Empty:
            pass
        self.after(80, self._poll_dlna)

    def _stop(self):
        if hasattr(self, "_listen_stop"):
            self._listen_stop.set()
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            self._log_write("\n■  Stopped.\n")
        self._btn_dl.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._status.config(text="Stopped", foreground="#888")

    # ── Log helpers ───────────────────────────────────────────────────────────
    def _log_write(self, text):
        self._log.config(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.config(state="disabled")

    def _log_clear(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    def _on_close(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self.destroy()


# ─── Entry ────────────────────────────────────────────────────────────────────

def main():
    ytd.setup_local_ffmpeg()
    ytd.remove_oauth2_plugin()
    App().mainloop()

if __name__ == "__main__":
    main()
