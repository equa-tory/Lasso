import yt_dlp
import os
import sys
import json

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)  # папка с exe
    return os.path.dirname(os.path.abspath(__file__))

def load_config():
    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, "config.json")

    if not os.path.exists(config_path):
        print("config.json не найден рядом с программой")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resolve_path(path):
    return os.path.expanduser(path)

def download_playlist(playlist_url, audio_format, download_path, start, end):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'ffmpeg_location': get_ffmpeg_path(),
        'writethumbnail': True,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': '192',
            },
            {
                'key': 'EmbedThumbnail',
            }
        ],
        'ignoreerrors': True,
        'yesplaylist': True,
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
        'retries': 3,
        'socket_timeout': 25,
        'playliststart': start,
    }

    if end:
        ydl_opts['playlistend'] = end

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])


if __name__ == "__main__":
    args = sys.argv[1:]
    cfg = load_config()

    start = cfg.get("start", 1)
    end = cfg.get("end", None)
    playlist_url = cfg.get("url")
    audio_format = cfg.get("format", "m4a")
    download_path = resolve_path(cfg.get("path", "~/Downloads"))

    try:
        if len(args) >= 1:
            start = int(args[0])
        if len(args) >= 2:
            end = int(args[1])
        if len(args) >= 3:
            playlist_url = args[2]
        if len(args) >= 4:
            audio_format = args[3]
        if len(args) >= 5:
            download_path = args[4]
    except:
        print("Ошибка аргументов")
        sys.exit(1)

    download_playlist(playlist_url, audio_format, download_path, start, end)