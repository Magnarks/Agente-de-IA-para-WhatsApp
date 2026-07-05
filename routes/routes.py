from fastapi import APIRouter, Request, HTTPException
from config import settings
import threading
from chatIA import chat
from openWA import obtener_informacion_contacto, obtener_informacion_grupo, enviar_mensaje, enviar_mensaje_audio, reaccionar_mensaje, enviar_mensaje_imagen
from database_chatbot import guardar_mensaje, consultar_media_mensaje_citado

# Caché para deduplicar eventos de webhook (message.id)
processed_deliveries = set()
processed_lock = threading.Lock()

router = APIRouter()

def is_duplicate_webhook(payload):
    data_payload = payload.get("data", {})
    data_id = data_payload.get("id", None)
    if not data_id:
        return False

    with processed_lock:
        if data_id in processed_deliveries:
            return True

        processed_deliveries.add(data_id)
        return False

@router.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    print(f"Webhook recibido: {payload}")

    if is_duplicate_webhook(payload):
        data_payload = payload.get("data", {})
        data_id = data_payload.get("id", None)
        print("Webhook duplicado ignorado:", data_id)
        return {"status": "ignored", "reason": "duplicate"}

    evento = payload.get("event", "desconocido")
    print(f"Evento del webhook: {evento}")
    if evento == "message.received":
        data = payload.get("data", {})
        if not data:
            print("No se recibió el campo 'data' en el webhook.")
            return {"status": "error", "message": "No se recibió el campo 'data'."}
        else:
            print(f"Datos del webhook: {data}")
            chat_id = data.get("chatId", "desconocido")
            if chat_id == settings.DEFAULT_GROUP:
                guardar_mensaje(chat_id, data)
            id_remitente = data.get("from", "desconocido")
            isGroup = data.get("isGroup", False)
            id_mensaje = data.get("id", None)
            print(f"ID del remitente: {id_remitente}, ¿Es grupo?: {isGroup}")
            if(id_remitente != "desconocido"):
                info_contacto = obtener_informacion_contacto(id_remitente)
                print(f"Información del contacto: {info_contacto}")
                if isGroup:
                    info_grupo = obtener_informacion_grupo(id_remitente)
                    print(f"Información del grupo: {info_grupo}")
                    id_remitente_grupo = data.get("id", "desconocido")
                    id_remitente_grupo = id_remitente_grupo.split("_")[3]
                    print(f"ID del remitente ajustado para grupo: {id_remitente_grupo}")
                    info_contacto = obtener_informacion_contacto(id_remitente_grupo)
                    print(f"Información del contacto en grupo: {info_contacto}")
                mensaje = data.get("body", "")
                tipo_mensaje = data.get("type", "desconocido")
                remitente = info_contacto.get("name", "pushName")
                print(f"Tipo de mensaje: {tipo_mensaje}")
                print(f"Mensaje recibido: {mensaje}")
                print(f"Remitente: {remitente}")

                mensaje_citado = data.get("quotedMessage", None)

                if mensaje_citado is not None:
                    id_citado = mensaje_citado.get("id", None)
                    body_citado = mensaje_citado.get("body", "")
                else:
                    id_citado = None
                    body_citado = ""

                if tipo_mensaje == "text" and "@gemma" in mensaje:
                    print("Procesando mensaje de chat...", id_mensaje)
                    delivery_id = payload.get("deliveryId")
                    if body_citado != "" and id_citado is not None:
                        media_citado = consultar_media_mensaje_citado(chat_id, id_citado)
                        if media_citado is not None:
                            respuesta = await chat(mensaje + " " + f"'{body_citado}'", remitente, id_remitente_grupo, chat_id, media_citado, delivery_id=delivery_id)
                        else:
                            respuesta = await chat(mensaje + " " + f"'{body_citado}'", remitente, id_remitente_grupo, chat_id, delivery_id=delivery_id)                            
                    else:
                        respuesta = await chat(mensaje, remitente, id_remitente_grupo, chat_id, delivery_id=delivery_id)
                    print(f"Respuesta generada: {respuesta}")
                    if "emoji" in respuesta and id_mensaje:
                        await reaccionar_mensaje(chat_id, id_mensaje, respuesta["emoji"])
                    if respuesta.get("response") == "audio generado" and "audio_file" in respuesta:
                        await enviar_mensaje_audio(chat_id, respuesta["audio_file"])
                    elif respuesta.get("response") == "audio generado":
                        await enviar_mensaje(chat_id, "🔷 Gemma: No se pudo generar la respuesta de audio.", id_mensaje)
                    elif respuesta.get("response") == "imagen generada" and "image_file" in respuesta:
                        await enviar_mensaje_imagen(chat_id, respuesta["image_file"])
                    else:
                        await enviar_mensaje(chat_id, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                    return {
                        "status": "ok",
                        "response": respuesta
                    }                
                elif tipo_mensaje == "image" and "@gemma" in mensaje:
                    media = data.get("media", None)
                    if media is not None:
                        print("Procesando mensaje de chat...", id_mensaje)
                        respuesta = await chat(mensaje, remitente, id_remitente_grupo, chat_id, media, delivery_id=payload.get("deliveryId"))
                        print(f"Respuesta generada: {respuesta}")
                        if "emoji" in respuesta and id_mensaje:
                            await reaccionar_mensaje(chat_id, id_mensaje, respuesta["emoji"])
                        if respuesta.get("response") == "audio generado" and "audio_file" in respuesta:
                            await enviar_mensaje_audio(chat_id, respuesta["audio_file"])
                        elif respuesta.get("response") == "audio generado":
                            await enviar_mensaje(chat_id, "🔷 Gemma: No se pudo generar la respuesta de audio.", id_mensaje)
                        else:
                            await enviar_mensaje(chat_id, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                        return {
                            "status": "ok",
                            "response": respuesta
                        }
                    else:
                        return {"status": "error", "message": "No se pudo obtener los medios del mensaje."}     
                elif tipo_mensaje == "ptt" or tipo_mensaje == "audio":
                    media = data.get("media", None)
                    if media is not None:
                        print("Procesando mensaje de voz...")
                        respuesta = await chat(mensaje, remitente, id_remitente_grupo, chat_id, media, delivery_id=payload.get("deliveryId"))
                        print(f"Respuesta generada: {respuesta}")
                        if respuesta["response"] == "IGNORAR_AUDIO":
                            return {"status": "error", "message": "No se llamo a gemma en el mensaje."}
                        if "emoji" in respuesta and id_mensaje:
                            await reaccionar_mensaje(chat_id, id_mensaje, respuesta["emoji"])
                        if respuesta["response"] != "No se pudo obtener el tipo de archivo.":
                            await enviar_mensaje(chat_id, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                    else:
                        return {"status": "error", "message": "No se pudo obtener los medios del mensaje."}                    
            else:
                print("No se pudo obtener el ID del remitente.", id_remitente)
                return {"status": "error", "message": "No se pudo obtener el ID del remitente."}
    elif evento == "message.sent":
        data = payload.get("data", {})
        if not data:
            print("No se recibió el campo 'data' en el webhook.")
            return {"status": "error", "message": "No se recibió el campo 'data'."}
        else:
            print(f"Datos del webhook: {data}")
            chat_id = data.get("chatId", "desconocido")
            if chat_id == settings.DEFAULT_GROUP:
                guardar_mensaje(chat_id, data)
            id_remitente = data.get("from", "desconocido")
            id_destinatario = data.get("to", "desconocido")
            isGroup = data.get("isGroup", False)
            id_mensaje = data.get("id", None)
            print(f"ID del remitente: {id_remitente}, ¿Es grupo?: {isGroup}")
            if(id_remitente != "desconocido" and id_destinatario != "desconocido"):
                info_contacto = obtener_informacion_contacto(id_remitente)
                info_contacto_destinatario = obtener_informacion_contacto(id_destinatario)
                print(f"Información del contacto: {info_contacto}")
                print(f" información del destinatario: {info_contacto_destinatario}")
                if isGroup:
                    info_grupo = obtener_informacion_grupo(id_destinatario)
                    print(f"Información del grupo: {info_grupo}")
                    id_remitente_grupo = data.get("id", "desconocido")
                    id_remitente_grupo = id_remitente_grupo.split("_")[3]
                    print(f"ID del remitente ajustado para grupo: {id_remitente_grupo}")
                    info_contacto = obtener_informacion_contacto(id_remitente_grupo)
                    print(f"Información del contacto en grupo: {info_contacto}")
                mensaje = data.get("body", "")
                tipo_mensaje = data.get("type", "desconocido")
                remitente = info_contacto.get("name", "pushName")
                destinatario = info_contacto_destinatario.get("name", "pushName")
                print(f"Tipo de mensaje: {tipo_mensaje}")
                print(f"Mensaje recibido: {mensaje}")
                print(f"Remitente: {remitente}")
                print(f"Destinatario: {destinatario}")

                mensaje_citado = data.get("quotedMessage", None)

                if mensaje_citado is not None:
                    id_citado = mensaje_citado.get("id", None)
                    body_citado = mensaje_citado.get("body", "")
                else:
                    id_citado = None
                    body_citado = ""

                if tipo_mensaje == "text" and "@gemma" in mensaje:
                    print("Procesando mensaje de chat...", id_mensaje)
                    delivery_id = payload.get("deliveryId")
                    if body_citado != "" and id_citado is not None:
                        media_citado = consultar_media_mensaje_citado(chat_id, id_citado)
                        if media_citado is not None:
                            respuesta = await chat(mensaje + " " + f"'{body_citado}'", destinatario, id_remitente_grupo, chat_id, media_citado, delivery_id=delivery_id)
                        else:
                            respuesta = await chat(mensaje + " " + f"'{body_citado}'", destinatario, id_remitente_grupo, chat_id, delivery_id=delivery_id)
                    else:
                        respuesta = await chat(mensaje, destinatario, id_remitente_grupo, chat_id, delivery_id=delivery_id)
                    print(f"Respuesta generada: {respuesta}")
                    if "emoji" in respuesta and id_mensaje:
                        await reaccionar_mensaje(id_destinatario, id_mensaje, respuesta["emoji"])
                    if respuesta.get("response") == "audio generado" and "audio_file" in respuesta:
                        await enviar_mensaje_audio(id_destinatario, respuesta["audio_file"])
                    elif respuesta.get("response") == "audio generado":
                        await enviar_mensaje(id_destinatario, "🔷 Gemma: No se pudo generar la respuesta de audio.", id_mensaje)
                    elif respuesta.get("response") == "imagen generada" and "image_file" in respuesta:
                        await enviar_mensaje_imagen(chat_id, respuesta["image_file"])
                    else:
                        await enviar_mensaje(id_destinatario, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                    return {
                        "status": "ok",
                        "response": respuesta
                    }
                elif tipo_mensaje == "image" and "@gemma" in mensaje:
                    media = data.get("media", None)
                    if media is not None:
                        print("Procesando mensaje de chat...", id_mensaje)
                        respuesta = await chat(mensaje, remitente, chat_id, media, delivery_id=payload.get("deliveryId"))
                        print(f"Respuesta generada: {respuesta}")
                        if "emoji" in respuesta and id_mensaje:
                            await reaccionar_mensaje(id_destinatario, id_mensaje, respuesta["emoji"])
                        if respuesta.get("response") == "audio generado" and "audio_file" in respuesta:
                            await enviar_mensaje_audio(chat_id, respuesta["audio_file"])
                        elif respuesta.get("response") == "audio generado":
                            await enviar_mensaje(chat_id, "🔷 Gemma: No se pudo generar la respuesta de audio.", id_mensaje)
                        else:
                            await enviar_mensaje(chat_id, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                        return {
                            "status": "ok",
                            "response": respuesta
                        }
                    else:
                        return {"status": "error", "message": "No se pudo obtener los medios del mensaje."}    
                elif tipo_mensaje == "ptt" or tipo_mensaje == "audio":
                    media = data.get("media", None)
                    if media is not None:
                        print("Procesando mensaje de voz...")
                        respuesta = await chat(mensaje, remitente, chat_id, media, delivery_id=payload.get("deliveryId"))
                        print(f"Respuesta generada: {respuesta}")
                        if respuesta["response"] == "IGNORAR_AUDIO":
                            return {"status": "error", "message": "No se llamo a gemma en el mensaje."}
                        if "emoji" in respuesta and id_mensaje:
                            await reaccionar_mensaje(chat_id, id_mensaje, respuesta["emoji"])
                        if respuesta["response"] != "No se pudo obtener el tipo de archivo.":
                            await enviar_mensaje(chat_id, "🔷 Gemma: " + respuesta["response"], id_mensaje)
                    else:
                        return {"status": "error", "message": "No se pudo obtener los medios del mensaje."}    
            else:
                print("No se pudo obtener el ID del destinatario.", id_destinatario)
                return {"status": "error", "message": "No se pudo obtener el ID del destinatario."}
    else:
       return {"status": "error", "message": "No se pudo recibir evento."} 

