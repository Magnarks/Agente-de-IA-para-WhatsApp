import pymongo
from config import settings

client = pymongo.MongoClient(settings.MONGODB_URL, int(settings.MONGODB_PORT))

db = client.openWA

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
        return documento["media"]
