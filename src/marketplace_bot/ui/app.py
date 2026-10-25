"""La ventana del Marketplace bot (Flet).

Pantallas: Hoy, Plantillas (con su editor), Historial y Ajustes. La ventana
nunca mueve el mouse: le pide al Ejecutor que corra el motor y muestra lo que
va pasando.
"""
import os
import sys

import flet as ft

from .. import VERSION, plantillas
from ..config import Ajustes, Rutas, cargar_seleccion, guardar_seleccion
from ..ejecutor import Ejecutor
from . import tema
from .vistas.ajustes import VistaAjustes
from .vistas.editor import VistaEditor
from .vistas.historial import VistaHistorial
from .vistas.hoy import VistaHoy
from .vistas.plantillas import VistaPlantillas
from .vistas.progreso import BarritaProgreso


def abrir(ruta):
    """Abre un archivo o carpeta con el programa de Windows que corresponda."""
    try:
        os.startfile(ruta)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass


def ancho_pantalla():
    if sys.platform == "win32":
        try:
            import ctypes

            return ctypes.windll.user32.GetSystemMetrics(0)
        except Exception:  # noqa: BLE001
            pass
    return 1920


class App:
    PANTALLAS = [
        ("hoy", "Hoy", ft.Icons.TODAY_OUTLINED, ft.Icons.TODAY),
        ("plantillas", "Plantillas", ft.Icons.INVENTORY_2_OUTLINED, ft.Icons.INVENTORY_2),
        ("historial", "Historial", ft.Icons.HISTORY, ft.Icons.HISTORY),
        ("ajustes", "Ajustes", ft.Icons.SETTINGS_OUTLINED, ft.Icons.SETTINGS),
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self.ajustes = Ajustes.cargar()
        self.rutas = Rutas(self.ajustes)
        self.rutas.plantillas.mkdir(parents=True, exist_ok=True)
        self.seleccion = cargar_seleccion()
        self.plantillas = []
        self.ejecutor = Ejecutor(self.rutas, self.ajustes, al_linea=self._al_linea,
                                 al_cambio=self._al_cambio, al_terminar=self._al_terminar)
        self._geometria = None
        self.recargar_plantillas()

        page.title = "Marketplace bot"
        page.theme_mode = ft.ThemeMode.DARK
        page.theme = page.dark_theme = tema.tema()
        page.bgcolor = tema.FONDO
        page.padding = 0
        page.window.width, page.window.height = 1320, 860
        page.window.min_width, page.window.min_height = 1000, 680

        self.vistas = {
            "hoy": VistaHoy(self),
            "plantillas": VistaPlantillas(self),
            "historial": VistaHistorial(self),
            "ajustes": VistaAjustes(self),
        }
        self.barrita = BarritaProgreso(self)
        self.riel = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, min_width=96,
            bgcolor=tema.PANEL, on_change=lambda e: self.ir(self.PANTALLAS[e.control.selected_index][0]),
            leading=ft.Container(ft.Column([
                ft.Icon(ft.Icons.STOREFRONT, size=30, color=tema.ACENTO),
                ft.Text("Marketplace\nbot", size=11, text_align=ft.TextAlign.CENTER, color=tema.TENUE),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4), padding=ft.Padding.only(top=18, bottom=12)),
            trailing=ft.Container(ft.Text(f"v{VERSION}", size=10, color=tema.TENUE), padding=ft.Padding.only(bottom=12)),
            pin_trailing_to_bottom=True,
            destinations=[ft.NavigationRailDestination(icon=i, selected_icon=s, label=t) for _, t, i, s in self.PANTALLAS],
        )
        self.cuerpo = ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=28, vertical=22))
        self.principal = ft.Row([self.riel, ft.VerticalDivider(width=1, color=tema.BORDE), self.cuerpo],
                                expand=True, spacing=0)
        page.add(self.principal)
        self.ir("hoy")

    # ---------- navegacion ----------
    def ir(self, nombre, **kwargs):
        if self.ejecutor.corriendo and nombre != "hoy":
            self.avisar("El bot está trabajando. Esperá a que termine o detenelo.")
            return
        claves = [p[0] for p in self.PANTALLAS]
        if nombre in claves:
            self.riel.selected_index = claves.index(nombre)
        self.actual = nombre
        vista = VistaEditor(self, **kwargs) if nombre == "editor" else self.vistas[nombre]
        self.cuerpo.content = vista.construir()
        self.vista_actual = vista
        self.page.update()

    def refrescar(self):
        if getattr(self, "vista_actual", None) and hasattr(self.vista_actual, "refrescar"):
            self.vista_actual.refrescar()
        self.page.update()

    # ---------- plantillas y seleccion ----------
    def recargar_plantillas(self):
        self.plantillas = plantillas.listar(self.rutas.plantillas)
        existentes = {p.nombre for p in self.plantillas}
        if self.seleccion - existentes:
            self.seleccion &= existentes
            guardar_seleccion(self.seleccion)

    def marcadas(self):
        return [p for p in self.plantillas if p.nombre in self.seleccion]

    def marcar(self, nombre, valor):
        if valor:
            self.seleccion.add(nombre)
        else:
            self.seleccion.discard(nombre)
        guardar_seleccion(self.seleccion)

    # ---------- mensajes ----------
    def avisar(self, texto, color=None):
        self.page.show_dialog(ft.SnackBar(ft.Text(texto, color=tema.TEXTO), bgcolor=color or tema.TARJETA,
                                          behavior=ft.SnackBarBehavior.FLOATING, width=520))

    def preguntar(self, titulo, texto, si, al_si, peligro=False):
        def responder(ok):
            self.page.pop_dialog()
            if ok:
                al_si()

        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=ft.Text(titulo), content=ft.Text(texto, width=440),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: responder(False)),
                ft.FilledButton(si, on_click=lambda e: responder(True),
                                style=ft.ButtonStyle(bgcolor=tema.PELIGRO) if peligro else None),
            ], actions_alignment=ft.MainAxisAlignment.END,
        ))

    # ---------- correr el bot ----------
    def empezar(self, accion, lista=None):
        """accion: publicar | probar | borrar | borrar_y_publicar."""
        if self.ejecutor.corriendo:
            return
        lista = lista if lista is not None else self.marcadas()
        if accion != "borrar" and not lista:
            self.avisar("Marcá al menos una plantilla para publicar (pantalla Plantillas).")
            return
        con_problemas = [p for p in lista if plantillas.problemas(p, self.rutas)]
        if accion != "borrar" and con_problemas:
            nombres = "\n".join(f"• {p.titulo}: {plantillas.problemas(p, self.rutas)[0]}" for p in con_problemas[:5])
            self.preguntar("Hay plantillas con problemas",
                           f"Estas van a fallar:\n{nombres}\n\n¿Seguir igual con las demás?",
                           "Seguir sin esas", lambda: self.empezar(accion, [p for p in lista if p not in con_problemas]))
            return
        if accion == "borrar":
            corrida = self.ejecutor.borrar(confirmar=True)
        elif accion == "probar":
            corrida = self.ejecutor.publicar(lista, confirmar=False)
        else:
            corrida = self.ejecutor.publicar(lista, confirmar=True, borrar_antes=accion == "borrar_y_publicar")
        if corrida:
            self._modo_trabajo(True)

    def detener(self):
        self.ejecutor.detener()

    def _modo_trabajo(self, activo):
        ventana = self.page.window
        if activo:
            self.ir("hoy")
            if self.ajustes.barrita_progreso:
                self._geometria = (ventana.width, ventana.height, ventana.left, ventana.top, ventana.maximized)
                ventana.maximized = False
                ventana.width, ventana.height = BarritaProgreso.ANCHO, BarritaProgreso.ALTO
                ventana.left = max(0, (ancho_pantalla() - BarritaProgreso.ANCHO) // 2)
                ventana.top = 0
                ventana.always_on_top = True
                ventana.title_bar_hidden = True
                self.page.controls[:] = [self.barrita.construir()]
            else:
                ventana.minimized = True
        else:
            if self._geometria:
                ancho, alto, izq, arriba, maximizada = self._geometria
                ventana.always_on_top = False
                ventana.title_bar_hidden = False
                ventana.width, ventana.height = ancho, alto
                if izq is not None and arriba is not None:
                    ventana.left, ventana.top = izq, arriba
                ventana.maximized = bool(maximizada)
                self._geometria = None
            ventana.minimized = False
            self.page.controls[:] = [self.principal]
            self.ir("hoy")
        self.page.update()

    # Estas tres las llama el Ejecutor desde otro hilo: pasamos al hilo de la ventana.
    def _al_linea(self, texto):
        self.page.run_task(self._actualizar)

    def _al_cambio(self, corrida):
        self.page.run_task(self._actualizar)

    def _al_terminar(self, corrida):
        self.page.run_task(self._terminado, corrida)

    async def _actualizar(self):
        if self._geometria:
            self.barrita.refrescar()
        elif self.actual == "hoy":
            self.vistas["hoy"].refrescar()
        self.page.update()

    async def _terminado(self, corrida):
        self.recargar_plantillas()
        self._modo_trabajo(False)
        exitos, fallos = len(corrida.exitosos), len(corrida.fallidos)
        partes = []
        if corrida.accion in ("borrar", "borrar_y_publicar"):
            partes.append(f"{corrida.borradas} borradas")
        if corrida.resultados:
            partes.append(f"{exitos} bien")
            if fallos:
                partes.append(f"{fallos} " + ("falló" if fallos == 1 else "fallaron"))
        self.avisar("Listo: " + ", ".join(partes) if partes else (corrida.mensaje_final or "Listo"),
                    tema.PELIGRO if fallos else None)


def main():
    ft.run(App)
