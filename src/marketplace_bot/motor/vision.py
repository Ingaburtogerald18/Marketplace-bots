"""Buscar botones de Facebook en la pantalla. Lo usan borrar y publicar.

Cada boton es un recorte en recursos/botones/ (por ejemplo
borrar/compartir.png). Si Facebook esta en otro idioma, el mismo boton puede
tener variantes: borrar/compartir_en.png.

Para cada recorte probamos:
- varios tamanos (Windows al 100, 125, 150 %...); el primero que funciona se
  usa para todo lo demas;
- la version invertida en gris, para que un recorte de modo oscuro sirva en
  modo claro y al reves. Por eso los recortes deben ser solo el boton (dos
  tonos), sin el borde o el fondo de la tarjeta.

Toma UNA captura por vuelta y compara todas las variantes con OpenCV, que es
mucho mas rapido que pedirle a pyautogui una captura por variante.
"""
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ESCALAS = (1.0, 1.25, 1.5, 1.1, 1.75, 0.9, 2.0, 0.8)  # 0.8: laptops con el zoom del navegador al 80-90 %
PARECIDO = 0.85  # que tanto debe parecerse la pantalla al recorte (0 a 1)


@dataclass
class Caja:
    left: int
    top: int
    width: int
    height: int
    parecido: float = 1.0

    @property
    def x(self):
        return self.left + self.width // 2

    @property
    def y(self):
        return self.top + self.height // 2

    @property
    def centro(self):
        return (self.x, self.y)


def recortar_zona(zona, ancho_pantalla, alto_pantalla):
    """Ajusta una zona (izq, arriba, ancho, alto) para que no se salga de la pantalla."""
    if zona is None:
        return None
    izq, arriba, ancho, alto = (int(round(v)) for v in zona)
    izq, arriba = max(0, izq), max(0, arriba)
    ancho = max(1, min(ancho, ancho_pantalla - izq))
    alto = max(1, min(alto, alto_pantalla - arriba))
    return (izq, arriba, ancho, alto)


def _captura_pyautogui():
    import pyautogui

    return pyautogui.screenshot()


class Vision:
    def __init__(self, carpeta_botones, capturar=None, parecido=PARECIDO, escala=None):
        self.carpeta = Path(carpeta_botones)
        self.capturar = capturar or _captura_pyautogui  # en las pruebas: una imagen fija
        self.parecido = parecido
        self.escala = escala  # si ya sabemos el tamano de esta PC, nos ahorramos probar los demas
        self._cache = {}

    # ---------- recortes ----------
    def archivos(self, nombre):
        """nombre = "borrar/compartir" -> compartir.png y sus variantes compartir_*.png."""
        base = self.carpeta / f"{nombre}.png"
        variantes = sorted(base.parent.glob(f"{base.stem}_*.png")) if base.parent.exists() else []
        return [p for p in [base, *variantes] if p.exists()]

    def existe(self, nombre):
        return bool(self.archivos(nombre))

    def _variantes(self, nombre):
        escalas = (self.escala,) if self.escala else ESCALAS
        clave = (nombre, escalas)
        if clave not in self._cache:
            variantes = []
            # Pillow lee rutas con tildes en Windows (OpenCV no).
            originales = [Image.open(a).convert("RGB") for a in self.archivos(nombre)]
            for e in escalas:
                for original in originales:
                    recorte = original if e == 1.0 else original.resize(
                        (max(1, round(original.width * e)), max(1, round(original.height * e))), Image.LANCZOS)
                    color = cv2.cvtColor(np.array(recorte), cv2.COLOR_RGB2BGR)
                    invertido = np.array(ImageOps.invert(recorte.convert("L")))
                    variantes.append((color, False, e))
                    variantes.append((invertido, True, e))
            self._cache[clave] = variantes
        return self._cache[clave]

    # ---------- pantalla ----------
    def pantalla(self, zona=None):
        """Devuelve (imagen_bgr, imagen_gris, desplazamiento) de la zona pedida."""
        imagen = self.capturar()
        zona = recortar_zona(zona, imagen.width, imagen.height)
        if zona:
            izq, arriba, ancho, alto = zona
            imagen = imagen.crop((izq, arriba, izq + ancho, arriba + alto))
            desplazamiento = (izq, arriba)
        else:
            desplazamiento = (0, 0)
        rgb = np.array(imagen.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), desplazamiento

    def tamano_pantalla(self):
        imagen = self.capturar()
        return imagen.width, imagen.height

    def buscar(self, nombre, zona=None, parecido=None, pantalla=None):
        """Una sola mirada a la pantalla. Devuelve la Caja o None."""
        parecido = parecido or self.parecido
        color, gris, (dx, dy) = pantalla or self.pantalla(zona)
        mejor = None
        # Las variantes vienen ordenadas por tamano (100 % primero): en cuanto un
        # tamano encuentra el boton, no probamos los demas.
        for recorte, invertido, e in self._variantes(nombre):
            if mejor and mejor[1] != e:
                break
            fondo = gris if invertido else color
            if recorte.shape[0] > fondo.shape[0] or recorte.shape[1] > fondo.shape[1]:
                continue  # recorte mas grande que la zona
            resultado = cv2.matchTemplate(fondo, recorte, cv2.TM_CCOEFF_NORMED)
            _, valor, _, (x, y) = cv2.minMaxLoc(resultado)
            if valor >= parecido and (mejor is None or valor > mejor[0].parecido):
                mejor = (Caja(x + dx, y + dy, recorte.shape[1], recorte.shape[0], float(valor)), e)
        if not mejor:
            return None
        caja, e = mejor
        if self.escala is None:
            if e != 1.0:
                print(f"   (tu pantalla esta al {e:.0%}, ajusto los tamaños)", flush=True)
            self.escala = e
        return caja

    def diagnostico(self, nombre, zona=None):
        """Lo mas parecido que hay en pantalla, en cualquier tamano: (parecido, tamano).
        Sirve para el registro cuando algo no aparece."""
        guardada, self.escala = self.escala, None
        try:
            color, gris, _ = self.pantalla(zona)
            mejor = (0.0, 1.0)
            for recorte, invertido, e in self._variantes(nombre):
                fondo = gris if invertido else color
                if recorte.shape[0] > fondo.shape[0] or recorte.shape[1] > fondo.shape[1]:
                    continue
                valor = float(cv2.minMaxLoc(cv2.matchTemplate(fondo, recorte, cv2.TM_CCOEFF_NORMED))[1])
                if valor > mejor[0]:
                    mejor = (valor, e)
            return mejor
        finally:
            self.escala = guardada

    def buscar_todas(self, nombre, zona=None, parecido=0.9):
        """Todas las apariciones (por ejemplo, las casillas de los grupos)."""
        color, gris, (dx, dy) = self.pantalla(zona)
        cajas = []
        for recorte, invertido, _ in self._variantes(nombre):
            fondo = gris if invertido else color
            if recorte.shape[0] > fondo.shape[0] or recorte.shape[1] > fondo.shape[1]:
                continue
            resultado = cv2.matchTemplate(fondo, recorte, cv2.TM_CCOEFF_NORMED)
            alto, ancho = recorte.shape[:2]
            for y, x in zip(*np.where(resultado >= parecido), strict=True):
                caja = Caja(int(x) + dx, int(y) + dy, ancho, alto, float(resultado[y, x]))
                if not any(abs(caja.x - c.x) < ancho // 2 and abs(caja.y - c.y) < alto // 2 for c in cajas):
                    cajas.append(caja)
        return sorted(cajas, key=lambda c: (c.y, c.x))

    def esperar(self, nombre, zona=None, espera=6.0, mientras=None, decir=True, parecido=None):
        """Mira la pantalla hasta `espera` segundos. `mientras` se llama entre
        miradas (por ejemplo, para bajar la pagina)."""
        inicio = time.time()
        while True:
            caja = self.buscar(nombre, zona, parecido=parecido)
            if caja:
                if decir:
                    print(f"   {nombre}: encontrado en {time.time() - inicio:.1f} s", flush=True)
                return caja
            if time.time() - inicio >= espera:
                break
            if mientras:
                mientras()
            else:
                time.sleep(0.3)
        if decir:
            print(f"   {nombre}: no lo encontré en {espera:.0f} s", flush=True)
        return None

    def esperar_que_se_vaya(self, nombre, zona=None, espera=6.0):
        """Espera a que el boton desaparezca. Devuelve True si se fue."""
        limite = time.time() + espera
        while time.time() < limite:
            if not self.buscar(nombre, zona):
                return True
            time.sleep(0.3)
        return False

    def esperar_alguno(self, nombres, zona=None, espera=6.0):
        """Espera a que aparezca cualquiera de los botones. Devuelve (nombre, caja)."""
        inicio = time.time()
        while True:
            pantalla = self.pantalla(zona)
            for nombre in nombres:
                if self.existe(nombre):
                    caja = self.buscar(nombre, pantalla=pantalla)
                    if caja:
                        print(f"   {nombre}: encontrado en {time.time() - inicio:.1f} s", flush=True)
                        return nombre, caja
            if time.time() - inicio >= espera:
                return None, None
            time.sleep(0.3)

    def px(self, valor):
        """Convierte una distancia medida al 100 % a la escala de esta pantalla."""
        return valor * (self.escala or 1.0)
