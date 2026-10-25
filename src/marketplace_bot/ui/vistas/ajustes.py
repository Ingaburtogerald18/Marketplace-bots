"""Ajustes de esta PC: cuenta/navegador, grupos, pausas, contacto."""
import flet as ft

from ... import VERSION, plantillas as plantillas_mod
from ...motor import navegador
from .. import tema


class VistaAjustes:
    def __init__(self, app):
        self.app = app

    def construir(self):
        from ..app import abrir

        app, a = self.app, self.app.ajustes

        def guardar(**cambios):
            for clave, valor in cambios.items():
                setattr(a, clave, valor)
            a.guardar()

        # --- cuenta ---
        perfiles = sorted({navegador.perfil(t) for t in navegador.listar() if "Facebook" in t})
        if a.ventana and a.ventana not in perfiles:
            perfiles.append(a.ventana)
        ventana = ft.Dropdown(
            label="Ventana de Facebook a usar", value=a.ventana or "", width=460,
            options=[ft.DropdownOption(key="", text="Automático (la primera que encuentre)")] +
            [ft.DropdownOption(key=p, text=p) for p in perfiles],
            on_select=lambda e: guardar(ventana=e.control.value or ""))

        # --- publicacion ---
        etiqueta_grupos = ft.Text(f"{a.max_grupos} grupos por artículo")

        def cambiar_grupos(e):
            valor = int(e.control.value)
            etiqueta_grupos.value = f"{valor} grupos por artículo"
            guardar(max_grupos=valor)
            etiqueta_grupos.update()

        def numero(etiqueta, clave, ancho=150, minimo=0):
            def cambiar(e):
                texto = e.control.value or ""
                if texto.isdigit() and int(texto) >= minimo:
                    guardar(**{clave: int(texto)})
            return ft.TextField(label=etiqueta, value=str(getattr(a, clave)), width=ancho,
                                input_filter=ft.NumbersOnlyInputFilter(), on_change=cambiar)

        firma = ft.TextField(label="Mi contacto", value=plantillas_mod.leer_firma(app.rutas), multiline=True,
                             min_lines=4, max_lines=8, width=620,
                             helper="Se agrega con un botón al final de la descripción. Se comparte con las otras PCs.")

        def guardar_firma(e):
            plantillas_mod.guardar_firma(app.rutas, firma.value or "")
            app.avisar("Guardé tu contacto.")

        def redetectar(e):
            guardar(escala=0)
            app.avisar("La próxima vez el bot vuelve a medir el tamaño de tu pantalla.")
            app.ir("ajustes")

        async def cambiar_carpeta(e):
            carpeta = await ft.FilePicker().get_directory_path(
                dialog_title="Elegí la carpeta del Marketplace bot (la que tiene «publicaciones»)")
            if not carpeta:
                return
            guardar(carpeta_datos=carpeta)
            app.avisar("Listo. Cerrá y abrí la ventana para usar la carpeta nueva.")
            app.ir("ajustes")

        escala = f"{a.escala:.0%}" if a.escala else "todavía no medido"
        bloques = [
            tema.titulo("Ajustes", "Se guardan solo en esta PC."),
            tema.tarjeta(ft.Column([
                tema.seccion("Cuenta y navegador"),
                ft.Text("Si tenés Facebook abierto en varios perfiles (por ejemplo «Work» y «Personal»), elegí cuál "
                        "usar. Así el bot nunca publica en la cuenta equivocada.", color=tema.TENUE, size=13),
                ft.Row([ventana, ft.TextButton("Buscar de nuevo", icon=ft.Icons.REFRESH,
                                               on_click=lambda e: app.ir("ajustes"))]),
            ], spacing=10)),
            tema.tarjeta(ft.Column([
                tema.seccion("Al publicar"),
                ft.Row([etiqueta_grupos, ft.Slider(value=a.max_grupos, min=1, max=20, divisions=19, width=360,
                                                   label="{value}", on_change_end=cambiar_grupos)]),
                ft.Text("Recomendado: 5 a 10 grupos relevantes. Publicar lo mismo en muchos grupos a diario "
                        "es lo que Facebook castiga como spam.", size=12, color=tema.TENUE),
                ft.Row([numero("Pausa mínima (s)", "pausa_min"), numero("Pausa máxima (s)", "pausa_max")]),
                ft.Switch(label="Reintentar una vez los artículos que fallen", value=a.reintentar_fallidos,
                          on_change=lambda e: guardar(reintentar_fallidos=e.control.value)),
                ft.Switch(label="Achicar las fotos antes de subirlas (más rápido)", value=a.reducir_fotos,
                          on_change=lambda e: guardar(reducir_fotos=e.control.value)),
            ], spacing=12)),
            tema.tarjeta(ft.Column([
                tema.seccion("Al borrar y mientras trabaja"),
                numero("Máximo a borrar por vez (0 = todas)", "max_borrar", 260, minimo=0),
                ft.Switch(label="Mostrar una barrita de progreso arriba de la pantalla (si no, la ventana se minimiza)",
                          value=a.barrita_progreso, on_change=lambda e: guardar(barrita_progreso=e.control.value)),
                ft.Row([ft.Text(f"Tamaño de pantalla detectado: {escala}", color=tema.TENUE),
                        ft.TextButton("Volver a medir", on_click=redetectar)]),
            ], spacing=12)),
            tema.tarjeta(ft.Column([
                tema.seccion("Mi contacto"),
                firma,
                ft.FilledButton("Guardar contacto", icon=ft.Icons.SAVE, on_click=guardar_firma),
            ], spacing=12)),
            tema.tarjeta(ft.Column([
                tema.seccion("Carpetas"),
                ft.Text(f"Plantillas: {app.rutas.plantillas}", selectable=True, size=13),
                ft.Text(f"Registros: {app.rutas.registros}", selectable=True, size=13),
                ft.Row([ft.OutlinedButton("Abrir plantillas", icon=ft.Icons.FOLDER_OPEN,
                                          on_click=lambda e: abrir(app.rutas.plantillas)),
                        ft.OutlinedButton("Abrir registros", icon=ft.Icons.FOLDER_OPEN,
                                          on_click=lambda e: abrir(app.rutas.registros)),
                        ft.TextButton("Usar otra carpeta…", on_click=cambiar_carpeta)]),
                ft.Text(f"Versión {VERSION}", size=12, color=tema.TENUE),
            ], spacing=10)),
        ]
        return ft.Column(bloques, spacing=16, scroll=ft.ScrollMode.AUTO, expand=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
