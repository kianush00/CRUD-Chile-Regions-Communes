import fastapi
from fastapi import Depends, Form, UploadFile, File
from database.database import Session
from database.models import RegionTabla
from database.models import ComunaTabla
from models.request.region import RegionComunasResponse
from models.response.default import DefaultResponse
from typing import List
from fastapi.responses import FileResponse
import os.path
import shutil
import json
import pandas
from pathlib import Path

router = fastapi.APIRouter()


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


@router.get(
    path="/region/{id_region}",
    name="Obtener región",
    description="Obtiene una región por su id")
def get_region(id_region: int, db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    region = buscar_region(id_region, db)

    if region is None:
        return respuesta_region_no_encontrada(response)
    else:
        return {"mensaje": "Región obtenida", "region": region}


@router.get(
    path="/region/{id_region}/comuna",
    name="Obtener región y sus comunas",
    description="Obtiene una región por su id, junto con sus comunas")
def get_region_comunas(id_region: int, limit: int = 1000, offset: int = 0, db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    region = buscar_region(id_region, db)

    if region is None:
        return respuesta_region_no_encontrada(response)
    else:
        comunas = buscar_comunas_de_region(id_region, db, limit, offset)
        return {"mensaje": "Región y comunas obtenidas", "region": region, "comunas": comunas,
                "total": count_comunas_de_region(id_region, db), "limit": limit, "offset": offset}


@router.get(
    path="/region/{id_region}/imagen",
    name="Obtener imagen de región",
    description="Obtiene el archivo imagen de la región")
def get_region_imagen(id_region: int, db: Session = Depends(get_db)):
    region = buscar_region(id_region, db)

    if region is not None and region.url is not None:
        imagen_url = url_imagen_region(id_region, region.url)
        if os.path.exists(imagen_url):
            return FileResponse(imagen_url, media_type="image/png")
        else:
            eliminar_url_region(region, db)

    return imagen_por_defecto()


@router.get(
    path="/region",
    name="Obtener regiones y sus comunas",
    description="Obtiene todas las regiones, junto con todas sus comunas")
def get_all_regiones_comunas(limit: int = 1000, offset: int = 0, db: Session = Depends(get_db)):
    respuesta = []
    regiones = buscar_regiones(db, limit, offset)

    if not regiones:
        return {"mensaje": "No hay regiones ni comunas disponibles"}

    for region in regiones:
        comunas = buscar_comunas_de_region(region.idregion, db, None, None)
        nombres_comunas: List[str] = []
        for comuna in comunas:
            nombres_comunas.append(comuna.nombre)
        respuesta.append({"region": region, "comunas": nombres_comunas})

    return {"mensaje": "Regiones y comunas obtenidas", "regiones": respuesta,
            "total": count_regiones(db), "limit": limit, "offset": offset}


@router.post(
    path="/region",
    name="Guardar región",
    description="Guarda una región a través de un formulario")
def save_region(idregion: int | None = Form(None), nombre: str = Form(...), active: int | None = Form(None),
                imagen: UploadFile | None = File(None), db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    region_a_guardar = RegionTabla()

    if nombre_de_region_es_repetido(nombre, db):
        return respuesta_region_registrada(response)
    guardar_region(region_a_guardar, db, idregion, nombre, active, imagen)

    response.respuesta = "Región guardada"
    return response


@router.post(
    path="/region/{id_region}/comuna",
    name="Guardar comunas de región",
    description="Guarda una lista de comunas para una región por su id")
def save_comunas_de_region(id_region: int, request: str = Form(...), imagenes: List[UploadFile] | None = File(None),
                           db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    region = buscar_region(id_region, db)
    comunas_repetidas: List[str] = []
    comunas: List[str] = json.loads(request)
    contador_com: int = 0

    if region is None:
        return respuesta_region_no_encontrada(response)

    comunas_repetidas, contador_com = guardar_comunas_obtiene_repetidas(comunas, comunas_repetidas, db,
                                                                        id_region, imagenes, contador_com)
    db.commit()
    return respuesta_save_comunas_de_region(comunas, comunas_repetidas)


@router.post(
    path="/region/comuna",
    name="Guardar regiones y sus comunas",
    description="Guarda una lista de regiones de un formulario, las cuales contienen listas de comunas")
def save_all_regiones_comunas_form(request: str = Form(...), imagenes_reg: List[UploadFile] | None = File(None),
                                   imagenes_com: List[UploadFile] | None = File(None), db: Session = Depends(get_db)):
    regiones_json = json.loads(request)
    regiones: List[RegionComunasResponse] = []

    for region_json in regiones_json:
        region: RegionComunasResponse = RegionComunasResponse()
        region.region = region_json["region"]
        region.comunas = region_json["comunas"]
        regiones.append(region)

    return save_all_regiones_comunas(regiones, imagenes_reg, imagenes_com, db)


@router.post(
    path="/csv/region/comuna",
    name="Guardar .csv de regiones y sus comunas",
    description="Guarda un archivo csv de regiones asociadas a comunas")
async def save_all_regiones_comunas_csv(request: UploadFile = File(...),
                                        imagenes_reg: List[UploadFile] | None = File(None),
                                        imagenes_com: List[UploadFile] | None = File(None),
                                        db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()

    # se valida el archivo .csv y se convierte a un listado de registros
    contenido = await request.read()
    if obtener_extension(request) == ".csv":
        registros = convert_bytes_to_string(contenido)
    else:
        return respuesta_archivo_invalido(response)

    regiones: List[RegionComunasResponse] = parse_csv_region_comunas_response(registros)
    return save_all_regiones_comunas(regiones, imagenes_reg, imagenes_com, db)


@router.put(
    path="/region/{id_region_path}",
    name="Actualizar región",
    description="Actualiza una región a través de un formulario")
def put_region(id_region_path: int, idregion: int | None = Form(None), nombre: str | None = Form(None),
               active: int | None = Form(None), imagen: UploadFile | None = File(None),
               db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    registro_a_actualizar = buscar_region(id_region_path, db)

    if registro_a_actualizar is None:
        return respuesta_region_no_encontrada(response)
    else:
        if nombre is not None:
            if nombre_de_region_es_repetido(nombre, db):
                return respuesta_region_registrada(response)
        guardar_region(registro_a_actualizar, db, idregion, nombre, active, imagen)

        response.respuesta = "Región actualizada"
        return response


@router.delete(
    path="/region/{id_region}",
    name="Eliminar región",
    description="Elimina una región por su id")
def delete_region(id_region: int, db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    registro_a_eliminar = buscar_region(id_region, db)

    if registro_a_eliminar is None:
        return respuesta_region_no_encontrada(response)
    else:
        try:
            eliminar_region(registro_a_eliminar, db)
            response.respuesta = "ok"
            response.mensaje = "Región ha sido eliminada"
        except:
            response.respuesta = "error"
            response.mensaje = "Región no puede ser eliminada"
        return response


@router.delete(
    path="/region",
    name="Eliminar regiones y sus comunas",
    description="Elimina todas las regiones y comunas")
def delete_all_regiones_comunas(db: Session = Depends(get_db)):
    response: DefaultResponse = DefaultResponse()
    try:
        delete_all(db)
        response.respuesta = "ok"
        response.mensaje = "Registros han sido eliminados"
    except:
        response.respuesta = "error"
        response.mensaje = "Registros no pueden ser eliminados"
    return response


def nombre_de_region_es_repetido(nombre_region: str, db: Session):
    nombre_repetido = db.query(RegionTabla).filter(RegionTabla.nombre == nombre_region).first()
    return nombre_repetido is not None


def nombre_de_comuna_es_repetido(nombre_comuna: str, db: Session):
    nombre_repetido = db.query(ComunaTabla).filter(ComunaTabla.nombre == nombre_comuna).first()
    return nombre_repetido is not None


def respuesta_region_registrada(response: DefaultResponse):
    response.respuesta = "error"
    response.mensaje = "Región ya ha sido registrada anteriormente"
    return response


def respuesta_region_no_encontrada(response: DefaultResponse):
    response.respuesta = "error"
    response.mensaje = "Región no encontrada"
    return response


def respuesta_archivo_invalido(response: DefaultResponse):
    response.respuesta = "error"
    response.mensaje = "Archivo inválido"
    return response


def respuesta_save_all(total_comunas: int, regiones_repetidas: List[str], comunas_repetidas: List[str],
                       regiones: List[RegionComunasResponse]):
    cant_comunas_guardadas_str = str(total_comunas - len(comunas_repetidas))
    cant_regiones_guardadas_str = str(len(regiones) - len(regiones_repetidas))
    comunas_repetidas_str = ", ".join(comunas_repetidas)
    regiones_repetidas_str = ", ".join(regiones_repetidas)

    return {"respuesta": f"Se han guardado {cant_comunas_guardadas_str} comunas "
                         f"y {cant_regiones_guardadas_str} regiones",
            "comunas_repetidas": comunas_repetidas_str,
            "regiones_repetidas": regiones_repetidas_str}


def respuesta_save_comunas_de_region(comunas: List[str], comunas_repetidas: List[str]):
    cant_comunas_guardadas_str = str(len(comunas) - len(comunas_repetidas))
    comunas_repetidas_str = ", ".join(comunas_repetidas)
    return {"respuesta": f"Se han guardado {cant_comunas_guardadas_str} comunas",
            "comunas_repetidas": comunas_repetidas_str}


def buscar_region(id_region: int, db: Session):
    return db.query(RegionTabla).filter(RegionTabla.idregion == id_region).first()


def buscar_comunas_de_region(id_region: int, db: Session, _limit: int | None, _offset: int | None):
    if _limit is None or _offset is None:
        return db.query(ComunaTabla).filter(ComunaTabla.idregion == id_region).all()
    else:
        return db.query(ComunaTabla).filter(ComunaTabla.idregion == id_region).limit(_limit).offset(_offset).all()


def buscar_regiones(db: Session, _limit: int | None, _offset: int | None):
    if _limit is None or _offset is None:
        return db.query(RegionTabla).all()
    else:
        return db.query(RegionTabla).limit(_limit).offset(_offset).all()


def count_comunas_de_region(id_region: int, db: Session):
    return db.query(ComunaTabla).filter(ComunaTabla.idregion == id_region).count()


def count_regiones(db: Session):
    return db.query(RegionTabla).count()


def guardar_region(region: RegionTabla, db: Session, idregion: int | None, nombre: str | None, active: int | None,
                   imagen: UploadFile | None):
    if nombre is not None:
        region.nombre = nombre.title()
    if idregion is not None:
        region.idregion = idregion
    if active is not None:
        region.active = active
    db.add(region)
    db.flush()
    validar_imagen_region(imagen, region, db)
    db.commit()


def eliminar_region(region: RegionTabla, db: Session):
    db.delete(region)
    db.commit()
    if region.url is not None:
        imagen_url = url_imagen_region(region.idregion, region.url)
        eliminar_imagen(imagen_url)


def delete_all(db: Session):
    db.query(ComunaTabla).delete()
    db.query(RegionTabla).delete()
    db.commit()
    [f.unlink() for f in Path("media/comuna").glob("*") if f.is_file()]
    [f.unlink() for f in Path("media/region").glob("*") if f.is_file()]


def guardar_comuna(comuna: str, id_region: int, db: Session, imagen: UploadFile | None):
    nueva_comuna = ComunaTabla()
    nueva_comuna.nombre = comuna.title()
    nueva_comuna.idregion = id_region
    db.add(nueva_comuna)
    db.flush()
    validar_imagen_comuna(imagen, nueva_comuna, db)


def guardar_region_obtiene_id(region: str, db: Session, imagen: UploadFile | None):
    nueva_region = RegionTabla()
    nueva_region.nombre = region.title()
    db.add(nueva_region)
    db.flush()
    validar_imagen_region(imagen, nueva_region, db)
    return nueva_region.idregion


def save_all_regiones_comunas(regiones: List[RegionComunasResponse], imagenes_reg: List[UploadFile] | None,
                              imagenes_com: List[UploadFile] | None, db: Session):
    comunas_repetidas: List[str] = []
    regiones_repetidas: List[str] = []
    contador_reg: int = -1
    contador_com: int = 0

    for region_y_comunas in regiones:
        contador_reg += 1

        if nombre_de_region_es_repetido(region_y_comunas.region, db):
            regiones_repetidas.append(region_y_comunas.region)
            for comuna_repetida in region_y_comunas.comunas:
                comunas_repetidas.append(comuna_repetida)
                contador_com += 1
        else:
            try:
                id_region = guardar_region_obtiene_id(region_y_comunas.region, db, imagenes_reg[contador_reg])
            except (IndexError, TypeError):
                id_region = guardar_region_obtiene_id(region_y_comunas.region, db, None)

            comunas_repetidas, contador_com = guardar_comunas_obtiene_repetidas(region_y_comunas.comunas,
                                                                                comunas_repetidas, db,
                                                                                id_region, imagenes_com, contador_com)

    db.commit()
    return respuesta_save_all(contador_com, regiones_repetidas, comunas_repetidas, regiones)


def guardar_comunas_obtiene_repetidas(comunas: List[str], comunas_repetidas: List[str], db: Session,
                                      id_region: int, imagenes: List[UploadFile] | None, contador_com: int):
    for comuna in comunas:
        if nombre_de_comuna_es_repetido(comuna, db):
            comunas_repetidas.append(comuna)
        else:
            try:
                guardar_comuna(comuna, id_region, db, imagenes[contador_com])
            except (IndexError, TypeError):
                guardar_comuna(comuna, id_region, db, None)
        contador_com += 1

    return comunas_repetidas, contador_com


def parse_csv_region_comunas_response(registros):
    regiones: List[RegionComunasResponse] = []
    str_regiones: List[str] = []
    str_region: str
    str_comuna: str

    # se crea un listado de objetos json con sus respectivas regiones
    for registro in registros:
        str_region = split_reg(registro, 0)
        if str_region not in str_regiones:
            region_y_comunas: RegionComunasResponse = RegionComunasResponse()
            str_regiones.append(str_region)
            region_y_comunas.region = str_region
            regiones.append(region_y_comunas)

    # se adjuntan las comunas a sus correspondientes regiones
    for region in regiones:
        for registro in registros:
            str_region = split_reg(registro, 0)
            if region.region == str_region:
                str_comuna = split_reg(registro, 1)
                region.comunas.append(str_comuna)

    return regiones


def validar_imagen_comuna(imagen: UploadFile | None, comuna: ComunaTabla, db: Session):
    if imagen is not None:
        if obtener_extension(imagen) in [".png", ".jpg"]:
            subir_imagen_comuna(comuna.idcomuna, imagen)
            comuna.url = obtener_extension(imagen)
            db.add(comuna)
            db.flush()


def validar_imagen_region(imagen: UploadFile | None, region: RegionTabla, db: Session):
    if imagen is not None:
        if obtener_extension(imagen) in [".png", ".jpg"]:
            subir_imagen_region(region.idregion, imagen)
            region.url = obtener_extension(imagen)
            db.add(region)
            db.flush()


def subir_imagen_region(id_region: int, imagen: UploadFile):
    ubicacion = url_imagen_region(id_region, obtener_extension(imagen))
    subir_imagen(ubicacion, imagen)


def subir_imagen_comuna(id_comuna: int, imagen: UploadFile):
    ubicacion = url_imagen_comuna(id_comuna, obtener_extension(imagen))
    subir_imagen(ubicacion, imagen)


def eliminar_url_region(region: RegionTabla, db: Session):
    region.url = None
    db.add(region)
    db.commit()


def obtener_extension(archivo: UploadFile):
    return os.path.splitext(archivo.filename)[1]


def subir_imagen(ubicacion: str, imagen: UploadFile):
    with open(ubicacion, "wb") as buffer:
        shutil.copyfileobj(imagen.file, buffer)


def eliminar_imagen(imagen_url: str):
    if os.path.exists(imagen_url):
        os.remove(imagen_url)


def imagen_por_defecto():
    return FileResponse("media/default.png", media_type="image/png")


def url_imagen_region(id_region: int, extension: str):
    return f"media/region/{id_region}{extension}"


def url_imagen_comuna(id_comuna: int, extension: str):
    return f"media/comuna/{id_comuna}{extension}"


def convert_bytes_to_string(bytes):
    data = bytes.decode('utf-8').splitlines()
    df = pandas.DataFrame(data)
    return parse_csv_json(df)


def parse_csv_json(df):
    result = df.to_json(orient="records")
    parsed = json.loads(result)
    parsed = parsed[1:]  # elimina header
    return parsed


def split_reg(registro, index: int):
    return registro["0"].split(";")[index].title()

# TODO:
# cambiar formato de envio de mensajes http
# paginacion
# informar cantidad de paginas, pagina actual, mostrar cantidad de resultados y paginas a petición
# query params
