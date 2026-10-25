"""Registro de cada corrida y historial.

Cada vez que el bot trabaja se crea una carpeta en registros/ con:
  registro.txt   todo lo que el bot fue diciendo
  resumen.json   que paso con cada articulo (publicado, fallo, ...)
  *.png          las capturas de pantalla de los fallos

Ademas se sigue escribiendo ultimo_registro.txt en la carpeta del proyecto.
Las carpetas de registros/ SI se suben a git (llevan el nombre de quien corrio
el bot), asi las capturas de los fallos de otras PCs llegan con un git pull.
Solo registros/historial.csv queda en cada PC.
"""
import csv
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .modelos import Resultado

def usuario_actual():
    return os.environ.get("USERNAME") or os.environ.get("USER", "") or "pc"


def nombre_corrida(inicio, accion):
    """2026-10-25_111328_borrar_sarit: unica por PC y dice de quien es."""
    usuario = "".join(c for c in usuario_actual() if c.isalnum() or c in "-_") or "pc"
    return f"{inicio:%Y-%m-%d_%H%M%S}_{accion}_{usuario}"


ACCIONES = {"publicar": "Publicar", "probar": "Prueba", "borrar": "Borrar", "borrar_y_publicar": "Borrar y publicar"}


class Corrida:
    def __init__(self, rutas, accion, articulos=()):
        self.rutas = rutas
        self.accion = accion
        self.inicio = datetime.now()
        self.fin = None
        self.carpeta = rutas.registros / nombre_corrida(self.inicio, accion)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.resultados = {r.carpeta: r for r in articulos}
        self.borradas = 0
        self.mensaje_borrar = ""
        self.mensaje_final = ""
        self.paso = ""  # lo que el motor esta haciendo ahora
        self.progreso = (0, len(self.resultados), 1)  # (articulo actual, total, ronda)
        encabezado = f"{self.inicio:%Y-%m-%d %H:%M} · {ACCIONES.get(accion, accion)}\n"
        self._escribir_archivo(self.carpeta / "registro.txt", encabezado, "w")
        self._escribir_archivo(rutas.ultimo_registro, encabezado, "w")

    @staticmethod
    def _escribir_archivo(ruta, texto, modo="a"):
        try:
            with open(ruta, modo, encoding="utf-8") as f:
                f.write(texto)
        except OSError:
            pass

    def anotar(self, linea):
        self._escribir_archivo(self.carpeta / "registro.txt", linea)
        self._escribir_archivo(self.rutas.ultimo_registro, linea)

    def resultado(self, carpeta, **cambios):
        r = self.resultados.setdefault(carpeta, Resultado(carpeta=carpeta))
        for clave, valor in cambios.items():
            setattr(r, clave, valor)
        return r

    def terminar(self, mensaje=""):
        self.fin = datetime.now()
        self.mensaje_final = mensaje
        # Lo que quedo "trabajando" o "pendiente" no llego a hacerse.
        for r in self.resultados.values():
            if r.estado in ("pendiente", "trabajando"):
                r.estado = "saltado" if r.estado == "pendiente" else "fallo"
                r.detalle = r.detalle or "El bot se detuvo antes"
        self.guardar()
        anotar_historial(self)

    def guardar(self):
        datos = {
            "accion": self.accion,
            "usuario": usuario_actual(),
            "inicio": self.inicio.isoformat(timespec="seconds"),
            "fin": self.fin.isoformat(timespec="seconds") if self.fin else None,
            "borradas": self.borradas,
            "mensaje": self.mensaje_final,
            "mensaje_borrar": self.mensaje_borrar,
            "resultados": [asdict(r) for r in self.resultados.values()],
        }
        (self.carpeta / "resumen.json").write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    @property
    def fallidos(self):
        return [r for r in self.resultados.values() if r.estado == "fallo"]

    @property
    def exitosos(self):
        return [r for r in self.resultados.values() if r.ok]


def anotar_historial(corrida):
    """Una linea por articulo en registros/historial.csv (con el resultado real)."""
    archivo = corrida.rutas.registros / "historial.csv"
    nuevo = not archivo.exists()
    usuario = usuario_actual()
    fecha = f"{corrida.inicio:%Y-%m-%d %H:%M}"
    try:
        with open(archivo, "a", encoding="utf-8", newline="") as f:
            escritor = csv.writer(f)
            if nuevo:
                escritor.writerow(["fecha", "usuario", "accion", "articulo", "resultado", "detalle"])
            if corrida.accion in ("borrar", "borrar_y_publicar"):
                escritor.writerow([fecha, usuario, "borrar", "", f"{corrida.borradas} borradas", corrida.mensaje_borrar])
            for r in corrida.resultados.values():
                escritor.writerow([fecha, usuario, corrida.accion, r.carpeta, r.estado, r.detalle])
    except OSError:
        pass


def leer_corridas(rutas, limite=50, solo_mias=False):
    """Las ultimas corridas, la mas nueva primero. `solo_mias` deja fuera las que
    llegaron de otras PCs por git."""
    if not rutas.registros.exists():
        return []
    corridas = []
    for carpeta in sorted(rutas.registros.iterdir(), reverse=True):
        resumen = carpeta / "resumen.json"
        if not resumen.exists():
            continue
        try:
            datos = json.loads(resumen.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if solo_mias and datos.get("usuario", usuario_actual()) != usuario_actual():
            continue
        datos["carpeta"] = str(carpeta)
        datos["resultados"] = [Resultado(**r) for r in datos.get("resultados", [])]
        corridas.append(datos)
        if len(corridas) >= limite:
            break
    return corridas


def nombre_captura(corrida_carpeta, indice, carpeta):
    return str(Path(corrida_carpeta) / f"fallo_{indice:02d}_{carpeta}.png")
