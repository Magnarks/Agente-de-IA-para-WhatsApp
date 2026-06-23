from pydantic import BaseModel

class Consulta(BaseModel):
    mensaje: str
    remitente: str

