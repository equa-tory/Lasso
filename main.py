import yt_dlp
import os

def download_playlist(playlist_url, audio_format='mp3', download_path='.', start=1, end=None):
    # Создание пути, если он не существует
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': '192',
        }],
        'yesplaylist': True,
        'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),  # Путь и шаблон названия файла
        'retries': 10,  # Количество повторных попыток
        'socket_timeout': 15,  # Таймаут сокета в секундах
        'playliststart': start,  # Начало диапазона
    }

    if end:
        ydl_opts['playlistend'] = end  # Конец диапазона

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([playlist_url])

if __name__ == "__main__":
    playlist_url = input("Введите URL плейлиста YouTube: ")
    #audio_format = 'm4a'
    audio_format = input("Введите желаемый аудиоформат (mp3 или m4a): ").lower()
    #download_path = '/home/equa/Music/Loop/'
    download_path = input("Введите путь для сохранения файлов (напр. /path/to/download): ")
    start = int(input("Введите номер начального видео для скачивания: "))
    end_input = input("Введите номер конечного видео для скачивания (или оставьте пустым для скачивания до конца): ")
    end = int(end_input) if end_input else None

    if audio_format not in ['mp3', 'm4a']:
        print("Неподдерживаемый формат. Используйте 'mp3' или 'm4a'.")
    else:
        download_playlist(playlist_url, audio_format, download_path, start, end)
