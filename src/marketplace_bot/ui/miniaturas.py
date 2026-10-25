"""Fotos chiquitas para la ventana. Las fotos originales pesan 1-2 MB: se
reducen una vez y se guardan en %LOCALAPPDATA%\\MarketplaceBot\\miniaturas."""
import hashlib
import io
from pathlib import Path

from PIL import Image, ImageOps

from ..config import MINIATURAS

_memoria = {}


def miniatura(ruta, lado=360):
    """Devuelve los bytes JPEG de la foto reducida, o None si no se puede leer."""
    ruta = Path(ruta)
    try:
        marca = ruta.stat().st_mtime_ns
    except OSError:
        return None
    clave = (str(ruta), marca, lado)
    if clave in _memoria:
        return _memoria[clave]
    nombre = hashlib.sha1(f"{ruta}|{marca}|{lado}".encode()).hexdigest() + ".jpg"
    archivo = MINIATURAS / nombre
    try:
        datos = archivo.read_bytes()
    except OSError:
        try:
            with Image.open(ruta) as imagen:
                imagen.draft("RGB", (lado * 2, lado * 2))  # mucho mas rapido con fotos grandes
                imagen = ImageOps.exif_transpose(imagen).convert("RGB")
                imagen.thumbnail((lado, lado))
                salida = io.BytesIO()
                imagen.save(salida, "JPEG", quality=85)
                datos = salida.getvalue()
        except Exception:  # noqa: BLE001 - una foto rota no debe tumbar la ventana
            return None
        try:
            MINIATURAS.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(datos)
        except OSError:
            pass
    _memoria[clave] = datos
    return datos
