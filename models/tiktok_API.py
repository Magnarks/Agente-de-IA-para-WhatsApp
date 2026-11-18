import yt_dlp
import os
from datetime import datetime

ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
carpeta_videos = os.path.join(ruta_proyecto, "videos")

# url = "https://vt.tiktok.com/ZSpC6A2oJ/"

def generar_nombre_video(custom_name=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if custom_name:
        return f"{custom_name}_{timestamp}.mp4"
    return f"tiktok_{timestamp}.mp4"

def descargar_post_tiktok(url):

    nombre_video = generar_nombre_video()

    ydl_opts = {
        'verbose': True, 
        'outtmpl': os.path.join(carpeta_videos, nombre_video),
        'format': 'best',
        'noplaylist': True,
        'quiet': False,
        'progress_hooks': [lambda d: print(f"Progress: {d}")],
        'cookiesfrombrowser': ('chrome',),  # Use Chrome cookies for authentication
        'extractor_args': {'tiktok': {'webpage_download': True}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            print(f"\nVideo descargado exitosamente: {os.path.join(carpeta_videos, nombre_video)}")
            return os.path.join(carpeta_videos, nombre_video)
    except yt_dlp.utils.DownloadError as e:
        print(f"Error al descargar el video: {str(e)}")
    except Exception as e:
        print(f"Error al descargar el video: {e}")

# descargar_post_tiktok(url)