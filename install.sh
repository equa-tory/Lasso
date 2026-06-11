#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo
echo "=========================================="
echo " YouTube Downloader — Unix Setup"
echo "=========================================="
echo

# ── Python ────────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install via your package manager."
    echo "  Ubuntu/Debian:  sudo apt install python3"
    echo "  macOS:          brew install python"
    exit 1
fi
echo "OK $(python3 --version)"

# ── Deno ──────────────────────────────────────────────────────────────────────
if command -v deno &>/dev/null; then
    echo "OK $(deno --version | head -1)"
else
    echo
    echo "Installing Deno (JS runtime required by yt-dlp)..."
    curl -fsSL https://deno.land/install.sh | sh
    # Add deno to PATH for this session so the rest of the script can use it
    export DENO_INSTALL="$HOME/.deno"
    export PATH="$DENO_INSTALL/bin:$PATH"
fi

# ── ffmpeg ────────────────────────────────────────────────────────────────────
if command -v ffmpeg &>/dev/null; then
    echo "OK ffmpeg found"
else
    echo
    echo "ffmpeg not found. Install it:"
    echo "  Ubuntu/Debian:  sudo apt install ffmpeg"
    echo "  macOS:          brew install ffmpeg"
    echo "  (continuing anyway — install it before downloading videos)"
fi

# ── Create bin/yt ─────────────────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/bin"

cat > "$SCRIPT_DIR/bin/yt" << 'LAUNCHER'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/../yt_download.py" "$@"
LAUNCHER

chmod +x "$SCRIPT_DIR/bin/yt"
echo "Created bin/yt"

# ── Add bin/ to PATH in shell rc files ────────────────────────────────────────
BIN_PATH="$SCRIPT_DIR/bin"
ADDED=false

add_to_rc() {
    local RC="$1"
    if [ -f "$RC" ] && ! grep -qF "$BIN_PATH" "$RC" 2>/dev/null; then
        printf '\n# YouTube Downloader\nexport PATH="%s:$PATH"\n' "$BIN_PATH" >> "$RC"
        echo "Added to $RC"
        ADDED=true
    fi
}

add_to_rc "$HOME/.bashrc"
add_to_rc "$HOME/.zshrc"
add_to_rc "$HOME/.bash_profile"
add_to_rc "$HOME/.profile"

# Also add deno to PATH in rc files if freshly installed
if [ -d "$HOME/.deno/bin" ]; then
    for RC in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.profile"; do
        if [ -f "$RC" ] && ! grep -q 'DENO_INSTALL' "$RC" 2>/dev/null; then
            printf '\nexport DENO_INSTALL="$HOME/.deno"\nexport PATH="$DENO_INSTALL/bin:$PATH"\n' >> "$RC"
        fi
    done
fi

echo
echo "=========================================="
echo " Setup complete!"
echo
echo " Reload your shell:"
echo "   source ~/.bashrc    (bash)"
echo "   source ~/.zshrc     (zsh)"
echo "   or open a new terminal"
echo
echo " Then use:"
echo "   yt --help"
echo "   yt 1-4 v https://youtube.com/..."
echo "   yt 1 a https://youtu.be/..."
echo "   yt                  (interactive)"
echo "=========================================="
echo
