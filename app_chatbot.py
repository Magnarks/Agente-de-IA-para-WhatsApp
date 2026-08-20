from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from routes.routes import router
from chatIA import chat
from openWA import registrar_webhook_openwa, enviar_mensaje, obtener_informacion_grupo, obtener_informacion_contacto, iniciar_sesion_openwa, detener_sesion_openwa, estado_sesion_openwa
from database_chatbot import consultar_usuarios_grupo
import uvicorn
from config import settings
import asyncio

estado_conexion_openwa = False

lista_participantes = []

historial_conversacion = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    MAX_INTENTOS = 10
    ESPERA_SEGUNDOS = 3

    # iniciar el chatbot
    sesion_iniciada = await iniciar_sesion_openwa()
    sesion_realizada = None  # valor por defecto seguro
    if sesion_iniciada:
        for intento in range(1, MAX_INTENTOS + 1):
            try:
                sesion_realizada = await estado_sesion_openwa()
                if sesion_realizada == "ready":
                    print(f"Sesión de OpenWA lista. Estado: {sesion_realizada}")
                    break
                print(f"Estado actual: {sesion_realizada}. Reintentando... ({intento}/{MAX_INTENTOS})")
                await asyncio.sleep(ESPERA_SEGUNDOS)
            except Exception as e:
                print(f"Error al verificar el estado: {e}")
                await asyncio.sleep(ESPERA_SEGUNDOS)
        else:
            print("No se pudo establecer la sesión de OpenWA tras varios intentos.")
    else:
        print("No se pudo iniciar sesión en OpenWA.")

    # iniciar webhook openWA
    global estado_conexion_openwa
    if not estado_conexion_openwa:
        if sesion_realizada == "ready":
            estado_conexion_openwa = registrar_webhook_openwa(estado_conexion_openwa)
        else:
            print("No se pudo iniciar sesión en OpenWA. Verifica que la sesión esté activa.")

    if settings.DEFAULT_GROUP.split(",")[0] != "" and sesion_realizada == "ready":
        participantes = consultar_usuarios_grupo(settings.DEFAULT_GROUP.split(",")[0])
        if participantes != "":
            lista_participantes = participantes
            print(f"Participantes del grupo {settings.DEFAULT_GROUP.split(',')[0]}: {lista_participantes}")
    if len(lista_participantes) > 0 and sesion_realizada == "ready":
        respuesta = await chat(f"iniciando... en tu respuesta si es posible di la fecha actual y si encuentras participantes del grupo saludalos usando su lid (esto hace que se mencionen como un mensaje de WhatsApp, IMPORTANTE NUNCA INVENTES O MODIFIQUES EL VALOR ESTE YA ESTA CARGADO DESDE BASE DE DATOS) y según la hora en el saludo menciona buenos días, buenas tardes o buenas noches. Los participantes están en esta lista de Python: {lista_participantes}. también saluda a @clau", "administrador", "", "")
    else:
        respuesta = await chat("iniciando... en tu respuesta si es posible di la fecha actual.", "administrador", "", "")
    print(f"Respuesta del chatbot al iniciar: {respuesta}")
    if respuesta.get("error") == 'Connection error.':
        print('No se inicializo modelo de IA')
    else:
        if len(lista_participantes) > 0 and sesion_realizada == "ready":
            await enviar_mensaje(settings.DEFAULT_GROUP.split(",")[0], settings.PREFIJO_MENSAJE + " " + respuesta["response"])
            #pass
        else:
            print("No se pudo enviar el mensaje. Verifica que la sesión esté activa.")
        # El yield marca la transición entre startup y shutdown
    yield
    # SHUTDOWN - código después del yield (aquí limpieza si es necesaria)
    print("Cerrando aplicación...")
    if estado_conexion_openwa and sesion_realizada == "ready":
        if len(lista_participantes) > 0 and sesion_realizada == "ready":
            respuesta = await chat(f"Apagando... si encuentras participantes del grupo despídete usando su lid (esto hace que se mencionen como un mensaje de WhatsApp, IMPORTANTE NUNCA INVENTES O MODIFIQUES EL VALOR ESTE YA ESTA CARGADO DESDE BASE DE DATOS) y según la hora en la que se encuentren menciona buenos días, buenas tardes o buenas noches. Los participantes están en esta lista de Python: {lista_participantes}, también despidete de @clau", "administrador", "", "")
        else:
            respuesta = await chat("Apagando... genera una respuesta de despedida.", "administrador", "", "")
        if respuesta.get("error") == 'Connection error.':
            await enviar_mensaje(settings.DEFAULT_GROUP.split(",")[0], settings.PREFIJO_MENSAJE + " Gemma Apagada...")  
            await asyncio.sleep(ESPERA_SEGUNDOS)
            await detener_sesion_openwa()
            estado_conexion_openwa = False
            print("Sesión de OpenWA detenida.")  
        else:
            if len(lista_participantes) > 0 and sesion_realizada == "ready":
                await enviar_mensaje(settings.DEFAULT_GROUP.split(",")[0], settings.PREFIJO_MENSAJE + " " + respuesta["response"])
                await asyncio.sleep(ESPERA_SEGUNDOS)
                await detener_sesion_openwa()
                estado_conexion_openwa = False
                print("Sesión de OpenWA detenida.")

app = FastAPI(
    title="Chatbot API",
    description="API para el chatbot de Whatsapp",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

app.mount("/audios", StaticFiles(directory=settings.RUTA_AUDIOS), name="audios")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app_chatbot:app", port=8000, reload=True)