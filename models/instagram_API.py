import instaloader
import glob
import os
from config import settings

ruta_proyecto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
carpeta_videos = os.path.join(ruta_proyecto, "videos")

# Inicializar Instaloader
loader = instaloader.Instaloader(dirname_pattern=carpeta_videos)

loader.load_session_from_file(settings.INSTAGRAM_SESSION)

url = "https://www.instagram.com/reel/DfN13lmifPW/?utm_source=ig_web_copy_link&psln=NTc4MTIwNjQ2YQ=="

def descargar_post_instagram(url):
    try:
        if "/reel/" in url:
            shortcode = url.split("/reel/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        elif "/p/" in url:
            shortcode = url.split("/p/", 1)[1].split("/", 1)[0].split("?", 1)[0]
        else:
            raise ValueError("La URL debe ser de un reel o una publicación de Instagram.")

        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        target = "reel_descargado"
        nombre_base = loader.format_filename(post, target=target)
        ruta_base = os.path.join(carpeta_videos, nombre_base)
        loader.download_post(post, target=target)

        if post.is_video:
            ruta_archivo = f"{ruta_base}.mp4"
        else:
            extensiones_imagen = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
            rutas_imagen = [
                ruta
                for ruta in glob.glob(f"{ruta_base}.*")
                if os.path.splitext(ruta)[1].lower() in extensiones_imagen
            ]
            if not rutas_imagen:
                raise FileNotFoundError(f"No se encontró la imagen descargada para {post}.")
            ruta_archivo = rutas_imagen[0]

        if not os.path.isfile(ruta_archivo):
            raise FileNotFoundError(f"No se encontró el archivo descargado: {ruta_archivo}")

        print("¡Publicación descargada con éxito!")
        return ruta_archivo
    except Exception as e:
        print(f"Error al descargar: {e}")
        return None

if __name__ == "__main__":
    ruta_archivo = descargar_post_instagram(url)
    if ruta_archivo:
        print(f"Ruta del archivo: {ruta_archivo}")
