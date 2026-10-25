"""La barrita que queda arriba de la pantalla mientras el bot trabaja.

Es chiquita, siempre visible y no dice palabras de botones de Facebook, para
que el bot no la confunda con la pagina.
"""
import flet as ft

from .. import tema


class BarritaProgreso:
    ANCHO = 560
    ALTO = 76

    def __init__(self, app):
        self.app = app
        self.texto = ft.Text("Empezando…", size=13, weight=ft.FontWeight.W_600, max_lines=1,
                             overflow=ft.TextOverflow.ELLIPSIS)
        self.detalle = ft.Text("No toqués el mouse. Mouse a una esquina = parar.", size=11, color=tema.TENUE,
                               max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        self.barra = ft.ProgressBar(value=None, bar_height=4)

    def construir(self):
        self.refrescar()
        return ft.Container(ft.Column([
            ft.Row([
                ft.ProgressRing(width=18, height=18, stroke_width=2.5),
                ft.Column([self.texto, self.detalle], spacing=0, expand=True),
                ft.FilledButton("Detener", icon=ft.Icons.STOP, on_click=lambda e: self.app.detener(),
                                style=ft.ButtonStyle(bgcolor=tema.PELIGRO, padding=ft.Padding.symmetric(horizontal=14))),
            ], spacing=12),
            self.barra,
        ], spacing=8), padding=ft.Padding.symmetric(horizontal=14, vertical=10), bgcolor=tema.PANEL, expand=True)

    def refrescar(self):
        corrida = self.app.ejecutor.corrida
        if not corrida:
            return
        actual, total, ronda = corrida.progreso
        trabajando = next((r for r in corrida.resultados.values() if r.estado == "trabajando"), None)
        if trabajando:
            self.texto.value = f"{actual} de {total}" + (" · reintento" if ronda > 1 else "") + f" · {trabajando.titulo}"
            self.barra.value = (actual - 1) / total if total else None
        elif corrida.accion in ("borrar", "borrar_y_publicar") and not any(
                r.estado != "pendiente" for r in corrida.resultados.values()):
            self.texto.value = f"Quitando publicaciones viejas · {corrida.borradas} listas"
            self.barra.value = None
        hechos = sum(1 for r in corrida.resultados.values() if r.ok)
        fallos = len(corrida.fallidos)
        if total:
            self.detalle.value = f"{hechos} bien" + (f" · {fallos} con problema" if fallos else "") + \
                " · Mouse a una esquina = parar"
