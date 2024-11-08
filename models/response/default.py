from pydantic import BaseModel


class DefaultResponse(BaseModel):
    respuesta: str = None
    mensaje: str = None
