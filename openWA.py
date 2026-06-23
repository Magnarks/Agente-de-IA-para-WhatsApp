import requests
import json
from config import settings
import base64

def _get_registered_webhooks():
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/webhooks"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"No se pudo obtener la lista de webhooks: {e}")
        return []

def registrar_webhook_openwa(estado_conexion_openwa):
    if estado_conexion_openwa:
        print("El webhook ya está registrado.")
        return estado_conexion_openwa

    # Verificar si ya existe un webhook igual para evitar registros duplicados.
    webhooks = _get_registered_webhooks()
    if isinstance(webhooks, list):
        for hook in webhooks:
            if hook.get("url") == settings.OPENWA_WEBHOOK_URL:
                print("El webhook ya está registrado en OpenWA.")
                return True

    # URL del API
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/webhooks"
    # Encabezados de la petición
    headers = {
        "Accept": "*/*", # Para solicitar la respuesta en formato JSON
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}", # Token de autenticación
    }
    parametros = {
        "url": settings.OPENWA_WEBHOOK_URL,
        "events":  ["message.sent","message.received","session.connected", "session.disconnected"],
        "secret": "215f628d-210d-47ed-9f5a-44a7e2781f01",
        "headers": {
            "X-Custom-Header": "value"
        },
        "retryCount": 3
    }

    try:
        # Realizar la solicitud
        response = requests.post(api_url, headers=headers, json=parametros)
        # Verificar la respuesta
        if response.status_code == 200 or response.status_code == 201:
            estado_conexion_openwa = True
            print("Webhook registrado exitosamente.", estado_conexion_openwa)
            return estado_conexion_openwa
        else:
            respuesta = json.loads(response.text)
            print("Error al registrar el webhook.")
            print(respuesta)
            return estado_conexion_openwa
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return estado_conexion_openwa
    
def obtener_informacion_contacto(contact_id):
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/contacts/{contact_id}"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error al obtener la información del contacto.")
            return {"error": "No se pudo obtener la información del contacto."}
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return {"error": "Error en la solicitud."}
    
def obtener_informacion_grupo(group_id):
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/groups/{group_id}"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print("Error al obtener la información del grupo.")
            return {"error": "No se pudo obtener la información del grupo."}
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return {"error": "Error en la solicitud."}
    
async def obtener_historial_mensajes(chat_id: str, limit: int, offset: int = 1):
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    parametros = {
        "chatId": chat_id,
        "limit": limit,
        "offset": offset
    }
    try:
        response = requests.get(api_url, headers=headers, params=parametros)
        if response.status_code == 200:
            print(response.json())
            return response.json()
        else:
            print("Error al obtener la información del grupo.")
            return {"error": "No se pudo obtener la información del grupo."}
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return {"error": "Error en la solicitud."}
    
async def enviar_mensaje(contact_id, mensaje, id_mensaje = None):

    if id_mensaje is not None:
        api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/reply"
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
        }
        payload = {
            "chatId": contact_id,
            "quotedMessageId": id_mensaje,
            "text": mensaje
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Mensaje enviado exitosamente.")
                return True
            else:
                print("Error al enviar el mensaje.")
                return False
        except requests.exceptions.Timeout:
            print("Error: La solicitud ha excedido el tiempo de espera.")
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}")
            return False
    else:
        api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/send-text"
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
        }
        payload = {
            "chatId": contact_id,
            "text": mensaje
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Mensaje enviado exitosamente.")
                return True
            else:
                print("Error al enviar el mensaje.")
                return False
        except requests.exceptions.Timeout:
            print("Error: La solicitud ha excedido el tiempo de espera.")
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}")
            return False
    
async def enviar_mensaje_audio(contact_id, audio_file_path):

    print(f"Preparando para enviar el mensaje de audio: {audio_file_path} al contacto: {contact_id}")

    with open(audio_file_path, "rb") as archivo_ogg:
        datos_binarios = archivo_ogg.read()
        
        # Convierte a Base64
        audio_base64 = base64.b64encode(datos_binarios)
        
        # Convierte el resultado de bytes a string (opcional)
        audio_string = audio_base64.decode('utf-8')

    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/send-audio"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    payload = {
        "chatId": contact_id,
        "base64": audio_string,
        "mimetype": "audio/ogg"
    }
    # payload = {
    #     "chatId": contact_id,
    #     "audio": {
    #         "url": f"http://127.0.0.1:8000/audios/respuesta_audio_{audio_file_path.split('_')[-1]}"
    #     },
    #     "ptt": True
    # }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200 or response.status_code == 201:
            print("Mensaje de audio enviado exitosamente.")
            return True
        else:
            print("Error al enviar el mensaje de audio.", response.status_code, response.text)
            return False
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return False
    
async def reaccionar_mensaje(contact_id, id_mensaje, emoji="👍"):

    if id_mensaje is not None:
        api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/react"
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
        }
        payload = {
            "chatId": contact_id,
            "messageId": id_mensaje,
            "emoji": emoji
        }
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Reacción enviada exitosamente.")
                return True
            else:
                print("Error al enviar reacción el mensaje.", response.status_code, response.text)
                return False
        except requests.exceptions.Timeout:
            print("Error: La solicitud ha excedido el tiempo de espera.")
        except requests.exceptions.RequestException as e:
            print(f"Error en la solicitud: {e}")
            return False
    else:
        print("No se envio id_mensaje")
        return False