import requests
import json
from config import settings
import base64
import re
from database_chatbot import consultar_usuarios_grupo

PATRON_MENCION = re.compile(r'@(\d{8,15})\b')

ALIAS_RESERVADOS = {"gemma"}
 
def construir_mapa_menciones(miembros):
    """
    A partir de la lista de miembros (la que ya te da
    consultar_usuarios_grupo), arma pares (alias, lid_numero),
    ordenados por longitud de alias descendente (para que el regex
    haga match greedy y no corte 'Nicole Vargas' como si fuera solo
    'Nicole' antes de intentar el nombre completo).
 
    Cada persona genera 2 alias posibles: su nombre completo y su
    primer nombre, así el modelo puede escribir cualquiera de los dos
    y de todas formas resuelve al lid correcto.
    """
    alias_map = []
    for m in miembros:
        lid_raw = (m.get("lid") or "").lstrip("@")
        if not lid_raw:
            continue
 
        nombre = (m.get("name") or m.get("pushName") or "").strip()
        if not nombre:
            continue
 
        primer_nombre = nombre.split()[0]
 
        for alias in {nombre, primer_nombre}:
            if alias.lower() in ALIAS_RESERVADOS:
                continue
            alias_map.append((alias, lid_raw))
 
    alias_map.sort(key=lambda par: len(par[0]), reverse=True)
    return alias_map


def reemplazar_menciones(texto: str, miembros):
    """
    Busca '@Alias' en el texto que generó el modelo y lo reemplaza por
    '@<lid_real>', tomado de la base de datos (no del texto del
    modelo). Devuelve (texto_corregido, mentions) listo para mandarle
    a la API de OpenWA.
 
    '@clau' (y cualquier alias en ALIAS_RESERVADOS) se deja intacto,
    tal cual lo escribió el modelo — sigue funcionando como
    disparador textual, no como mention real de WhatsApp.
    """
    alias_map = construir_mapa_menciones(miembros)
    mentions = []
 
    for alias, lid in alias_map:
        patron = re.compile(rf'@{re.escape(alias)}\b', re.IGNORECASE)
        if patron.search(texto):
            texto = patron.sub(f'@{lid}', texto)
            jid = f"{lid}@lid"
            if jid not in mentions:
                mentions.append(jid)
 
    return texto, mentions
 
 
# Y en enviar_mensaje, para AMBOS endpoints (reply y send-text),
# reemplaza el payload así:
 
def _payload_con_menciones(chat_id, mensaje, quoted_message_id=None):
    """
    Sustituye '@Nombre' por '@lid' real (tomado de la BD) y arma el
    payload final para OpenWA. chat_id se usa tanto para el envío
    como para buscar los miembros del grupo (son el mismo valor).
    """
    miembros = consultar_usuarios_grupo(chat_id)
    texto_final, mentions = reemplazar_menciones(mensaje, miembros)
 
    payload = {"chatId": chat_id, "text": texto_final}
    if quoted_message_id:
        payload["quotedMessageId"] = quoted_message_id
    if mentions:
        payload["mentions"] = mentions
 
    print(f"Payload a enviar: {json.dumps(payload, indent=2)}")
    return payload
 
# Uso:
#   payload = _payload_con_menciones(contact_id, mensaje, id_mensaje)
# reemplaza los payload={...} hardcodeados en ambos bloques (if/else)
# de tu función enviar_mensaje.
#
# Ventajas sobre lo que tenías:
# - Ya no depende de settings.DEFAULT_MENTIONS_GROUP (puedes eliminar
#   esa variable del .env si quieres, o dejarla sin usar).
# - Si el mensaje no menciona a nadie, 'mentions' ni siquiera se manda
#   (algunas APIs de WhatsApp son quisquillosas con arrays vacíos).
# - Funciona igual en tu chat de pruebas, porque no consulta ninguna
#   colección de Mongo — solo lee el texto que ya vas a enviar.

async def iniciar_sesion_openwa():
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/start"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.post(api_url, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            print("Sesión iniciada exitosamente.")
            return True
        else:
            if response.status_code == 400:
                print("La sesión ya está iniciada.")
                return True
            print("Error al iniciar la sesión.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return False
    
async def detener_sesion_openwa():
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/stop"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.post(api_url, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            print("Sesión detenida exitosamente.")
            return True
        else:
            if response.status_code == 400:
                print("La sesión ya está detenida.")
                return True
            print("Error al detener la sesión.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return False
    
async def estado_sesion_openwa():
    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200 or response.status_code == 201:
            print("Sesión activa.")
            respuesta = response.json()
            if respuesta.get("status") == "ready":
                print("Sesión conectada.")
                return respuesta.get("status")
            else:
                print(f"Sesión no conectada. Estado: {respuesta.get('status')}")
                return respuesta.get("status")
        else:
            if response.status_code == 400:
                print("La sesión no está activa.")
                return True
            print("Error al obtener el estado de la sesión.")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return False

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
        "events": ["message.received", "message.sent", "message.ack", "message.failed", "message.revoked", "message.reaction", "message.edited", "session.status", "session.qr", "session.authenticated", "session.disconnected", "session.reconnect_loop", "group.join", "group.leave", "group.update", "call.received", "*"],
        "secret": settings.OPENWA_SECRET_WEBHOOK,
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
        # payload = {
        #     "chatId": contact_id,
        #     "quotedMessageId": id_mensaje,
        #     "text": mensaje,
        #     # "mentions": [m.strip() for m in settings.DEFAULT_MENTIONS_GROUP.split(",")]
        # }
        payload = _payload_con_menciones(contact_id, mensaje, id_mensaje)
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Mensaje enviado exitosamente.")
                return True
            else:
                print("Error al enviar el mensaje.", response.status_code, response.text)
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
        # payload = {
        #     "chatId": contact_id,
        #     "text": mensaje,
        #     "mentions": [m.strip() for m in settings.DEFAULT_MENTIONS_GROUP.split(",")]
        # }
        payload = _payload_con_menciones(contact_id, mensaje)
        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200 or response.status_code == 201:
                print("Mensaje enviado exitosamente.")
                return True
            else:
                print("Error al enviar el mensaje.", response.status_code, response.text)
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
        "mimetype": "audio/ogg",
        "ptt": True
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
    
async def enviar_mensaje_imagen(contact_id, base64_image, mensaje=""):

    print(f"Preparando para enviar el mensaje de imagen al contacto: {contact_id}")

    # with open(image_file_path, "rb") as archivo_imagen:
    #     datos_binarios = archivo_imagen.read()
        
    #     # Convierte a Base64
    #     imagen_base64 = base64.b64encode(datos_binarios)
        
    #     # Convierte el resultado de bytes a string (opcional)
    #     imagen_string = imagen_base64.decode('utf-8')

    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/send-image"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    payload = {
        "chatId": contact_id,
        "base64": base64_image,
        "mimetype": "image/jpeg",
        "caption": mensaje
    }
    # payload = {
    #     "chatId": contact_id,
    #     "image": {
    #         "url": f"http://127.0.0.1:8000/images/respuesta_imagen_{image_file_path.split('_')[-1]}"
    #     },
    #     "ptt": True
    # }
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200 or response.status_code == 201:
            print("Mensaje de imagen enviado exitosamente.")
            return True
        else:
            print("Error al enviar el mensaje de imagen.", response.status_code, response.text)
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
    
async def enviar_encuesta(contact_id, encuesta, opciones, multiple=False):

    api_url = f"{settings.OPENWA_BASE_URL}/api/sessions/{settings.OPENWA_SESSION_ID}/messages/send-poll"
    headers = {
        "Accept": "*/*",
        "Authorization": f"Bearer {settings.OPENWA_API_TOKEN}",
    }
    payload = {
        "chatId": contact_id,
        "name": encuesta,
        "options": opciones,
        "allowMultipleAnswers": multiple
    }
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        if response.status_code == 200 or response.status_code == 201:
            print("Encuesta enviada exitosamente.")
            return True
        else:
            print("Error al enviar encuesta.", response.status_code, response.text)
            return False
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")
        return False