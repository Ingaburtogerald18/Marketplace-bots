"""La busqueda de botones, probada con capturas reales de Facebook.

Cada error real que aparezca se guarda en tests/capturas/ y se agrega aqui,
asi lo que ya funcionaba no se vuelve a romper.
"""
import pytest
from PIL import Image, ImageOps

from marketplace_bot.motor.vision import Vision


@pytest.mark.parametrize("captura, boton, donde", [
    ("borrar_publicacion", "borrar/compartir", (671, 155)),
    ("borrar_publicacion", "borrar/opciones", (777, 155)),
    ("borrar_menu_opciones", "borrar/eliminar", (715, 400)),
    ("borrar_confirmacion", "borrar/confirmar", (579, 281)),
    ("borrar_pagina_vacia", "borrar/vacio", (1152, 597)),
    ("publicar_lista_estados", "crear/estados/Nuevo", (71, 737)),
    ("publicar_lista_estados", "crear/estados/Usado - Como nuevo", (106, 772)),
    ("publicar_lista_estados", "crear/estados/Usado - Buen estado", (104, 807)),
    ("publicar_lista_estados", "crear/estados/Usado - Aceptable", (96, 842)),
])
def test_encuentra_el_boton(vision_de, captura, boton, donde):
    caja = vision_de(captura).buscar(boton)
    assert caja is not None, f"no encontró {boton} en {captura}"
    assert abs(caja.x - donde[0]) <= 3 and abs(caja.y - donde[1]) <= 3


@pytest.mark.parametrize("captura, boton", [
    ("borrar_pagina_vacia", "borrar/compartir"),  # 24 oct: la página estaba vacía
    ("borrar_publicacion", "borrar/vacio"),
    ("publicar_lista_estados", "crear/publicar"),
])
def test_no_inventa_botones(vision_de, captura, boton):
    assert vision_de(captura).buscar(boton) is None


def test_busca_solo_en_la_zona(vision_de):
    vision = vision_de("borrar_publicacion")
    assert vision.buscar("borrar/opciones", zona=(740, 130, 80, 50)) is not None
    assert vision.buscar("borrar/opciones", zona=(0, 0, 400, 300)) is None


def test_modo_claro_con_recorte_de_modo_oscuro(tmp_path):
    """Invertimos la captura (oscuro -> claro): el recorte de modo oscuro debe servir igual."""
    from conftest import BOTONES, CAPTURAS

    claro = ImageOps.invert(Image.open(CAPTURAS / "borrar_publicacion.png").convert("RGB"))
    vision = Vision(BOTONES, capturar=lambda: claro)
    caja = vision.buscar("borrar/compartir")
    assert caja is not None and abs(caja.x - 671) <= 3


def test_pantalla_al_125(tmp_path):
    from conftest import BOTONES, CAPTURAS

    original = Image.open(CAPTURAS / "borrar_publicacion.png").convert("RGB")
    grande = original.resize((round(original.width * 1.25), round(original.height * 1.25)), Image.LANCZOS)
    vision = Vision(BOTONES, capturar=lambda: grande)
    caja = vision.buscar("borrar/compartir")
    assert caja is not None
    assert vision.escala == 1.25
    assert abs(caja.x - 671 * 1.25) <= 5


def test_escala_conocida_solo_prueba_ese_tamano(vision_de):
    vision = vision_de("borrar_publicacion", escala=1.0)
    assert {e for _, _, e in vision._variantes("borrar/compartir")} == {1.0}


def test_variantes_de_idioma(vision_de):
    archivos = [p.name for p in vision_de("borrar_publicacion").archivos("borrar/compartir")]
    assert archivos == ["compartir.png", "compartir_en.png"]


def test_casillas_de_grupos_no_se_repiten(tmp_path):
    from conftest import BOTONES

    casilla = Image.open(BOTONES / "crear" / "casilla.png").convert("RGB")
    lienzo = Image.new("RGB", (400, 400), (36, 37, 38))
    for y in (20, 120, 220):
        lienzo.paste(casilla, (50, y))
    vision = Vision(BOTONES, capturar=lambda: lienzo)
    cajas = vision.buscar_todas("crear/casilla")
    assert [c.y for c in cajas] == [32, 132, 232]
