import sys
from pathlib import Path

import pytest
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

CAPTURAS = RAIZ / "tests" / "capturas"
BOTONES = RAIZ / "recursos" / "botones"


def pantalla(nombre):
    imagen = Image.open(CAPTURAS / f"{nombre}.png").convert("RGB")
    return lambda: imagen


@pytest.fixture
def vision_de():
    from marketplace_bot.motor.vision import Vision

    return lambda nombre, **kw: Vision(BOTONES, capturar=pantalla(nombre), **kw)


class AccionesFalsas:
    """Hace como que mueve el mouse: anota todo y no toca nada."""

    def __init__(self, ancho=1920, alto=1080):
        self.hechas = []
        self.ancho, self.alto = ancho, alto

    def __getattr__(self, nombre):
        return lambda *a, **k: self.hechas.append((nombre, a))

    def tamano_pantalla(self):
        return self.ancho, self.alto

    def pausa(self, *a):
        pass

    def captura(self, ruta, cajas=(), puntos=()):
        self.hechas.append(("captura", (str(ruta),)))
        return str(ruta)


@pytest.fixture
def acciones():
    return AccionesFalsas()


@pytest.fixture
def rutas(tmp_path):
    from marketplace_bot.config import Ajustes, Rutas

    rutas = Rutas(Ajustes(carpeta_datos=str(tmp_path)))
    rutas.botones = BOTONES  # los recortes reales del proyecto
    rutas.categorias = BOTONES / "crear" / "categorias"
    rutas.estados = BOTONES / "crear" / "estados"
    rutas.plantillas.mkdir()
    return rutas
