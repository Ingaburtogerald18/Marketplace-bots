"""Mouse, teclado y portapapeles. Todo lo que el bot "hace" pasa por aqui."""
import random
import time
from pathlib import Path


class Acciones:
    def __init__(self):
        import pyautogui
        import pyperclip

        self.pyautogui = pyautogui
        self.pyperclip = pyperclip
        pyautogui.FAILSAFE = True  # mouse en una esquina = detener
        pyautogui.PAUSE = 0.05
        self._portapapeles = None

    # ---------- pausas ----------
    @staticmethod
    def pausa(min_seg=0.8, max_seg=1.8):
        time.sleep(random.uniform(min_seg, max_seg))

    # ---------- mouse ----------
    def mover(self, punto, duracion=None):
        x, y = punto.centro if hasattr(punto, "centro") else punto
        # Rapido pero no instantaneo: un salto de golpe se ve menos humano.
        self.pyautogui.moveTo(x, y, duration=duracion if duracion is not None else random.uniform(0.08, 0.18))

    def clic(self, punto):
        self.mover(punto)
        self.pyautogui.click()

    def rueda(self, punto, cantidad):
        self.mover(punto, 0)
        self.pyautogui.scroll(cantidad)

    def tamano_pantalla(self):
        return self.pyautogui.size()

    # ---------- teclado ----------
    def tecla(self, *teclas):
        for t in teclas:
            self.pyautogui.press(t)

    def atajo(self, *teclas):
        self.pyautogui.hotkey(*teclas)

    def cerrar_globos(self):
        """Esc cierra el autocompletar del navegador (el "Saved info" de Edge
        que tapo el formulario el 24 de octubre) y cualquier sugerencia."""
        self.pyautogui.press("esc")
        time.sleep(0.15)

    @staticmethod
    def ventana_activa():
        """Titulo de la ventana que esta al frente ("" si no se sabe)."""
        try:
            import ctypes

            usuario = ctypes.windll.user32
            hwnd = usuario.GetForegroundWindow()
            texto = ctypes.create_unicode_buffer(256)
            usuario.GetWindowTextW(hwnd, texto, 256)
            return texto.value
        except (AttributeError, OSError):
            return ""

    def esperar_ventana(self, titulos, abierta=True, espera=6.0):
        """Espera a que la ventana del frente sea (o deje de ser) una de `titulos`,
        por ejemplo la ventana "Abrir" de Windows. Devuelve True si paso."""
        limite = time.time() + espera
        while time.time() < limite:
            titulo = self.ventana_activa()
            if not titulo and abierta:
                break  # no podemos saberlo: que decida el que llama
            if (titulo in titulos) == abierta:
                return True
            time.sleep(0.1)
        return False

    # ---------- texto ----------
    def guardar_portapapeles(self):
        try:
            self._portapapeles = self.pyperclip.paste()
        except Exception:  # noqa: BLE001 - si no se puede, no pasa nada
            self._portapapeles = None

    def restaurar_portapapeles(self):
        if self._portapapeles is not None:
            try:
                self.pyperclip.copy(self._portapapeles)
            except Exception:  # noqa: BLE001
                pass

    def pegar(self, texto):
        """Pega texto con el portapapeles (asi no fallan tildes, emojis ni simbolos)."""
        self.pyperclip.copy(texto)
        self.pyautogui.hotkey("ctrl", "v")
        self.pausa(0.15, 0.3)

    def ir_a(self, url):
        self.pyautogui.hotkey("ctrl", "l")
        time.sleep(0.4)
        self.pegar(url)
        self.pyautogui.press("enter")
        self.pausa(1, 1.5)  # despues cada paso espera a ver su boton, no hace falta mas

    # ---------- capturas ----------
    def captura(self, ruta, cajas=(), puntos=()):
        """Guarda la pantalla marcando en rojo donde busco (cajas) y donde dio clic (puntos)."""
        from PIL import ImageDraw

        imagen = self.pyautogui.screenshot()
        dibujo = ImageDraw.Draw(imagen)
        for zona in cajas:
            if zona:
                izq, arriba, ancho, alto = zona
                dibujo.rectangle([izq, arriba, izq + ancho, arriba + alto], outline="red", width=4)
        for punto in puntos:
            if punto:
                x, y = punto.centro if hasattr(punto, "centro") else punto
                dibujo.ellipse([x - 20, y - 20, x + 20, y + 20], outline="red", width=4)
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        imagen.save(ruta)
        return str(ruta)
