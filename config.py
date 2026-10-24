import os
import shutil
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

ruta_actual = os.path.dirname(os.path.abspath(__file__))
carpeta_audios = os.path.join(ruta_actual, "audios")
if not os.path.exists(carpeta_audios):
    os.makedirs(carpeta_audios)
else:
    for archivo in os.listdir(carpeta_audios):
        ruta_archivo = os.path.join(carpeta_audios, archivo)
        try:
            if os.path.isfile(ruta_archivo) or os.path.islink(ruta_archivo):
                os.unlink(ruta_archivo)
            elif os.path.isdir(ruta_archivo):
                shutil.rmtree(ruta_archivo)
        except Exception as e:
            print('Error al eliminar %s. Razón: %s' % (ruta_archivo, e))

carpeta_imagenes = os.path.join(ruta_actual, "imagenes")
if not os.path.exists(carpeta_imagenes):
    os.makedirs(carpeta_imagenes)
else:
    for archivo in os.listdir(carpeta_imagenes):
        ruta_archivo = os.path.join(carpeta_imagenes, archivo)
        try:
            if os.path.isfile(ruta_archivo) or os.path.islink(ruta_archivo):
                os.unlink(ruta_archivo)
            elif os.path.isdir(ruta_archivo):
                shutil.rmtree(ruta_archivo)
        except Exception as e:
            print('Error al eliminar %s. Razón: %s' % (ruta_archivo, e))

carpeta_prompts = os.path.join(ruta_actual, "prompts")
archivo_prompts = os.path.join(carpeta_prompts, "System_Prompt_V2.md")

class Settings:
    def __init__(self):
        self.OPENAI_API_BASE_URL: str = os.getenv("OPENAI_API_BASE_URL", "http://localhost:11434/v1")
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "nokeyneeded")
        self.MODEL_NAME: str = os.getenv("MODEL_NAME", "gemma4")
        self.SYSTEM_MESSAGE = Path(archivo_prompts).read_text(encoding="utf-8")
        self.OPENWA_SESSION_ID: str = os.getenv("OPENWA_SESSION_ID", "xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        self.OPENWA_API_TOKEN: str = os.getenv("OPENWA_API_TOKEN", "dev-admin-key")
        self.OPENWA_WEBHOOK_URL: str = os.getenv("OPENWA_WEBHOOK_URL", "http://127.0.0.1:8000/webhook")
        self.OPENWA_BASE_URL: str = os.getenv("OPENWA_BASE_URL", "http://localhost:2785")
        self.OPENWA_SECRET_WEBHOOK: str = os.getenv("OPENWA_SECRET_WEBHOOK", "xxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", "localhost")
        self.MONGODB_PORT: str = os.getenv("MONGODB_PORT", 27017)
        self.DEFAULT_GROUP: str = os.getenv("DEFAULT_GROUP", "")
        self.DEFAULT_MENTIONS_GROUP: str = os.getenv("DEFAULT_MENTIONS_GROUP", "00000000000000@lid,00000000000000@lid,00000000000000@lid,00000000000000@lid")
        self.RUTA_AUDIOS: str = carpeta_audios
        self.RUTA_IMAGENES: str = carpeta_imagenes
        self.TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "tvly-xxxxx")
        self.FOOTBALLDATA_KEY: str = os.getenv("FOOTBALLDATA_KEY", "xxxxxxxxx")
        self.API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "API_FOOTBALL_KEY")
        self.VOZ_FEMENINA: str = os.getenv("VOZ_FEMENINA", "C:\\Users\\diego\\Documents\\Python\\IA\\chatbot\\voces\\voz_paisa.wav")
        self.TEXTO_VOZ_FEMENINA: str = os.getenv("TEXTO_VOZ_FEMENINA", "Papacito, ¿Que usted y yo que somos? Yo celosa y usted mio")
        self.VOZ_FEMENINA_2: str = os.getenv("VOZ_FEMENINA_2", "C:\\Users\\diego\\Documents\\Python\\IA\\chatbot\\voces\\voz_paisa_2.wav")
        self.TEXTO_VOZ_FEMENINA_2: str = os.getenv("TEXTO_VOZ_FEMENINA_2", "Saben algo que me parece demasiado curioso a mí: yo voy mucho al gimnasio y últimamente cada vez que entro al gimnasio, solo veo hombres levantando pesas y haciendo ¡Ah! ")
        self.VOZ_MASCULINA: str = os.getenv("VOZ_MASCULINA", "C:\\Users\\diego\\Documents\\Python\\IA\\chatbot\\voces\\voz_burro.wav")
        self.TEXTO_VOZ_MASCULINA: str = os.getenv("TEXTO_VOZ_MASCULINA", "Una vez un granjero me quiso cambiar por un kilo de frijoles mágicos. Eso nunca lo superé. ¡Otro día, en una fiesta, jugaron a ponerle la cola al burro conmigo y qué crees! Me picotearon las nachas. Luego gritaron todos: ¡Piñata! ¡Piñata! y que todos me agarran a palos")
        self.NVIDIA_API_KEY: str = os.getenv("NVIDIA_API_KEY", "xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        self.HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "xxx")
        self.PREFIJO_MENSAJE: str = os.getenv("PREFIJO_MENSAJE", "🔷 Gemma: ")
        self.LID_BOT: str = os.getenv("LID_BOT", "@xxxxxx")

settings = Settings()