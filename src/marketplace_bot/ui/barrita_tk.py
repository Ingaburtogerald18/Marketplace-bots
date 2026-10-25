"""La barrita de progreso que queda arriba de la pantalla mientras el bot trabaja.

Es una ventanita aparte hecha con tkinter (viene con Python). Antes era la
ventana principal achicada, pero Windows no la dejaba achicar y quedaba como un
cuadro grande en el centro que tapaba el aviso «Eliminar» de Facebook
(25 de octubre). Esta mide siempre lo mismo y queda sobre la barra de
direcciones del navegador, donde el bot nunca busca botones.

Recibe el estado por la entrada (una linea JSON por cambio:
titulo, paso, detalle, valor) y escribe "detener" cuando tocan el boton.
Se cierra sola cuando la ventana principal cierra la entrada.

    python -m marketplace_bot barrita
"""
import json
import queue
import sys
import threading
import tkinter as tk

ANCHO, ALTO = 560, 92
FONDO = "#1b1e22"
BORDE = "#2f343a"
TEXTO = "#e8eaed"
TENUE = "#9aa0a6"
ACENTO = "#3d8bfd"
PELIGRO = "#e5484d"
BARRA_FONDO = "#2a2e33"


def escala_pantalla():
    """En Windows: pide pixeles reales y devuelve la escala (1.0, 1.25, 1.5...)."""
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return ctypes.windll.user32.GetDpiForSystem() / 96
    except (AttributeError, OSError):
        return 1.0


class Barrita:
    def __init__(self, raiz, escala=1.0, al_detener=None):
        self.raiz = raiz
        self.escala = escala
        self.al_detener = al_detener or (lambda: None)
        self.valor = None
        self._fase = 0.0

        def px(n):
            return int(n * escala)

        def letra(tamano, peso="normal"):
            return ("Segoe UI", -px(tamano), peso)

        self.px = px
        raiz.overrideredirect(True)  # sin barra de titulo
        raiz.attributes("-topmost", True)
        raiz.configure(bg=BORDE)
        ancho, alto = px(ANCHO), px(ALTO)
        raiz.geometry(f"{ancho}x{alto}+{(raiz.winfo_screenwidth() - ancho) // 2}+0")

        caja = tk.Frame(raiz, bg=FONDO)
        caja.place(x=1, y=0, relwidth=1, width=-2, relheight=1, height=-1)
        self.boton = tk.Button(caja, text="■  Detener", command=self._detener, font=letra(13, "bold"),
                               bg=PELIGRO, fg="white", activebackground="#c93b3f", activeforeground="white",
                               relief="flat", bd=0, padx=px(14), pady=px(4), cursor="hand2")
        self.boton.place(relx=1, x=-px(14), y=px(12), anchor="ne")
        textos = tk.Frame(caja, bg=FONDO)
        textos.place(x=px(16), y=px(9), relwidth=1, width=-px(150))
        self.titulo = tk.Label(textos, text="Empezando…", font=letra(14, "bold"), fg=TEXTO, bg=FONDO, anchor="w")
        self.paso = tk.Label(textos, text="", font=letra(13), fg=ACENTO, bg=FONDO, anchor="w")
        self.detalle = tk.Label(textos, text="No toqués el mouse · Mouse a una esquina = parar",
                                font=letra(11), fg=TENUE, bg=FONDO, anchor="w")
        for etiqueta in (self.titulo, self.paso, self.detalle):
            etiqueta.pack(fill="x")
        self.barra = tk.Canvas(caja, height=px(4), bg=BARRA_FONDO, highlightthickness=0, bd=0)
        self.barra.place(x=px(16), rely=1, y=-px(10), relwidth=1, width=-px(32), anchor="sw")
        self._animar()

    def poner(self, estado):
        if "titulo" in estado:
            self.titulo.config(text=estado["titulo"])
        if "paso" in estado:
            self.paso.config(text=("→ " + estado["paso"]) if estado["paso"] else "")
        if "detalle" in estado:
            self.detalle.config(text=estado["detalle"])
        if "valor" in estado:
            self.valor = estado["valor"]

    def _animar(self):
        ancho = max(self.barra.winfo_width(), 1)
        alto = self.px(4)
        self.barra.delete("all")
        if self.valor is None:  # sin total conocido: un tramo que va y viene
            self._fase = (self._fase + 0.02) % 1.3
            inicio = (self._fase - 0.3) * ancho
            self.barra.create_rectangle(inicio, 0, inicio + ancho * 0.3, alto, fill=ACENTO, width=0)
        else:
            self.barra.create_rectangle(0, 0, ancho * max(0.0, min(1.0, self.valor)), alto, fill=ACENTO, width=0)
        self.raiz.after(30, self._animar)

    def _detener(self):
        self.boton.config(text="Deteniendo…", state="disabled")
        self.al_detener()


def main():
    escala = escala_pantalla()
    raiz = tk.Tk()
    raiz.title("Marketplace bot - progreso")

    def detener():
        print("detener", flush=True)

    barrita = Barrita(raiz, escala, detener)
    cola = queue.Queue()

    def leer():
        for linea in sys.stdin:
            try:
                cola.put(json.loads(linea))
            except ValueError:
                pass
        cola.put(None)  # la ventana principal cerro: nos vamos

    def revisar():
        while not cola.empty():
            estado = cola.get()
            if estado is None:
                raiz.destroy()
                return
            barrita.poner(estado)
        raiz.after(100, revisar)

    threading.Thread(target=leer, daemon=True).start()
    raiz.after(100, revisar)
    raiz.mainloop()


if __name__ == "__main__":
    main()
