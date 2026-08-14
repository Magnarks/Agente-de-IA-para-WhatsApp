import os
import MemePy
import base64

ruta_actual = os.path.dirname(os.path.abspath(__file__))
carpeta_imagenes = os.path.join(ruta_actual, "imagenes")

def generar_meme_guardado(plantilla, texto):
    meme = MemePy.MemeGenerator.save_meme_to_disk(plantilla, carpeta_imagenes, texto)
    return meme

def generar_meme_image(plantilla, texto):
    meme = MemePy.MemeGenerator.get_meme_image(plantilla, texto)
    return meme

def generar_meme_bytes(plantilla, texto):
    meme = MemePy.MemeGenerator.get_meme_image_bytes(plantilla, texto)
    return meme


# imagen = generar_meme_bytes("MeAlsoMe", ["Probando este código", "para generar memes con IA"])

# print(f"Imagen generada: {imagen}")
# base64_imagen = base64.b64encode(imagen.getvalue()).decode('utf-8')
# print(f"Imagen en base64: {base64_imagen}")