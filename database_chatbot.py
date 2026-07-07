import pymongo
from config import settings

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

def guardar_mensaje(id_chat, json):
    insercion = db["historial_mensajes_" + id_chat].insert_one(json)
    if insercion.inserted_id:
        return {"estado_guardado": True, "data": insercion.inserted_id}
    else:
        return {"estado_guardado": False, "data": "Error al guardar"}

def consultar_media_mensaje_citado(id_chat, id_mensaje):
    busqueda = db["historial_mensajes_" + id_chat].find(
        {"id": id_mensaje}
    )
    for documento in busqueda:
        if "media" in documento:
            return documento["media"]
        else: 
            return None
        
def consultar_mensajes(id_chat, limite=10):
    busqueda = db["historial_mensajes_" + id_chat].find().sort("timestamp", -1).limit(limite)
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
