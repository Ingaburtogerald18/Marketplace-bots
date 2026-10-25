"""La barrita que queda arriba de la pantalla mientras el bot trabaja.

La ventana principal se minimiza y se abre la barrita de barrita_tk.py en un
proceso aparte; aqui solo se decide que dice y se le manda.
"""
import json
import subprocess
import threading

from ... import ejecutor as ejecutor_mod


def estado_barrita(corrida):
    """Lo que muestra la barrita para esta corrida: titulo, paso, detalle y valor (0..1 o None)."""
    actual, total, ronda = corrida.progreso
    trabajando = next((r for r in corrida.resultados.values() if r.estado == "trabajando"), None)
    valor = None
    if trabajando:
        titulo = f"{actual} de {total}" + (" · reintento" if ronda > 1 else "") + f" · {trabajando.titulo}"
        valor = (actual - 1) / total if total else None
    elif corrida.accion in ("borrar", "borrar_y_publicar") and all(
            r.estado == "pendiente" for r in corrida.resultados.values()):
        titulo = "Borrando publicaciones viejas" + (f" · {corrida.borradas} borradas" if corrida.borradas else "")
    else:
        titulo = "Trabajando…"
    detalle = "No toqués el mouse · Mouse a una esquina = parar"
    if total:
        hechos = sum(1 for r in corrida.resultados.values() if r.ok)
        fallos = len(corrida.fallidos)
        detalle = f"{hechos} bien" + (f" · {fallos} con problema" if fallos else "") + " · Mouse a una esquina = parar"
    return {"titulo": titulo, "paso": corrida.paso, "detalle": detalle, "valor": valor}


class BarritaProgreso:
    def __init__(self, app):
        self.app = app
        self.proceso = None
        self._ultimo = None

    def abrir(self):
        self.cerrar()
        try:
            self.proceso = subprocess.Popen(
                ejecutor_mod.comando_propio("barrita"), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", env=ejecutor_mod.entorno_python(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self.proceso = None
            return
        self._ultimo = None
        threading.Thread(target=self._escuchar, args=(self.proceso,), daemon=True).start()
        self.refrescar()

    def _escuchar(self, proceso):
        for linea in proceso.stdout:
            if linea.strip() == "detener":
                self.app.ejecutor.detener()

    def refrescar(self):
        corrida = self.app.ejecutor.corrida
        if not (self.proceso and corrida):
            return
        estado = estado_barrita(corrida)
        if estado == self._ultimo:
            return
        self._ultimo = estado
        try:
            self.proceso.stdin.write(json.dumps(estado, ensure_ascii=False) + "\n")
            self.proceso.stdin.flush()
        except (OSError, ValueError):  # la barrita se cerro
            self.proceso = None

    def cerrar(self):
        proceso, self.proceso = self.proceso, None
        if not proceso:
            return
        try:
            proceso.stdin.close()
            proceso.wait(timeout=2)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            proceso.kill()
