from pydantic import BaseModel
from typing import List


class RegionResponse(BaseModel):
    idregion: int = None
    nombre: str = None
    active: int = None
    url: str = None


class RegionComunasResponse(BaseModel):
    region: str = None
    comunas: List[str] = []
