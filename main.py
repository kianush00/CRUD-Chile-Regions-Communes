import fastapi
import uvicorn

from api import comunas
from api import regiones

api = fastapi.FastAPI()

api.include_router(comunas.router)
api.include_router(regiones.router)

if __name__ == '__main__':
    uvicorn.run("main:api", host="127.0.0.1", port=8000, reload=True)
