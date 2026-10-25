"""Pantalla principal: lo que sale hoy, la revision previa y el ultimo resultado."""
import sys
from datetime import datetime

import flet as ft

from ... import plantillas as plantillas_mod
from ...motor import navegador
from ...registros import ACCIONES, leer_corridas
from .. import tema
from ..miniaturas import miniatura

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]


def fecha_bonita(fecha):
    return f"{DIAS[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"



def cuantas_borrar(ajustes):
    return f"hasta {ajustes.max_borrar} publicaciones" if ajustes.max_borrar else "todas tus publicaciones"

class VistaHoy:
    def __init__(self, app):
        self.app = app

    def construir(self):
        self.contenedor = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=18,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.refrescar()
        return self.contenedor

    def refrescar(self):
        app = self.app
        corrida = app.ejecutor.corrida if app.ejecutor.corriendo else None
        marcadas = app.marcadas()
        self.contenedor.controls = [
            ft.Row([
                tema.titulo("Hoy", fecha_bonita(datetime.now()).capitalize()),
                ft.Container(expand=True),
                tema.chip(f"{len(marcadas)} de {len(app.plantillas)} plantillas marcadas", tema.TENUE,
                          ft.Icons.CHECK_BOX_OUTLINED),
            ]),
            self._trabajando(corrida) if corrida else self._acciones(marcadas),
            ft.Row([self._marcadas(marcadas), self._revision(marcadas)],
                   vertical_alignment=ft.CrossAxisAlignment.START, spacing=18),
            self._ultimo_resultado(),
        ]

    # ---------- botones grandes ----------
    def _acciones(self, marcadas):
        app = self.app
        n = len(marcadas)
        principal = ft.FilledButton(
            content=ft.Row([ft.Icon(ft.Icons.AUTORENEW, size=22),
                            ft.Column([ft.Text("Renovar mis publicaciones", size=17, weight=ft.FontWeight.BOLD),
                                       ft.Text(f"Borra las viejas y publica {n} marcadas", size=12)],
                                      spacing=0, tight=True)], tight=True, spacing=12),
            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=26, vertical=18),
                                 shape=ft.RoundedRectangleBorder(radius=14)),
            on_click=lambda e: app.preguntar(
                "Renovar publicaciones",
                f"Voy a borrar {cuantas_borrar(app.ajustes)} y luego publicar {n}.\n\n"
                "Mientras trabajo no toqués el mouse ni el teclado. Para detenerme, llevá el mouse a una esquina.",
                "Empezar", lambda: app.empezar("borrar_y_publicar")),
            disabled=n == 0,
        )

        def secundario(texto, icono, accion, mensaje=None, peligro=False):
            def clic(e):
                if mensaje:
                    app.preguntar(texto, mensaje, "Empezar", lambda: app.empezar(accion), peligro)
                else:
                    app.empezar(accion)
            return ft.OutlinedButton(content=texto, icon=icono, on_click=clic,
                                     style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=18, vertical=16)))

        return tema.tarjeta(ft.Row([
            principal,
            ft.Container(width=8),
            secundario("Solo publicar", ft.Icons.UPLOAD, "publicar", f"¿Publicar {n} artículo(s) sin borrar nada?"),
            secundario("Solo borrar", ft.Icons.DELETE_SWEEP_OUTLINED, "borrar",
                       f"¿Borrar {cuantas_borrar(app.ajustes)} de Marketplace?", peligro=True),
            secundario("Probar sin publicar", ft.Icons.SCIENCE_OUTLINED, "probar"),
        ], wrap=True, spacing=10, run_spacing=10), padding=20)

    def _trabajando(self, corrida):
        actual, total, ronda = corrida.progreso
        trabajando = next((r for r in corrida.resultados.values() if r.estado == "trabajando"), None)
        if trabajando:
            texto = trabajando.titulo
        else:
            texto = "Borrando publicaciones…" if corrida.accion != "publicar" else "Preparando…"
        return tema.tarjeta(ft.Column([
            ft.Row([ft.ProgressRing(width=22, height=22, stroke_width=3),
                    ft.Text(ACCIONES.get(corrida.accion, ""), size=17, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.FilledButton("Detener", icon=ft.Icons.STOP, on_click=lambda e: self.app.detener(),
                                    style=ft.ButtonStyle(bgcolor=tema.PELIGRO))]),
            ft.ProgressBar(value=(actual / total) if total else None),
            ft.Text(f"Artículo {actual} de {total}" + (" (reintento)" if ronda > 1 else "") + f" · {texto}"
                    if total else texto, color=tema.TENUE),
            *([ft.Text(f"Borradas: {corrida.borradas}", color=tema.TENUE)] if corrida.borradas else []),
        ], spacing=10), padding=20)

    # ---------- lo marcado ----------
    def _marcadas(self, marcadas):
        app = self.app
        filas = []
        for p in marcadas:
            foto = miniatura(p.portada, 120) if p.portada else None
            problemas = plantillas_mod.problemas(p, app.rutas)
            filas.append(ft.Container(ft.Row([
                ft.Container(ft.Image(src=foto, width=52, height=52, fit=ft.BoxFit.COVER, border_radius=8)
                             if foto else ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, color=tema.TENUE),
                             width=52, height=52, border_radius=8, bgcolor=tema.PANEL),
                ft.Column([ft.Text(p.titulo, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, weight=ft.FontWeight.W_500),
                           ft.Text(f"{tema.precio(p.precio)} · {len(p.fotos)} fotos" +
                                   (f" · ⚠ {problemas[0]}" if problemas else ""),
                                   size=12, color=tema.ALERTA if problemas else tema.TENUE)],
                          spacing=2, expand=True),
                ft.IconButton(ft.Icons.CLOSE, icon_size=18, tooltip="Quitar de hoy",
                              on_click=lambda e, n=p.nombre: (app.marcar(n, False), app.refrescar())),
            ], spacing=12), padding=ft.Padding.symmetric(vertical=4)))
        if not filas:
            filas = [ft.Text("No marcaste nada todavía.", color=tema.TENUE)]
        return tema.tarjeta(ft.Column([
            ft.Row([tema.seccion("Lo que sale hoy"), ft.Container(expand=True),
                    ft.TextButton("Elegir plantillas", icon=ft.Icons.EDIT_NOTE, on_click=lambda e: app.ir("plantillas"))]),
            ft.Column(filas, spacing=2, scroll=ft.ScrollMode.AUTO, height=min(360, 64 * max(1, len(filas)) + 8)),
        ], spacing=8), expand=3)

    # ---------- revision previa ----------
    def _revision(self, marcadas):
        app = self.app
        lineas = []

        def linea(ok, texto, detalle=""):
            icono, color = ((ft.Icons.CHECK_CIRCLE, tema.EXITO) if ok is True else
                            (ft.Icons.WARNING_AMBER, tema.ALERTA) if ok is None else (ft.Icons.CANCEL, tema.PELIGRO))
            lineas.append(ft.Row([ft.Icon(icono, color=color, size=20),
                                  ft.Column([ft.Text(texto, weight=ft.FontWeight.W_500),
                                             *([ft.Text(detalle, size=12, color=tema.TENUE)] if detalle else [])],
                                            spacing=0, expand=True)], vertical_alignment=ft.CrossAxisAlignment.START))

        if sys.platform == "win32":
            ventanas = navegador.listar()
            con_facebook = [v for v in ventanas if "Facebook" in v]
            elegida = app.ajustes.ventana
            if elegida:
                encontrada = any(elegida.lower() in v.lower() for v in ventanas)
                linea(encontrada, f"Cuenta elegida: {elegida}",
                      "Abierta" if encontrada else "No la veo abierta. Abrí Facebook en ese navegador/perfil.")
            elif con_facebook:
                perfiles = sorted({navegador.perfil(v) for v in con_facebook})
                if len(perfiles) > 1:
                    linea(None, "Facebook está abierto en varios perfiles",
                          ", ".join(perfiles) + ". Elegí cuál usar en Ajustes.")
                else:
                    linea(True, f"Facebook abierto en {perfiles[0]}")
            else:
                linea(None, "No veo Facebook abierto", "Abrilo en tu navegador antes de empezar.")
        else:
            linea(None, "Navegador", "La revisión del navegador solo funciona en Windows.")

        con_problemas = [(p, plantillas_mod.problemas(p, app.rutas)) for p in marcadas]
        con_problemas = [(p, pr) for p, pr in con_problemas if pr]
        if marcadas and not con_problemas:
            linea(True, "Las plantillas marcadas están completas")
        for p, pr in con_problemas[:4]:
            linea(False, p.titulo, pr[0])
        linea(True if app.ajustes.max_grupos <= 10 else None, f"Hasta {app.ajustes.max_grupos} grupos por artículo",
              "Menos grupos = menos riesgo de que Facebook lo vea como spam." if app.ajustes.max_grupos > 10 else "")
        lineas.append(ft.Text("Si usás Edge: apagá «Guardar y rellenar información personal» "
                              "(edge://settings/personalinfo) para que no tape el formulario.",
                              size=12, color=tema.TENUE))
        return tema.tarjeta(ft.Column([tema.seccion("Revisión antes de empezar"), *lineas], spacing=10), expand=2)

    # ---------- ultimo resultado ----------
    def _ultimo_resultado(self):
        app = self.app
        corridas = leer_corridas(app.rutas, limite=1)
        if not corridas or app.ejecutor.corriendo:
            return ft.Container()
        c = corridas[0]
        resultados = c["resultados"]
        bien = [r for r in resultados if r.ok]
        mal = [r for r in resultados if r.estado == "fallo"]
        inicio = datetime.fromisoformat(c["inicio"])
        chips = []
        if c["accion"] in ("borrar", "borrar_y_publicar"):
            chips.append(tema.chip(f"{c.get('borradas', 0)} borradas", tema.TENUE, ft.Icons.DELETE_OUTLINE))
        if resultados:
            chips.append(tema.chip(f"{len(bien)} bien", tema.EXITO, ft.Icons.CHECK))
        if mal:
            chips.append(tema.chip(f"{len(mal)} " + ("falló" if len(mal) == 1 else "fallaron"), tema.PELIGRO, ft.Icons.CLOSE))
        filas = []
        for r in mal:
            filas.append(ft.Row([
                ft.Icon(ft.Icons.ERROR, color=tema.PELIGRO, size=18),
                ft.Column([ft.Text(r.titulo or r.carpeta, weight=ft.FontWeight.W_500),
                           ft.Text(r.detalle, size=12, color=tema.TENUE)], spacing=0, expand=True),
                *([ft.TextButton("Ver captura", icon=ft.Icons.IMAGE_OUTLINED,
                                 on_click=lambda e, ruta=r.captura: _abrir(ruta))] if r.captura else []),
            ]))
        botones = []
        reintentables = [p for p in app.plantillas if p.nombre in {r.carpeta for r in mal}]
        if reintentables and c["accion"] != "probar":
            botones.append(ft.FilledButton(f"Reintentar los que fallaron ({len(reintentables)})", icon=ft.Icons.REPLAY,
                                           on_click=lambda e: app.empezar("publicar", reintentables)))
        mensaje = c.get("mensaje_borrar") or c.get("mensaje") or ""
        return tema.tarjeta(ft.Column([
            ft.Row([tema.seccion(f"Última vez: {ACCIONES.get(c['accion'], c['accion'])} · "
                                 f"{fecha_bonita(inicio)}, {inicio:%H:%M}"),
                    ft.Container(expand=True), *chips]),
            *([ft.Text(mensaje, color=tema.TENUE)] if mensaje else []),
            *filas,
            ft.Row(botones + [ft.TextButton("Ver historial", on_click=lambda e: app.ir("historial"))]),
        ], spacing=10))


def _abrir(ruta):
    from ..app import abrir

    abrir(ruta)
