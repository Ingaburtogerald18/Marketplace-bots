"""Corre el motor en un proceso aparte y va contando lo que pasa.

La ventana no mueve el mouse: le pide al Ejecutor que corra el motor, y el
Ejecutor le avisa (con funciones que la ventana le pasa) cada linea del
registro, cada articulo que cambia de estado y cuando termina.
"""
import os
import subprocess
import sys
import threading
from pathlib import Path

from . import config
from .modelos import Resultado
from .motor import eventos
from .registros import Corrida


def comando_motor(*argumentos):
    if config.CONGELADO:  # el .exe se llama a si mismo
        return [sys.executable, "motor", *argumentos]
    return [sys.executable, "-u", "-m", "marketplace_bot", "motor", *argumentos]


class Ejecutor:
    def __init__(self, rutas, ajustes, al_linea=None, al_cambio=None, al_terminar=None):
        self.rutas = rutas
        self.ajustes = ajustes
        self.al_linea = al_linea or (lambda texto: None)
        self.al_cambio = al_cambio or (lambda corrida: None)
        self.al_terminar = al_terminar or (lambda corrida: None)
        self.proceso = None
        self.corrida = None
        self.detenido = False

    @property
    def corriendo(self):
        return self.corrida is not None and self.corrida.fin is None

    # ---------- acciones ----------
    def publicar(self, plantillas, confirmar=True, borrar_antes=False):
        accion = "borrar_y_publicar" if borrar_antes else ("publicar" if confirmar else "probar")
        articulos = [Resultado(carpeta=p.nombre, titulo=p.titulo) for p in plantillas]
        pasos = []
        if borrar_antes:
            pasos.append(self._args_borrar(confirmar=True))
        pasos.append(self._args_publicar([p.nombre for p in plantillas], confirmar))
        return self._empezar(accion, articulos, pasos)

    def borrar(self, confirmar=True):
        return self._empezar("borrar", [], [self._args_borrar(confirmar)])

    def detener(self):
        self.detenido = True
        if self.proceso and self.proceso.poll() is None:
            self.proceso.kill()

    # ---------- por dentro ----------
    def _comunes(self, corrida_carpeta):
        args = ["--registro", str(corrida_carpeta), "--ventana", self.ajustes.ventana or ""]
        if self.ajustes.escala:
            args += ["--escala", str(self.ajustes.escala)]
        return args

    def _args_borrar(self, confirmar):
        args = ["borrar", "--max", str(self.ajustes.max_borrar)]
        return args + (["--confirmar"] if confirmar else [])

    def _args_publicar(self, nombres, confirmar):
        args = ["publicar", "--solo", *nombres, "--max-grupos", str(self.ajustes.max_grupos),
                "--pausa", str(self.ajustes.pausa_min), str(self.ajustes.pausa_max)]
        if not self.ajustes.reintentar_fallidos:
            args.append("--sin-reintento")
        if not self.ajustes.reducir_fotos:
            args.append("--fotos-originales")
        return args + (["--confirmar"] if confirmar else [])

    def _empezar(self, accion, articulos, pasos):
        if self.corriendo:
            return None
        self.detenido = False
        self.corrida = Corrida(self.rutas, accion, articulos)
        threading.Thread(target=self._trabajar, args=(self.corrida, pasos), daemon=True).start()
        return self.corrida

    def _trabajar(self, corrida, pasos):
        mensaje = ""
        entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        if not config.CONGELADO:
            src = str(Path(__file__).resolve().parents[1])
            entorno["PYTHONPATH"] = src + os.pathsep + entorno.get("PYTHONPATH", "")
        try:
            for paso in pasos:
                if self.detenido:
                    break
                comando = comando_motor(*paso[:1], *self._comunes(corrida.carpeta), *paso[1:])
                self.proceso = subprocess.Popen(
                    comando, cwd=self.rutas.raiz, text=True, encoding="utf-8", errors="replace",
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=entorno,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                for linea in self.proceso.stdout:
                    self._linea(corrida, linea)
                codigo = self.proceso.wait()
                if self.detenido:
                    mensaje = "Lo detuviste."
                    self._linea(corrida, "⏹ Lo detuviste.\n")
                    break
                if codigo in (1, 3) and paso[0] == "publicar":
                    mensaje = mensaje or "El bot se detuvo."
                    break
                # Si borrar falla seguimos con publicar: lo importante es publicar.
        except Exception as e:  # noqa: BLE001 - que la ventana se entere de cualquier error
            mensaje = f"No pude correr el bot: {e}"
            self._linea(corrida, f"⚠ {mensaje}\n")
        finally:
            self.proceso = None
            corrida.terminar(mensaje)
            self.al_cambio(corrida)
            self.al_terminar(corrida)

    def _linea(self, corrida, linea):
        evento, texto = eventos.leer_linea(linea)
        if texto is not None:
            corrida.anotar(texto)
            self.al_linea(texto)
            return
        tipo = evento.get("tipo")
        if tipo == "articulo":
            corrida.resultado(evento["carpeta"], titulo=evento.get("titulo", ""), estado=evento["estado"],
                              detalle=evento.get("detalle", ""), captura=evento.get("captura", ""))
            if "indice" in evento:
                corrida.progreso = (evento["indice"], evento["total"], evento.get("ronda", 1))
        elif tipo == "borrada":
            corrida.borradas = evento["total"]
        elif tipo == "fin_borrar":
            corrida.borradas = evento.get("borradas", corrida.borradas)
            corrida.mensaje_borrar = evento.get("mensaje", "")
        elif tipo == "escala":
            self.ajustes.escala = evento["valor"]
            self.ajustes.guardar()
        elif tipo == "error":
            corrida.mensaje_final = evento.get("mensaje", "")
        self.al_cambio(corrida)
