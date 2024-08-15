import yt_dlp
import os

def download_playlist(playlist_url, audio_format='mp3', download_path='.', start=1, end=None):
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': '192',
        }],
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
    playlist_url = input("Введите URL плейлиста YouTube: ")
    audio_format = input("Введите желаемый аудиоформат: ").lower()
    download_path = input("Введите путь для сохранения файлов: ")
    start = int(input("Введите номер начального видео для скачивания: "))
    end_input = input("Введите номер конечного видео для скачивания (или оставьте пустым для скачивания до конца): ")
    end = int(end_input) if end_input else None

    download_playlist(playlist_url, audio_format, download_path, start, end)
