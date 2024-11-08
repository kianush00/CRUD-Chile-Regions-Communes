from pydantic import BaseModel


class ComunaResponse(BaseModel):
    idcomuna: int = None
    idregion: int = None
    nombre: str = None
    active: int = None
    url: str = None

    class Config:
        orm_mode = True
