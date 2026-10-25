"""Lo que el bot hizo cada vez, con el resultado real de cada articulo."""
from datetime import datetime
from pathlib import Path

import flet as ft

from ...registros import ACCIONES, leer_corridas
from .. import tema
from .hoy import fecha_bonita


class VistaHistorial:
    def __init__(self, app):
        self.app = app

    def construir(self):
        from ..app import abrir

        corridas = leer_corridas(self.app.rutas, limite=40)
        tarjetas = []
        for c in corridas:
            inicio = datetime.fromisoformat(c["inicio"])
            resultados = c["resultados"]
            bien = sum(1 for r in resultados if r.ok)
            mal = sum(1 for r in resultados if r.estado == "fallo")
            chips = []
            if c["accion"] in ("borrar", "borrar_y_publicar"):
                chips.append(tema.chip(f"{c.get('borradas', 0)} borradas", tema.TENUE))
            if resultados:
                chips.append(tema.chip(f"{bien} bien", tema.EXITO))
            if mal:
                chips.append(tema.chip(f"{mal} " + ("falló" if mal == 1 else "fallaron"), tema.PELIGRO))
            filas = []
            for r in resultados:
                icono, color, texto = tema.ESTADOS_ARTICULO.get(r.estado, tema.ESTADOS_ARTICULO["pendiente"])
                filas.append(ft.Row([
                    ft.Icon(icono, color=color, size=18),
                    ft.Text(r.titulo or r.carpeta, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(r.detalle or texto, size=12, color=tema.TENUE, width=320, max_lines=2),
                    ft.IconButton(ft.Icons.IMAGE_OUTLINED, tooltip="Ver captura del fallo", icon_size=18,
                                  on_click=lambda e, ruta=r.captura: abrir(ruta)) if r.captura else ft.Container(width=40),
                ]))
            mensaje = c.get("mensaje_borrar") or c.get("mensaje") or ""
            registro = Path(c["carpeta"]) / "registro.txt"
            tarjetas.append(ft.ExpansionTile(
                title=ft.Text(f"{ACCIONES.get(c['accion'], c['accion'])} · {fecha_bonita(inicio)}, {inicio:%H:%M}",
                              weight=ft.FontWeight.W_600),
                subtitle=ft.Row(chips, spacing=6, wrap=True),
                bgcolor=tema.TARJETA, collapsed_bgcolor=tema.TARJETA,
                shape=ft.RoundedRectangleBorder(radius=14), collapsed_shape=ft.RoundedRectangleBorder(radius=14),
                controls_padding=ft.Padding.only(left=16, right=16, bottom=12),
                controls=[*([ft.Text(mensaje, color=tema.TENUE)] if mensaje else []), *filas,
                          ft.Row([ft.TextButton("Abrir registro completo", icon=ft.Icons.DESCRIPTION_OUTLINED,
                                                on_click=lambda e, ruta=registro: abrir(ruta)),
                                  ft.TextButton("Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
                                                on_click=lambda e, ruta=c["carpeta"]: abrir(ruta))])],
            ))
        if not tarjetas:
            tarjetas = [ft.Text("Todavía no hay corridas con la versión nueva.", color=tema.TENUE)]
        return ft.Column([
            tema.titulo("Historial", "Lo que pasó cada vez, artículo por artículo. Se guarda solo en esta PC."),
            ft.Column(tarjetas, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
        ], expand=True, spacing=16)
