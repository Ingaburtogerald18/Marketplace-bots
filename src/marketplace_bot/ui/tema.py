"""Colores y piezas visuales que se repiten en todas las pantallas."""
import flet as ft

FONDO = "#111315"
PANEL = "#1a1d21"
TARJETA = "#20242a"
BORDE = "#2c3139"
TEXTO = "#e9ebee"
TENUE = "#9aa3ad"
ACENTO = "#3d8bfd"
EXITO = "#3fb950"
ALERTA = "#d29922"
PELIGRO = "#f85149"


def tema():
    return ft.Theme(color_scheme_seed=ACENTO, font_family="Segoe UI")


def titulo(texto, subtitulo=None):
    controles = [ft.Text(texto, size=26, weight=ft.FontWeight.BOLD, color=TEXTO)]
    if subtitulo:
        controles.append(ft.Text(subtitulo, size=13, color=TENUE))
    return ft.Column(controles, spacing=2)


def seccion(texto):
    return ft.Text(texto, size=15, weight=ft.FontWeight.W_600, color=TEXTO)


def tarjeta(contenido, padding=16, expand=None, ancho=None):
    return ft.Container(content=contenido, bgcolor=TARJETA, border_radius=14, padding=padding,
                        border=ft.Border.all(1, BORDE), expand=expand, width=ancho)


def chip(texto, color=TENUE, icono=None):
    fila = [ft.Text(texto, size=12, color=color, weight=ft.FontWeight.W_500)]
    if icono:
        fila.insert(0, ft.Icon(icono, size=14, color=color))
    return ft.Container(content=ft.Row(fila, spacing=4, tight=True), border_radius=20,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        border=ft.Border.all(1, color))


def precio(texto):
    return f"C$ {int(texto):,}" if str(texto).isdigit() else f"C$ {texto}"


ESTADOS_ARTICULO = {
    # estado: (icono, color, texto)
    "pendiente": (ft.Icons.SCHEDULE, TENUE, "En espera"),
    "trabajando": (ft.Icons.AUTORENEW, ACENTO, "Trabajando…"),
    "publicado": (ft.Icons.CHECK_CIRCLE, EXITO, "Publicado"),
    "probado": (ft.Icons.CHECK_CIRCLE_OUTLINE, EXITO, "Prueba bien"),
    "fallo": (ft.Icons.ERROR, PELIGRO, "Falló"),
    "saltado": (ft.Icons.REMOVE_CIRCLE_OUTLINE, TENUE, "No se hizo"),
}
