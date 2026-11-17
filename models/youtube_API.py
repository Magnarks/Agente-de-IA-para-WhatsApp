from pytubefix import Search, YouTube
from pytubefix.cli import on_progress
import os
import asyncio
import uuid

ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
carpeta_audios = os.path.join(ruta_proyecto, "audios")
carpeta_videos = os.path.join(ruta_proyecto, "videos")

def _formatear_duracion(segundos):
    if not isinstance(segundos, int) or segundos < 0:
        return "desconocida"

    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    if horas:
        return f"{horas}:{minutos:02d}:{segundos:02d}"
    return f"{minutos}:{segundos:02d}"

def buscar_video(query):
    """Return serializable video candidates from the first search page."""
    results = Search(query)
    videos = []
    for video in results.videos:
        duracion_segundos = video.length
        candidato = {
            "titulo": video.title,
            "url": video.watch_url,
            "duracion_segundos": duracion_segundos,
            "duracion": _formatear_duracion(duracion_segundos),
        }
        videos.append(candidato)
        print(f'Titulo: {candidato["titulo"]}')
        print(f'URL: {candidato["url"]}')
        print(f'Duración: {candidato["duracion"]}')
    print('---')
    return videos

async def descargar_audio(url: str) -> str:
    """
    Corre la descarga (bloqueante) en un hilo aparte del pool de
    threads de asyncio, así el event loop principal queda libre para
    seguir atendiendo otros webhooks/mensajes mientras se descarga.
    """
    return await asyncio.to_thread(_descargar_audio_sync, url)

def _descargar_audio_sync(url: str) -> str:
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)
 
    ys = yt.streams.get_audio_only()
    extension = os.path.splitext(ys.default_filename)[1]
    nombre_archivo = f"youtube_audio_{uuid.uuid4().hex}{extension}"
    ruta_archivo = ys.download(
        output_path=carpeta_audios,
        filename=nombre_archivo,
    )
    if ruta_archivo is None:
        raise RuntimeError("Pytubefix no devolvió la ruta del audio descargado.")

    print(f"Audio descargado en: {ruta_archivo}")
    return ruta_archivo

async def descargar_video(url: str) -> str:
    """
    Corre la descarga (bloqueante) en un hilo aparte del pool de
    threads de asyncio, así el event loop principal queda libre para
    seguir atendiendo otros webhooks/mensajes mientras se descarga.
    """
    return await asyncio.to_thread(_descargar_video_sync, url)

def _descargar_video_sync(url):
    yt = YouTube(url, on_progress_callback=on_progress)
    print(yt.title)

    ys = yt.streams.get_by_resolution("720p")
    extension = os.path.splitext(ys.default_filename)[1]
    nombre_archivo = f"youtube_video_{uuid.uuid4().hex}{extension}"
    ruta_archivo = ys.download(
        output_path=carpeta_videos,
        filename=nombre_archivo,
    )
    if ruta_archivo is None:
        raise RuntimeError("Pytubefix no devolvió la ruta del video descargado.")

    print(f'Video descargado en la carpeta: {ruta_archivo}')
    return ruta_archivo

# video = descargar_video('https://youtube.com/watch?v=dvgZkm1xWPE')
# print(video)
# audio = asyncio.run(descargar_audio('https://youtube.com/watch?v=dvgZkm1xWPE'))
# print(audio)