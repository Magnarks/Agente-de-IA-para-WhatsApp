import yt_dlp
from yt_dlp.networking.impersonate import ImpersonateTarget
import os
from datetime import datetime
import time

ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
carpeta_videos = os.path.join(ruta_proyecto, "videos")

# url = "https://www.tiktok.com/@edwinmanuelalcala/video/7701873281879559431?is_from_webapp=1&sender_device=pc"

def generar_nombre_video(custom_name=None):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if custom_name:
        return f"{custom_name}_{timestamp}.mp4"
    return f"tiktok_{timestamp}.mp4"

def descargar_post_tiktok(url, intentos=3):

    nombre_video = generar_nombre_video()

    ydl_opts = {
        'verbose': True,
        'outtmpl': os.path.join(carpeta_videos, nombre_video),
        'noplaylist': True,
        'cookiesfrombrowser': ('chrome',),
        'impersonate': ImpersonateTarget.from_str('chrome'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.8103.50 Safari/537.36'
        }
    }

    for i in range(1, intentos + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                texto = info.get('description')
                autor = info.get('uploader')
                likes = info.get('like_count')
                print(autor, likes, texto)
                print(f"\nVideo descargado exitosamente: {os.path.join(carpeta_videos, nombre_video)}")
                return {"archivo_file": os.path.join(carpeta_videos, nombre_video), "caption": f"Descripción: {texto}\nAutor: {autor}\nLikes: {likes}"}
        except yt_dlp.utils.DownloadError as e:
            print(f"Intento {i}/{intentos} falló: {e}")
            if i < intentos:
                print(f"Reintentando en {3 * i} segundos...")
                ydl_opts['cookiesfrombrowser'] = None
                time.sleep(3 * i)
            if i == intentos:
                print(f"Error al descargar el video después de {intentos} intentos: {e}")
        except Exception as e:
            print(f"Error al descargar el video: {e}")
    return None

# descargar_post_tiktok(url)