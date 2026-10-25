"""Linea de comandos del motor. La ventana lo llama asi (tambien sirve a mano):

    python -m marketplace_bot motor borrar --confirmar --max 20
    python -m marketplace_bot motor publicar --solo kz-edx-pro attack-shark-r1 --confirmar
    python -m marketplace_bot motor ventanas

Sin --confirmar es una prueba: llena todo pero no borra ni publica.
Para detenerlo de emergencia, lleva el mouse a una esquina de la pantalla.

Codigos de salida: 0 todo bien, 2 algun articulo fallo, 3 detenido, 1 error.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .. import config
from . import eventos


def _argumentos(argv):
    parser = argparse.ArgumentParser(prog="marketplace_bot motor")
    sub = parser.add_subparsers(dest="accion", required=True)

    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--confirmar", action="store_true", help="de verdad (sin esto es una prueba)")
    comunes.add_argument("--ventana", default=None, help="texto de la ventana del navegador a usar")
    comunes.add_argument("--registro", default=None, help="carpeta donde guardar capturas")
    comunes.add_argument("--escala", type=float, default=None, help="escala de Windows ya conocida (1.25 = 125 %%)")

    borrar = sub.add_parser("borrar", parents=[comunes])
    borrar.add_argument("--max", type=int, default=20, help="maximo a borrar por corrida")

    publicar = sub.add_parser("publicar", parents=[comunes])
    publicar.add_argument("--solo", nargs="+", required=True, help="carpetas de publicaciones/")
    publicar.add_argument("--max-grupos", type=int, default=None)
    publicar.add_argument("--pausa", type=int, nargs=2, default=None, metavar=("MIN", "MAX"))
    publicar.add_argument("--sin-reintento", action="store_true")
    publicar.add_argument("--fotos-originales", action="store_true", help="no reducir las fotos")

    sub.add_parser("ventanas")
    return parser.parse_args(argv)


def main(argv=None):
    eventos.configurar_salida()
    args = _argumentos(argv if argv is not None else sys.argv[1:])

    if args.accion == "ventanas":
        from . import navegador

        print(json.dumps(navegador.listar(), ensure_ascii=False))
        return 0

    from pyautogui import FailSafeException

    from .acciones import Acciones
    from .navegador import NavegadorNoEncontrado, preparar
    from .vision import Vision

    ajustes = config.Ajustes.cargar()
    rutas = config.Rutas(ajustes)
    registro = Path(args.registro) if args.registro else rutas.registros / f"{datetime.now():%Y-%m-%d_%H%M%S}_{args.accion}"
    registro.mkdir(parents=True, exist_ok=True)
    ventana = args.ventana if args.ventana is not None else ajustes.ventana

    vision = Vision(rutas.botones, escala=args.escala)
    acciones = Acciones()
    escala_inicial = vision.escala
    try:
        if args.accion == "borrar":
            from .borrar import URL_VENTAS, BorrarBot

            preparar(URL_VENTAS, ventana)
            bot = BorrarBot(vision, acciones, registro)
            if not args.confirmar:
                eventos.decir("Modo prueba (no borra nada):")
            borradas, ok, mensaje = bot.correr(confirmar=args.confirmar, maximo=args.max)
            eventos.emitir("fin_borrar", borradas=borradas, ok=ok, mensaje=mensaje, captura=bot.ultima_captura)
            eventos.decir(f"Terminé. Publicaciones borradas: {borradas}")
            codigo = 0 if ok else 1
        else:
            from .publicar import URL_CREAR, PublicarBot

            carpetas = [rutas.plantillas / n for n in args.solo if (rutas.plantillas / n / "datos.txt").exists()]
            faltan = sorted(set(args.solo) - {c.name for c in carpetas})
            if faltan:
                eventos.decir("⚠ No encontré estas plantillas: " + ", ".join(faltan))
            if not carpetas:
                eventos.decir("No hay nada que publicar.")
                return 1
            preparar(URL_CREAR, ventana)
            bot = PublicarBot(vision, acciones, registro, config.SUBIDAS,
                              max_grupos=args.max_grupos or ajustes.max_grupos,
                              reducir_fotos=not args.fotos_originales and ajustes.reducir_fotos)
            acciones.guardar_portapapeles()
            try:
                fallidas = bot.correr(carpetas, args.confirmar,
                                      reintentar=not args.sin_reintento and ajustes.reintentar_fallidos,
                                      pausa=tuple(args.pausa or (ajustes.pausa_min, ajustes.pausa_max)))
            finally:
                acciones.restaurar_portapapeles()
            hechas = len(carpetas) - len(fallidas)
            eventos.emitir("fin_publicar", hechas=hechas, fallidas=fallidas)
            verbo = "Publicados" if args.confirmar else "Probados"
            eventos.decir(f"\nTerminé. {verbo}: {hechas} de {len(carpetas)}."
                          + (f" Fallaron: {', '.join(fallidas)}" if fallidas else ""))
            codigo = 2 if fallidas else 0
    except FailSafeException:
        eventos.decir("⏹ Detenido: llevaste el mouse a una esquina.")
        eventos.emitir("detenido")
        codigo = 3
    except NavegadorNoEncontrado as e:
        eventos.decir(f"✖ {e}")
        eventos.emitir("error", mensaje=str(e))
        codigo = 1
    if vision.escala and vision.escala != escala_inicial:
        eventos.emitir("escala", valor=vision.escala)
    return codigo
