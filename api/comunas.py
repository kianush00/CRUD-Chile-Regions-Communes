import fastapi
from fastapi import Depends, Form, UploadFile, File
from database.database import Session
from database.models import ComunaTabla
from models.response.default import DefaultResponse
from api.regiones import nombre_de_comuna_es_repetido, buscar_region, imagen_por_defecto, eliminar_imagen, \
    url_imagen_comuna, validar_imagen_comuna
from fastapi.responses import FileResponse
import os.path

router = fastapi.APIRouter()


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


@router.get(
    path="/comuna/{id_comuna}",
    name="Obtener comuna",
    description="Obtiene una comuna por su id")
def get_comuna(id_comuna: int, db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    comuna = buscar_comuna(id_comuna, db)

    if comuna is None:
        return respuesta_comuna_no_encontrada(response)
    else:
        region = buscar_region(comuna.idregion, db)
        comuna.region = region.nombre
        return {"mensaje": "Comuna obtenida", "comuna": comuna}


@router.get(
    path="/comuna/{id_comuna}/imagen",
    name="Obtener imagen de comuna",
    description="Obtiene el archivo imagen de la comuna")
def get_comuna_imagen(id_comuna: int, db: Session = Depends(get_db)):
    comuna = buscar_comuna(id_comuna, db)

    if comuna is not None and comuna.url is not None:
        imagen_url = url_imagen_comuna(id_comuna, comuna.url)
        if os.path.exists(imagen_url):
            return FileResponse(imagen_url, media_type="image/png")
        else:
            eliminar_url_comuna(comuna, db)

    return imagen_por_defecto()


@router.post(
    path="/comuna",
    name="Guardar comuna",
    description="Guarda una comuna a través de un formulario")
def save_comuna(idcomuna: int | None = Form(None), idregion: int = Form(...), nombre: str = Form(...),
                active: int | None = Form(None), imagen: UploadFile | None = File(None),
                db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    comuna_a_guardar = ComunaTabla()

    if nombre_de_comuna_es_repetido(nombre, db):
        return respuesta_comuna_registrada(response)
    guardar_comuna(comuna_a_guardar, db, idcomuna, idregion, nombre, active, imagen)

    response.respuesta = "Comuna guardada"
    return response


@router.put(
    path="/comuna/{id_comuna_path}",
    name="Actualizar comuna",
    description="Actualiza una comuna a través de un formulario")
def put_comuna(id_comuna_path: int, idcomuna: int | None = Form(None), idregion: int | None = Form(None),
               nombre: str | None = Form(None), active: int | None = Form(None),
               imagen: UploadFile | None = File(None), db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    registro_a_actualizar = buscar_comuna(id_comuna_path, db)

    if registro_a_actualizar is None:
        return respuesta_comuna_no_encontrada(response)
    else:
        if nombre is not None:
            if nombre_de_comuna_es_repetido(nombre, db):
                return respuesta_comuna_registrada(response)
        guardar_comuna(registro_a_actualizar, db, idcomuna, idregion, nombre, active, imagen)

        response.respuesta = "Comuna actualizada"
        return response


@router.delete(
    path="/comuna/{id_comuna}",
    name="Eliminar comuna",
    description="Elimina una comuna por su id")
def delete_comuna(id_comuna: int, db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    registro_a_eliminar = buscar_comuna(id_comuna, db)

    if registro_a_eliminar is None:
        return respuesta_comuna_no_encontrada(response)
    else:
        try:
            eliminar_comuna(registro_a_eliminar, db)
            response.respuesta = "ok"
            response.mensaje = "Comuna ha sido eliminada"
        except:
            response.respuesta = "error"
            response.mensaje = "Comuna no puede ser eliminada"
        return response


def respuesta_comuna_no_encontrada(response: DefaultResponse):
    response.respuesta = "error"
    response.mensaje = "Comuna no encontrada"
    return response


def respuesta_comuna_registrada(response: DefaultResponse):
    response.respuesta = "error"
    response.mensaje = "Comuna ya ha sido registrada anteriormente"
    return response


def buscar_comuna(id_comuna: int, db: Session):
    return db.query(ComunaTabla).filter(ComunaTabla.idcomuna == id_comuna).first()


def eliminar_url_comuna(comuna: ComunaTabla, db: Session):
    comuna.url = None
    db.add(comuna)
    db.commit()


def eliminar_comuna(comuna: ComunaTabla, db: Session):
    db.delete(comuna)
    db.commit()
    if comuna.url is not None:
        imagen_url = url_imagen_comuna(comuna.idcomuna, comuna.url)
        eliminar_imagen(imagen_url)


def guardar_comuna(comuna: ComunaTabla, db: Session, idcomuna: int | None, idregion: int | None, nombre: str | None,
                   active: int | None, imagen: UploadFile | None):
    if nombre is not None:
        comuna.nombre = nombre.title()
    if idregion is not None:
        comuna.idregion = idregion
    if active is not None:
        comuna.active = active
    if idcomuna is not None:
        comuna.idcomuna = idcomuna
    db.add(comuna)
    db.flush()
    validar_imagen_comuna(imagen, comuna, db)
    db.commit()
