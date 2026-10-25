"""Como el motor le cuenta a la ventana lo que va pasando.

El motor corre en un proceso aparte (asi el boton Detener lo puede cortar en
seco). Cada linea que imprime es texto para el registro, salvo las que
empiezan con PREFIJO, que llevan un evento en JSON para la ventana.
"""
import json
import os
import sys
import time

PREFIJO = "@@evento "
_inicio = time.time()


def emitir(tipo, **datos):
    print(PREFIJO + json.dumps({"tipo": tipo, **datos}, ensure_ascii=False), flush=True)


def paso(texto):
    """Lo que el bot esta haciendo ahora, en pocas palabras, para la barrita."""
    emitir("paso", texto=texto)
    print(f"   [{time.time() - _inicio:6.1f} s] {texto}", flush=True)  # para medir cuanto tarda cada paso


def decir(texto):
    print(texto, flush=True)


def leer_linea(linea):
    """Devuelve (evento, None) si la linea es un evento, o (None, texto)."""
    if linea.startswith(PREFIJO):
        try:
            return json.loads(linea[len(PREFIJO):]), None
        except ValueError:
            pass
    return None, linea


def configurar_salida():
    # En el .exe sin consola Python puede arrancar sin stdout aunque la ventana
    # nos haya pasado un tubo: lo abrimos a mano.
    if sys.stdout is None:
        try:
            sys.stdout = open(1, "w", encoding="utf-8", buffering=1, closefd=False)  # noqa: SIM115
        except OSError:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = sys.stdout
    # En Windows la consola a veces no es UTF-8 y los emojis de los titulos rompen el print.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        except (AttributeError, ValueError):
            pass
