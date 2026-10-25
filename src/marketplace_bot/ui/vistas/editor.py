"""Crear o editar una plantilla: datos, descripcion y fotos (con vista previa)."""
from pathlib import Path

import flet as ft

from ... import plantillas as plantillas_mod
from ...modelos import ESTADOS_FB, MAX_FOTOS, Plantilla
from .. import tema
from ..miniaturas import miniatura

OTRA = "__otra__"


class VistaEditor:
    def __init__(self, app, plantilla=None):
        self.app = app
        self.original = plantilla
        self.fotos = [str(f) for f in plantilla.fotos] if plantilla else []

    def construir(self):
        app = self.app
        p = self.original or Plantilla(carpeta=Path())
        conocidas = app.rutas.categorias_conocidas()
        categoria = p.categoria or (conocidas[0] if conocidas else "")

        self.titulo = ft.TextField(label="Título", value=p.titulo, max_length=100, on_change=self._vista_previa)
        self.precio = ft.TextField(label="Precio", prefix=ft.Text("C$ "), value=p.precio, width=200,
                                   input_filter=ft.NumbersOnlyInputFilter(), on_change=self._vista_previa,
                                   helper="Solo números (puede ser 0)")
        self.categoria = ft.Dropdown(label="Categoría", value=categoria if categoria in conocidas else OTRA, expand=True,
                                     options=[ft.DropdownOption(key=c, text=c) for c in conocidas] +
                                     [ft.DropdownOption(key=OTRA, text="Otra categoría…")],
                                     on_select=self._cambio_categoria)
        self.otra = ft.TextField(label="Nombre exacto de la categoría en Facebook",
                                 value="" if categoria in conocidas else categoria,
                                 visible=categoria not in conocidas,
                                 helper="El bot se detendrá la primera vez y guardará una captura para aprenderla.")
        self.estado = ft.Dropdown(label="Estado", value=p.estado if p.estado in ESTADOS_FB else "Nuevo", width=240,
                                  options=[ft.DropdownOption(key=e, text=e) for e in ESTADOS_FB])
        self.descripcion = ft.TextField(label="Descripción", value=p.descripcion, multiline=True, min_lines=12,
                                        max_lines=22, on_change=self._vista_previa)
        self.errores = ft.Text(color=tema.PELIGRO, visible=False)
        self.lista_fotos = ft.Row(wrap=True, spacing=10, run_spacing=10)
        self.previa = ft.Column(spacing=6, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self._pintar_fotos()
        self._vista_previa()

        formulario = ft.Column([
            self.titulo,
            ft.Row([self.precio, self.estado], spacing=16, vertical_alignment=ft.CrossAxisAlignment.START),
            self.categoria, self.otra,
            self.descripcion,
            ft.Row([ft.TextButton("Agregar mi contacto al final", icon=ft.Icons.CONTACT_PHONE_OUTLINED,
                                  on_click=self._agregar_firma),
                    ft.Text("(se edita en Ajustes)", size=12, color=tema.TENUE)]),
        ], spacing=14, expand=3, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        fotos = ft.Column([
            tema.tarjeta(self.previa, padding=12),
            ft.Row([tema.seccion("Fotos"), ft.Text("la 1.ª es la portada", size=12, color=tema.TENUE),
                    ft.Container(expand=True),
                    ft.OutlinedButton("Agregar fotos", icon=ft.Icons.ADD_PHOTO_ALTERNATE, on_click=self._agregar_fotos)]),
            self.lista_fotos,
        ], spacing=12, expand=2, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        return ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Volver", on_click=lambda e: app.ir("plantillas")),
                tema.titulo("Editar plantilla" if self.original else "Nueva plantilla"),
                ft.Container(expand=True),
                self.errores,
                ft.TextButton("Cancelar", on_click=lambda e: app.ir("plantillas")),
                ft.FilledButton("Guardar", icon=ft.Icons.SAVE, on_click=self._guardar),
            ]),
            ft.Row([formulario, fotos], expand=True, spacing=28, vertical_alignment=ft.CrossAxisAlignment.START),
        ], expand=True, spacing=16)

    # ---------- categoria ----------
    def _cambio_categoria(self, e):
        self.otra.visible = self.categoria.value == OTRA
        self.app.page.update()

    def _categoria_elegida(self):
        return self.otra.value.strip() if self.categoria.value == OTRA else (self.categoria.value or "")

    # ---------- descripcion ----------
    def _agregar_firma(self, e):
        firma = plantillas_mod.leer_firma(self.app.rutas)
        if not firma:
            self.app.avisar("Todavía no guardaste tu contacto. Escribilo en Ajustes › Mi contacto.")
            return
        texto = self.descripcion.value.rstrip()
        if firma in texto:
            self.app.avisar("La descripción ya tiene tu contacto.")
            return
        self.descripcion.value = (texto + "\n\n" + firma) if texto else firma
        self._vista_previa()
        self.app.page.update()

    # ---------- fotos ----------
    def _pintar_fotos(self):
        controles = []
        for i, ruta in enumerate(self.fotos):
            datos = miniatura(ruta, 240)
            controles.append(ft.Container(ft.Column([
                ft.Stack([
                    ft.Image(src=datos, width=132, height=132, fit=ft.BoxFit.COVER, border_radius=10) if datos else
                    ft.Container(ft.Icon(ft.Icons.BROKEN_IMAGE), width=132, height=132, bgcolor=tema.PANEL,
                                 alignment=ft.Alignment.CENTER),
                    ft.Container(ft.Text("Portada" if i == 0 else str(i + 1), size=11, color=tema.TEXTO),
                                 bgcolor="#cc000000" if i else tema.ACENTO, border_radius=10,
                                 padding=ft.Padding.symmetric(horizontal=8, vertical=2), left=6, top=6),
                ], width=132, height=132),
                ft.Row([
                    ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_size=18, tooltip="Antes", disabled=i == 0,
                                  on_click=lambda e, i=i: self._mover(i, -1)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, icon_size=18, tooltip="Quitar",
                                  on_click=lambda e, i=i: self._quitar(i)),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=18, tooltip="Después",
                                  disabled=i == len(self.fotos) - 1, on_click=lambda e, i=i: self._mover(i, 1)),
                ], spacing=0, alignment=ft.MainAxisAlignment.CENTER, width=132),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)))
        if not controles:
            controles = [ft.Text("Sin fotos todavía.", color=tema.TENUE)]
        if len(self.fotos) > MAX_FOTOS:
            controles.insert(0, ft.Text(f"Facebook acepta {MAX_FOTOS} fotos; quitá {len(self.fotos) - MAX_FOTOS}.",
                                        color=tema.ALERTA))
        self.lista_fotos.controls = controles

    def _mover(self, i, paso):
        j = i + paso
        if 0 <= j < len(self.fotos):
            self.fotos[i], self.fotos[j] = self.fotos[j], self.fotos[i]
            self._pintar_fotos()
            self._vista_previa()
            self.app.page.update()

    def _quitar(self, i):
        del self.fotos[i]
        self._pintar_fotos()
        self._vista_previa()
        self.app.page.update()

    async def _agregar_fotos(self, e):
        archivos = await ft.FilePicker().pick_files(
            dialog_title="Elegir fotos", allow_multiple=True, file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["jpg", "jpeg", "png", "heic", "heif"])
        nuevas = [a.path for a in archivos or [] if a.path]
        if not nuevas:
            return
        self.fotos.extend(nuevas)
        self._pintar_fotos()
        self._vista_previa()
        self.app.page.update()

    # ---------- vista previa ----------
    def _vista_previa(self, e=None):
        portada = miniatura(self.fotos[0], 480) if self.fotos else None
        precio = self.precio.value if hasattr(self, "precio") else ""
        self.previa.controls = [
            ft.Text("Así se verá", size=12, color=tema.TENUE),
            ft.Image(src=portada, height=200, fit=ft.BoxFit.COVER, border_radius=10) if portada else
            ft.Container(ft.Text("Sin portada", color=tema.TENUE), height=120, alignment=ft.Alignment.CENTER,
                         bgcolor=tema.PANEL, border_radius=10),
            ft.Text(self.titulo.value or "Título", size=16, weight=ft.FontWeight.BOLD, max_lines=2),
            ft.Text(tema.precio(precio or "0"), size=15, weight=ft.FontWeight.BOLD, color=tema.ACENTO),
            ft.Text((self.descripcion.value or "")[:220] + ("…" if len(self.descripcion.value or "") > 220 else ""),
                    size=12, color=tema.TENUE),
        ]
        if e is not None:
            self.previa.update()

    # ---------- guardar ----------
    def _guardar(self, e):
        app = self.app
        titulo = self.titulo.value.strip()
        precio = (self.precio.value or "").strip()
        categoria = self._categoria_elegida()
        faltan = [n for n, v in (("título", titulo), ("precio", precio), ("categoría", categoria)) if not v]
        error = ("Falta: " + ", ".join(faltan)) if faltan else ("Agregá al menos una foto." if not self.fotos else "")
        if error:
            self.errores.value, self.errores.visible = error, True
            app.page.update()
            return
        carpeta = self.original.carpeta if self.original else app.rutas.plantillas / plantillas_mod.nombre_carpeta(
            titulo, app.rutas.plantillas)
        nueva = Plantilla(carpeta=carpeta, titulo=titulo, precio=precio, categoria=categoria,
                          estado=self.estado.value or "Nuevo", descripcion=self.descripcion.value or "")
        try:
            plantillas_mod.guardar(nueva, self.fotos)
        except Exception as ex:  # noqa: BLE001 - mostrar cualquier error
            self.errores.value, self.errores.visible = f"No se pudo guardar: {ex}", True
            app.page.update()
            return
        if not self.original:
            app.marcar(carpeta.name, True)  # lo nuevo casi siempre se quiere publicar
        app.recargar_plantillas()
        app.ir("plantillas")
        app.avisar(f"Guardé «{titulo}».")
