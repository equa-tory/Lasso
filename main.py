import yt_dlp
import os

def download_playlist(playlist_url, audio_format, download_path, start, end):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
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
    playlist_input = input("Введите URL плейлиста или видео YouTube: ")
    playlist_url = playlist_input if playlist_input else "https://www.youtube.com/playlist?list=PL4d3ASKA-XRUBJ9trFXOPfJv9SqcdXiLq"

    audio_input = input("Введите желаемый аудиоформат (оставьте пустым для 'm4a'): ").lower()
    audio_format = audio_input if audio_input else "m4a"

    download_input = input("Введите путь для сохранения файлов (оставьте пустым для '/Users/equa/Downloads'): ")
    download_path = download_input if download_input else "/Users/equa/Downloads"

    start_input = input("Введите номер начального видео для скачивания (оставьте пустым для 1): ")
    start = int(start_input) if start_input else 1

    end_input = input("Введите номер конечного видео для скачивания (оставьте пустым для скачивания до конца): ")
    end = int(end_input) if end_input else None

    download_playlist(playlist_url, audio_format, download_path, start, end)
