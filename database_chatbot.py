import pymongo
from config import settings
import time
from datetime import datetime, timedelta

client = pymongo.MongoClient(settings.MONGODB_URL, int(settings.MONGODB_PORT))

db = client.openWA

def guardar_memoria(remitente: str, id_remitente: str, memoria: str):
    from datetime import datetime
    doc = {
        "remitente": remitente,
        "id_remitente": id_remitente,
        "memoria": memoria,
        "fecha": datetime.now()
    }
    insercion = db["memoria_modelo"].insert_one(doc)
    return {"guardado": bool(insercion.inserted_id)}

def consultar_memorias(remitente: str, id_remitente: str):
    memorias = db["memoria_modelo"].find({"remitente": remitente, "id_remitente": id_remitente}).sort("fecha", -1).limit(20)
    return [{"memoria": m["memoria"], "fecha": str(m["fecha"])} for m in memorias]

def guardar_mensaje(id_chat, documento):
    insercion = db["historial_mensajes_" + id_chat].insert_one(documento)
    if insercion.inserted_id:
        return {"estado_guardado": True, "data": insercion.inserted_id}
    else:
        return {"estado_guardado": False, "data": "Error al guardar"}

def consultar_media_mensaje_citado(id_chat, id_mensaje):
    documento = db["historial_mensajes_" + id_chat].find_one({"id": id_mensaje})
    return documento.get("media") if documento else None
        
def consultar_mensajes(id_chat, limite=10):
    """
    Se excluye el campo 'media' con una proyección de Mongo: ese
    campo guarda el base64 completo de imágenes/videos/documentos
    (lo usa consultar_media_mensaje_citado), pero para armar el
    contexto de conversación no lo necesitamos, y meterlo ahí infla
    el prompt del modelo de forma masiva sin ningún beneficio.
    """
    busqueda = db["historial_mensajes_" + id_chat].find(
        {},
        {"media": 0}
    ).sort("timestamp", -1).limit(limite)
    mensajes = []
    for documento in busqueda:
        mensajes.append(documento)
    return mensajes


def consultar_usuarios_grupo(id_chat):
    busqueda = db["miembros_grupo_" + id_chat].find()
    usuarios = []
    for documento in busqueda:
        usuarios.append(documento)
    return usuarios

def _detectar_tipo_timestamp(nombre_coleccion):
    """
    Mira un documento de muestra para saber cómo está guardado el
    campo 'timestamp': como datetime real de Mongo, como número
    (epoch en segundos o milisegundos), o como string. Devuelve uno
    de: 'datetime', 'epoch_s', 'epoch_ms', 'string', o None si no hay
    documentos o no tiene el campo.
    """
    doc = db[nombre_coleccion].find_one({"timestamp": {"$exists": True}})
    if not doc:
        return None
 
    valor = doc["timestamp"]
 
    if isinstance(valor, datetime):
        return "datetime"
    if isinstance(valor, (int, float)):
        # Un epoch en milisegundos tiene ~13 dígitos hoy en día;
        # en segundos, ~10 dígitos. Umbral simple para distinguir.
        return "epoch_ms" if valor > 10**12 else "epoch_s"
    if isinstance(valor, str):
        return "string"
    return None
 
 
def limpiar_mensajes_antiguos(horas: int = 24):
    """
    Elimina, de TODAS las colecciones 'historial_mensajes_<chat_id>',
    los mensajes con más de 'horas' de antigüedad. Detecta
    automáticamente cómo está guardado 'timestamp' en cada colección.
 
    Pensada para llamarse una vez al arrancar tu app (en el startup
    del lifespan), no en cada mensaje.
    """
    nombres_colecciones = [
        nombre for nombre in db.list_collection_names()
        if nombre.startswith("historial_mensajes_")
    ]
 
    total_eliminados = 0
 
    for nombre in nombres_colecciones:
        tipo = _detectar_tipo_timestamp(nombre)
 
        if tipo == "datetime":
            corte = datetime.now() - timedelta(hours=horas)
            filtro = {"timestamp": {"$lt": corte}}
 
        elif tipo == "epoch_s":
            corte = time.time() - horas * 3600
            filtro = {"timestamp": {"$lt": corte}}
 
        elif tipo == "epoch_ms":
            corte = (time.time() - horas * 3600) * 1000
            filtro = {"timestamp": {"$lt": corte}}
 
        elif tipo == "string":
            print(f"[WARN] '{nombre}' tiene timestamp como string, se omite la limpieza automática (revisa el formato manualmente).")
            continue
 
        else:
            # Colección vacía o sin campo 'timestamp' en ningún documento
            continue
 
        resultado = db[nombre].delete_many(filtro)
        if resultado.deleted_count > 0:
            print(f"[INFO] {resultado.deleted_count} mensajes eliminados de '{nombre}' (más de {horas}h de antigüedad).")
        total_eliminados += resultado.deleted_count
 
    print(f"[INFO] Limpieza de mensajes completada. Total eliminados: {total_eliminados}.")
    return total_eliminados

def asegurar_indices():
    db["memoria_modelo"].create_index([("remitente", 1), ("id_remitente", 1), ("fecha", -1)])
    for nombre in db.list_collection_names():
        if nombre.startswith("historial_mensajes_"):
            db[nombre].create_index([("timestamp", -1)])
            db[nombre].create_index("id")  # para consultar_media_mensaje_citado / búsquedas por id
