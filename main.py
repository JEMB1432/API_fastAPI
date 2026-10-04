"""
API — gestor de colección de películas con FastAPI.
Docs:      http://127.0.0.1:8000/docs   y   /redoc
"""
from datetime import date
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

app = FastAPI(
    title="API",
    description="Gestor de colección de películas: CRUD, búsqueda, filtros y estadísticas.",
    version="1.0.0",
)


# ---------- Modelos (Pydantic) ----------
class Genero(str, Enum):
    accion = "accion"
    comedia = "comedia"
    drama = "drama"
    ciencia_ficcion = "ciencia_ficcion"
    terror = "terror"
    animacion = "animacion"
    documental = "documental"


class PeliculaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=120, examples=["Interestelar"])
    director: str = Field(..., min_length=1, max_length=80, examples=["Christopher Nolan"])
    anio: int = Field(..., ge=1888, le=date.today().year + 5, examples=[2014])
    genero: Genero
    calificacion: float = Field(..., ge=0, le=10, examples=[8.7])
    vista: bool = False


class PeliculaCrear(PeliculaBase):
    """Cuerpo para POST y PUT."""


class Pelicula(PeliculaBase):
    id: int


# ---------- "Base de datos" en memoria ----------
db: dict[int, Pelicula] = {}
siguiente_id = 1


def _insertar(datos: PeliculaCrear) -> Pelicula:
    global siguiente_id
    pelicula = Pelicula(id=siguiente_id, **datos.model_dump())
    db[siguiente_id] = pelicula
    siguiente_id += 1
    return pelicula


# Datos iniciales
for _p in [
    PeliculaCrear(titulo="Interestelar", director="Christopher Nolan", anio=2014,
                  genero=Genero.ciencia_ficcion, calificacion=8.7, vista=True),
    PeliculaCrear(titulo="Coco", director="Lee Unkrich", anio=2017,
                  genero=Genero.animacion, calificacion=8.4, vista=True),
    PeliculaCrear(titulo="Roma", director="Alfonso Cuarón", anio=2018,
                  genero=Genero.drama, calificacion=7.7, vista=False),
]:
    _insertar(_p)


def _obtener_o_404(pelicula_id: int) -> Pelicula:
    pelicula = db.get(pelicula_id)
    if pelicula is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La película con id {pelicula_id} no existe",
        )
    return pelicula


# ---------- Endpoints extra ----------
@app.get("/peliculas/buscar", response_model=list[Pelicula], tags=["Extra"])
def buscar(q: str = Query(..., min_length=2, description="Texto a buscar en título o director")):
    """Búsqueda por texto (título o director), sin distinguir mayúsculas."""
    texto = q.lower()
    return [p for p in db.values() if texto in p.titulo.lower() or texto in p.director.lower()]


@app.get("/peliculas/estadisticas", tags=["Extra"])
def estadisticas():
    """Resumen de la colección: totales, promedio, mejor película y conteo por género."""
    if not db:
        return {"total": 0, "vistas": 0, "pendientes": 0, "promedio_calificacion": None,
                "mejor_calificada": None, "por_genero": {}}
    peliculas = list(db.values())
    por_genero: dict[str, int] = {}
    for p in peliculas:
        por_genero[p.genero.value] = por_genero.get(p.genero.value, 0) + 1
    mejor = max(peliculas, key=lambda p: p.calificacion)
    vistas = sum(p.vista for p in peliculas)
    return {
        "total": len(peliculas),
        "vistas": vistas,
        "pendientes": len(peliculas) - vistas,
        "promedio_calificacion": round(sum(p.calificacion for p in peliculas) / len(peliculas), 2),
        "mejor_calificada": {"id": mejor.id, "titulo": mejor.titulo, "calificacion": mejor.calificacion},
        "por_genero": por_genero,
    }


# ---------- CRUD ----------
@app.post("/peliculas", response_model=Pelicula, status_code=status.HTTP_201_CREATED, tags=["CRUD"])
def crear_pelicula(datos: PeliculaCrear):
    """Crea una película nueva (201 Created)."""
    return _insertar(datos)


@app.get("/peliculas", response_model=list[Pelicula], tags=["CRUD"])
def listar_peliculas(
    genero: Optional[Genero] = Query(None, description="Filtrar por género"),
    vista: Optional[bool] = Query(None, description="Filtrar por vistas / pendientes"),
    anio_min: Optional[int] = Query(None, description="Año mínimo"),
):
    """Lista todas las películas, con filtros opcionales."""
    resultado = list(db.values())
    if genero is not None:
        resultado = [p for p in resultado if p.genero == genero]
    if vista is not None:
        resultado = [p for p in resultado if p.vista == vista]
    if anio_min is not None:
        resultado = [p for p in resultado if p.anio >= anio_min]
    return resultado


@app.get("/peliculas/{pelicula_id}", response_model=Pelicula, tags=["CRUD"])
def obtener_pelicula(pelicula_id: int):
    return _obtener_o_404(pelicula_id)


@app.put("/peliculas/{pelicula_id}", response_model=Pelicula, tags=["CRUD"])
def actualizar_pelicula(pelicula_id: int, datos: PeliculaCrear):
    _obtener_o_404(pelicula_id)
    actualizada = Pelicula(id=pelicula_id, **datos.model_dump())
    db[pelicula_id] = actualizada
    return actualizada


@app.delete("/peliculas/{pelicula_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["CRUD"])
def eliminar_pelicula(pelicula_id: int):
    _obtener_o_404(pelicula_id)
    del db[pelicula_id]
