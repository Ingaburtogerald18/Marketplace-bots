"""Rutas y ajustes del bot.

- RAIZ: la carpeta del proyecto (la que se comparte por git). Ahi viven las
  plantillas (publicaciones/), los recortes de botones (recursos/botones/) y
  los registros de cada corrida (registros/, no se sube a git).
- LOCAL: %LOCALAPPDATA%\\MarketplaceBot, solo de esta PC: ajustes, lo marcado
  para publicar hoy, miniaturas y fotos reducidas para subir.
"""
import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

CONGELADO = getattr(sys, "frozen", False)  # True cuando corre como .exe

LOCAL = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "MarketplaceBot"
ARCHIVO_AJUSTES = LOCAL / "ajustes.json"
ARCHIVO_SELECCION = LOCAL / "seleccion.json"  # el mismo que usaba la ventana vieja
MINIATURAS = LOCAL / "miniaturas"
SUBIDAS = LOCAL / "subidas"


def _raiz_por_defecto():
    if CONGELADO:
        return Path.home() / "Documents" / "Marketplace Bot"
    return Path(__file__).resolve().parents[2]  # src/marketplace_bot -> proyecto


def _recursos_empaquetados():
    base = Path(getattr(sys, "_MEIPASS", _raiz_por_defecto()))
    return base / "recursos" / "botones"


@dataclass
class Ajustes:
    carpeta_datos: str = ""          # vacio = la carpeta del proyecto
    ventana: str = ""                # texto que debe tener la ventana del navegador ("" = automatico)
    max_grupos: int = 20             # Facebook deja hasta 20
    pausa_min: int = 5               # segundos entre articulos
    pausa_max: int = 10
    reintentar_fallidos: bool = True
    reducir_fotos: bool = True       # sube las fotos a 1600 px: mas rapido
    max_borrar: int = 20
    barrita_progreso: bool = True    # ventanita arriba mientras trabaja
    escala: float = 0                # escala de Windows que el bot detecto (0 = no se sabe)

    @classmethod
    def cargar(cls):
        try:
            datos = json.loads(ARCHIVO_AJUSTES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        validos = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in datos.items() if k in validos})

    def guardar(self):
        LOCAL.mkdir(parents=True, exist_ok=True)
        ARCHIVO_AJUSTES.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")


class Rutas:
    """Todas las carpetas que usa el bot, segun los ajustes."""

    def __init__(self, ajustes=None):
        ajustes = ajustes or Ajustes.cargar()
        self.raiz = Path(ajustes.carpeta_datos) if ajustes.carpeta_datos else _raiz_por_defecto()
        self.plantillas = self.raiz / "publicaciones"
        self.registros = self.raiz / "registros"
        propios = self.raiz / "recursos" / "botones"
        self.botones = propios if propios.exists() else _recursos_empaquetados()
        self.categorias = self.botones / "crear" / "categorias"
        self.estados = self.botones / "crear" / "estados"
        self.firma = self.plantillas / "firma.txt"
        self.ultimo_registro = self.raiz / "ultimo_registro.txt"

    def categorias_conocidas(self):
        return sorted(p.stem for p in self.categorias.glob("*.png")) if self.categorias.exists() else []

    def estados_conocidos(self):
        return sorted(p.stem for p in self.estados.glob("*.png")) if self.estados.exists() else []


def cargar_seleccion():
    try:
        return set(json.loads(ARCHIVO_SELECCION.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def guardar_seleccion(nombres):
    LOCAL.mkdir(parents=True, exist_ok=True)
    ARCHIVO_SELECCION.write_text(json.dumps(sorted(nombres), ensure_ascii=False), encoding="utf-8")
