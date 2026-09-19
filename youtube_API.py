from pytubefix import Search, YouTube
from pytubefix.cli import on_progress
import os

ruta_actual = os.path.dirname(os.path.abspath(__file__))
carpeta_videos = os.path.join(ruta_actual, "videos")

def buscar_video(query):
    results = Search(query)
    video = results.videos[0]
    print(f'Titulo: {video.title}')
    print(f'URL: {video.watch_url}')
    print(f'Duración: {video.length // 60} min')
    print('---')
    return video

def descargar_audio(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_audio_only()
    ys.download(output_path=carpeta_videos)
    print(f'Audio descargado en la carpeta: {carpeta_videos}')

def descargar_video(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_by_resolution("720p")
    ys.download(output_path=carpeta_videos)
    print(f'Video descargado en la carpeta: {carpeta_videos}')

# descargar_video('https://youtube.com/watch?v=dvgZkm1xWPE')