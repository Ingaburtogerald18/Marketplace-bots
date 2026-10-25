"""Todas las plantillas en tarjetas, con buscador y casilla "Publicar hoy"."""
import unicodedata

import flet as ft

from ... import plantillas as plantillas_mod
from .. import tema
from ..miniaturas import miniatura


def _normal(texto):
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()


class VistaPlantillas:
    def __init__(self, app):
        self.app = app
        self.busqueda = ""
        self.categoria = "Todas"

    def construir(self):
        app = self.app
        app.recargar_plantillas()
        self.buscador = ft.TextField(hint_text="Buscar…", prefix_icon=ft.Icons.SEARCH, value=self.busqueda,
                                     width=280, dense=True, border_radius=12,
                                     on_change=lambda e: self._filtrar(busqueda=e.control.value))
        categorias = sorted({p.categoria for p in app.plantillas if p.categoria})
        self.filtro = ft.Dropdown(value=self.categoria, width=240, dense=True,
                                  options=[ft.DropdownOption(key="Todas", text="Todas las categorías")] +
                                  [ft.DropdownOption(key=c, text=c) for c in categorias],
                                  on_select=lambda e: self._filtrar(categoria=e.control.value))
        self.resumen = ft.Text(color=tema.TENUE)
        self.grilla = ft.GridView(expand=True, max_extent=270, child_aspect_ratio=0.66, spacing=16, run_spacing=16)
        self.refrescar()
        return ft.Column([
            ft.Row([tema.titulo("Plantillas", "Marcá lo que sale hoy. Lo vendido se desmarca, no se borra."),
                    ft.Container(expand=True),
                    ft.FilledButton("Nueva plantilla", icon=ft.Icons.ADD, on_click=lambda e: app.ir("editor"))]),
            ft.Row([self.buscador, self.filtro, ft.Container(expand=True), self.resumen,
                    ft.TextButton("Marcar todas", on_click=lambda e: self._marcar_todas(True)),
                    ft.TextButton("Desmarcar todas", on_click=lambda e: self._marcar_todas(False))]),
            self.grilla,
        ], expand=True, spacing=16)

    def _visibles(self):
        texto = _normal(self.busqueda)
        return [p for p in self.app.plantillas
                if (not texto or texto in _normal(p.titulo + " " + p.descripcion))
                and (self.categoria in (None, "Todas") or p.categoria == self.categoria)]

    def _filtrar(self, busqueda=None, categoria=None):
        if busqueda is not None:
            self.busqueda = busqueda
        if categoria is not None:
            self.categoria = categoria
        self.refrescar()
        self.app.page.update()

    def _marcar_todas(self, valor):
        for p in self._visibles():
            self.app.marcar(p.nombre, valor)
        self.refrescar()
        self.app.page.update()

    def refrescar(self):
        visibles = self._visibles()
        marcadas = sum(1 for p in self.app.plantillas if p.nombre in self.app.seleccion)
        self.resumen.value = f"{marcadas} marcadas de {len(self.app.plantillas)}"
        self.grilla.controls = [self._tarjeta(p) for p in visibles] or [
            ft.Text("No hay plantillas que coincidan." if self.app.plantillas else
                    "Todavía no hay plantillas. Creá la primera con «Nueva plantilla».", color=tema.TENUE)]

    def _tarjeta(self, p):
        app = self.app
        marcada = p.nombre in app.seleccion
        foto = miniatura(p.portada, 360) if p.portada else None
        problemas = plantillas_mod.problemas(p, app.rutas)

        def cambiar(e):
            app.marcar(p.nombre, e.control.value)
            self.refrescar()
            app.page.update()

        imagen = ft.Image(src=foto, fit=ft.BoxFit.COVER, width=270, height=170) if foto else ft.Container(
            ft.Icon(ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED, size=40, color=tema.TENUE),
            alignment=ft.Alignment.CENTER, height=170, bgcolor=tema.PANEL)
        menu = ft.PopupMenuButton(icon=ft.Icons.MORE_HORIZ, items=[
            ft.PopupMenuItem(content="Editar", icon=ft.Icons.EDIT, on_click=lambda e: app.ir("editor", plantilla=p)),
            ft.PopupMenuItem(content="Duplicar", icon=ft.Icons.COPY, on_click=lambda e: self._duplicar(p)),
            ft.PopupMenuItem(content="Eliminar plantilla", icon=ft.Icons.DELETE_OUTLINE, on_click=lambda e: self._eliminar(p)),
        ])
        return ft.Container(
            content=ft.Column([
                ft.Stack([
                    imagen,
                    ft.Container(tema.chip(f"{len(p.fotos)} fotos", tema.TEXTO, ft.Icons.PHOTO_LIBRARY_OUTLINED),
                                 bgcolor="#99000000", border_radius=20, right=8, top=8),
                ], height=170),
                ft.Container(ft.Column([
                    ft.Text(p.titulo or p.nombre, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,
                            weight=ft.FontWeight.W_600, size=14, height=40),
                    ft.Text(tema.precio(p.precio), size=16, weight=ft.FontWeight.BOLD, color=tema.ACENTO),
                    ft.Text(f"⚠ {problemas[0]}" if problemas else p.categoria, size=12, max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS, color=tema.ALERTA if problemas else tema.TENUE),
                    ft.Row([ft.Checkbox(label="Publicar hoy", value=marcada, on_change=cambiar),
                            ft.Container(expand=True), menu], spacing=0),
                ], spacing=4), padding=ft.Padding.only(left=12, right=4, top=10, bottom=4)),
            ], spacing=0),
            bgcolor=tema.TARJETA, border_radius=14, clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            border=ft.Border.all(2 if marcada else 1, tema.ACENTO if marcada else tema.BORDE),
            on_click=lambda e: app.ir("editor", plantilla=p), ink=True,
        )

    def _duplicar(self, p):
        try:
            nueva = plantillas_mod.duplicar(p, self.app.rutas.plantillas)
        except Exception as e:  # noqa: BLE001
            self.app.avisar(f"No pude duplicarla: {e}", tema.PELIGRO)
            return
        self.app.recargar_plantillas()
        self.app.ir("editor", plantilla=nueva)

    def _eliminar(self, p):
        def borrar():
            try:
                plantillas_mod.borrar_carpeta(p.carpeta)
            except OSError as e:
                self.app.avisar(f"Windows no dejó borrarla: {e}. Si la tenés abierta en el Explorador, cerrala.",
                                tema.PELIGRO)
                return
            self.app.marcar(p.nombre, False)
            self.app.recargar_plantillas()
            self.refrescar()
            self.app.page.update()
            self.app.avisar(f"Eliminé «{p.titulo}».")

        self.app.preguntar("Eliminar plantilla", f"¿Eliminar «{p.titulo}» y sus fotos? Esto no borra nada en Facebook.\n\n"
                           "Si solo se vendió, mejor desmarcala.", "Eliminar", borrar, peligro=True)
