from pytubefix import Search, YouTube
from pytubefix.cli import on_progress
import os
import asyncio

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

async def descargar_audio(url: str) -> str:
    """
    Corre la descarga (bloqueante) en un hilo aparte del pool de
    threads de asyncio, así el event loop principal queda libre para
    seguir atendiendo otros webhooks/mensajes mientras se descarga.
    """
    return await asyncio.to_thread(_descargar_audio_sync, url)

def _descargar_audio_sync(url: str) -> str:
    """
    La lógica de siempre, sin cambios — sigue siendo 100% síncrona.
    La clave está en CÓMO se llama (ver descargar_audio abajo).
    """
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)
 
    ys = yt.streams.get_audio_only()
    ys.download(output_path=carpeta_videos)
    print(f'Audio descargado en la carpeta: {carpeta_videos}')
    return os.path.join(carpeta_videos, ys.default_filename)

async def descargar_video(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_by_resolution("720p")
    ys.download(output_path=carpeta_videos)
    print(f'Video descargado en la carpeta: {carpeta_videos}')
    return os.path.join(carpeta_videos, ys.default_filename)

# video = descargar_video('https://youtube.com/watch?v=dvgZkm1xWPE')
# print(video)
# audio = asyncio.run(descargar_audio('https://youtube.com/watch?v=dvgZkm1xWPE'))
# print(audio)