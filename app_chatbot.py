from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.routes import router
from chatIA import chat
from openWA import registrar_webhook_openwa, enviar_mensaje, obtener_informacion_grupo, obtener_informacion_contacto
import uvicorn
from config import settings

app = FastAPI(
    title="Chatbot API",
    description="API para el chatbot de Whatsapp",
    version="1.0.0"
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

estado_conexion_openwa = False

lista_participantes = []

@app.on_event("startup")
async def startup_event():
    # iniciar el chatbot
    if settings.DEFAULT_GROUP != "":
        info_grupo = obtener_informacion_grupo(settings.DEFAULT_GROUP)
        participantes = info_grupo.get("participants", "")
        if participantes != "":
            for participante in participantes:
                datos_participante = obtener_informacion_contacto(participante["id"])
                lista_participantes.append(datos_participante)
    if len(lista_participantes) > 0:
        respuesta = await chat(f"iniciando... en tu respuesta si es posible di la fecha actual y si encuentras participantes del grupo saludalos usando su pushName. Los participantes están en esta lista de Python: {lista_participantes}", "administrador", "")
    else:
        respuesta = await chat("iniciando... en tu respuesta si es posible di la fecha actual.", "administrador", "")
    print(f"Respuesta del chatbot al iniciar: {respuesta}")
    if respuesta.get("error") == 'Connection error.':
        print('No se inicializo modelo de IA')
    else:
        if len(lista_participantes) > 0:
            await enviar_mensaje(settings.DEFAULT_GROUP, "🔷 Gemma: " + respuesta["response"])
    global estado_conexion_openwa
    if not estado_conexion_openwa:
        estado_conexion_openwa = registrar_webhook_openwa(estado_conexion_openwa)

if __name__ == "__main__":
    uvicorn.run("app_chatbot:app", port=8000, reload=True)