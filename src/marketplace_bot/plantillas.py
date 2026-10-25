"""Leer, guardar, duplicar y borrar plantillas (las carpetas de publicaciones/).

El formato no cambia respecto a la version anterior, asi que las plantillas
que ya existen y las de las otras PCs siguen sirviendo:
  datos.txt        titulo, precio, categoria, estado (una por linea, "clave: valor")
  descripcion.txt  el texto tal cual se pega en Facebook
  01.jpg, 02.jpg   las fotos en orden (la primera es la portada)
"""
import os
import re
import shutil
import stat
import unicodedata
from pathlib import Path

from PIL import Image, ImageOps

from .modelos import ESTADOS_FB, MAX_FOTOS, Plantilla

try:  # fotos HEIC del iPhone
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

FOTOS_OK = (".jpg", ".jpeg", ".png")
FOTOS_TODAS = FOTOS_OK + (".heic", ".heif")


def leer(carpeta):
    carpeta = Path(carpeta)
    datos = {}
    archivo = carpeta / "datos.txt"
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8-sig").splitlines():
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                datos[clave.strip().lower()] = valor.strip()
    descripcion = carpeta / "descripcion.txt"
    return Plantilla(
        carpeta=carpeta,
        titulo=datos.get("titulo", ""),
        precio=datos.get("precio", ""),
        categoria=datos.get("categoria", ""),
        estado=datos.get("estado", "Nuevo"),
        descripcion=descripcion.read_text(encoding="utf-8-sig").strip() if descripcion.exists() else "",
        fotos=sorted((p for p in carpeta.iterdir() if p.suffix.lower() in FOTOS_OK), key=lambda p: p.name.lower())
        if carpeta.exists() else [],
    )


def listar(carpeta_plantillas):
    carpeta_plantillas = Path(carpeta_plantillas)
    if not carpeta_plantillas.exists():
        return []
    carpetas = sorted(p for p in carpeta_plantillas.iterdir() if (p / "datos.txt").exists())
    return [leer(c) for c in carpetas]


def problemas(plantilla, rutas):
    """Lo que impediria publicar esta plantilla, en palabras simples."""
    lista = []
    if not plantilla.titulo:
        lista.append("Falta el título")
    if not plantilla.precio.isdigit():
        lista.append("El precio debe ser solo números")
    if not plantilla.fotos:
        lista.append("No tiene fotos")
    elif len(plantilla.fotos) > MAX_FOTOS:
        lista.append(f"Tiene {len(plantilla.fotos)} fotos; Facebook acepta {MAX_FOTOS}")
    if plantilla.categoria not in rutas.categorias_conocidas():
        lista.append(f"El bot aún no conoce la categoría «{plantilla.categoria}»")
    if plantilla.estado not in rutas.estados_conocidos():
        lista.append(f"El bot aún no conoce el estado «{plantilla.estado}»")
    return lista


def nombre_carpeta(titulo, carpeta_plantillas):
    texto = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()[:40].strip("-") or "articulo"
    nombre, n = texto, 2
    while (Path(carpeta_plantillas) / nombre).exists():
        nombre, n = f"{texto}-{n}", n + 1
    return nombre


def a_jpg(origen, destino):
    """Copia una foto; si es HEIC (iPhone) la convierte a JPG."""
    origen, destino = Path(origen), Path(destino)
    if origen.suffix.lower() in (".heic", ".heif"):
        with Image.open(origen) as imagen:
            ImageOps.exif_transpose(imagen).convert("RGB").save(destino.with_suffix(".jpg"), quality=92)
        return destino.with_suffix(".jpg")
    destino = destino.with_suffix(".jpg" if origen.suffix.lower() == ".jpeg" else origen.suffix.lower())
    shutil.copy2(origen, destino)
    return destino


def guardar(plantilla, fotos):
    """Guarda datos, descripcion y fotos en orden (01, 02, ...; la 01 es la portada).

    `fotos` es la lista final de rutas (pueden estar en esta carpeta o fuera).
    """
    carpeta = Path(plantilla.carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "datos.txt").write_text(
        f"titulo: {plantilla.titulo}\nprecio: {plantilla.precio}\n"
        f"categoria: {plantilla.categoria}\nestado: {plantilla.estado}\n",
        encoding="utf-8",
    )
    (carpeta / "descripcion.txt").write_text(plantilla.descripcion.strip() + "\n", encoding="utf-8")

    # Primero todo a una carpeta temporal y luego se renombra en orden, por si
    # alguna foto nueva tiene el mismo nombre que una vieja.
    temporal = carpeta / "_nuevas"
    if temporal.exists():
        borrar_carpeta(temporal)
    temporal.mkdir()
    nuevas = [a_jpg(f, temporal / f"{i:02d}") for i, f in enumerate(fotos, 1)]
    for vieja in carpeta.iterdir():
        if vieja.is_file() and vieja.suffix.lower() in FOTOS_TODAS:
            _quitar_solo_lectura(vieja)
            vieja.unlink()
    for foto in nuevas:
        foto.replace(carpeta / foto.name)
    temporal.rmdir()
    return leer(carpeta)


def duplicar(plantilla, carpeta_plantillas):
    nueva = Plantilla(
        carpeta=Path(carpeta_plantillas) / nombre_carpeta(plantilla.titulo + " copia", carpeta_plantillas),
        titulo=plantilla.titulo + " (copia)", precio=plantilla.precio, categoria=plantilla.categoria,
        estado=plantilla.estado, descripcion=plantilla.descripcion,
    )
    return guardar(nueva, plantilla.fotos)


def _quitar_solo_lectura(ruta):
    try:
        os.chmod(ruta, stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def borrar_carpeta(carpeta):
    """Borra la carpeta aunque Windows o Drive hayan dejado archivos de solo lectura."""
    def reintentar(funcion, ruta, *_):
        _quitar_solo_lectura(ruta)
        funcion(ruta)

    shutil.rmtree(carpeta, onexc=reintentar)


def leer_firma(rutas):
    try:
        return rutas.firma.read_text(encoding="utf-8-sig").strip()
    except OSError:
        return ""


def guardar_firma(rutas, texto):
    rutas.plantillas.mkdir(parents=True, exist_ok=True)
    rutas.firma.write_text(texto.strip() + "\n", encoding="utf-8")


__all__ = ["ESTADOS_FB", "leer", "listar", "problemas", "guardar", "duplicar", "borrar_carpeta",
           "nombre_carpeta", "leer_firma", "guardar_firma", "FOTOS_TODAS"]
