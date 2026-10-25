"""Borra tus publicaciones de Marketplace, una por una.

Por cada publicacion:
  1. Espera la pagina de ventas: o aparece "Compartir" (hay publicaciones) o el
     mensaje "Cuando empieces a vender..." (ya no queda nada: terminamos bien).
  2. Clic en el "..." a la derecha de "Compartir" (o en la linea de abajo,
     cuando una publicacion vieja muestra "Volver a publicar").
  3. "Eliminar publicacion" cerca del menu y el "Eliminar" azul del centro.
  4. Si Facebook pregunta el motivo, elige "Prefiero no responder" (cuando
     exista su recorte en recursos/botones/borrar/).
  5. Recarga y repite.
"""
from . import eventos

URL_VENTAS = "https://www.facebook.com/marketplace/you/selling"


class BorrarBot:
    def __init__(self, vision, acciones, carpeta_registro):
        self.vision = vision
        self.acciones = acciones
        self.carpeta_registro = carpeta_registro
        self.ultima_captura = ""

    # ---------- zonas ----------
    def _zona(self, izq, arriba, ancho, alto):
        w, h = self.acciones.tamano_pantalla()
        from .vision import recortar_zona

        return recortar_zona((izq, arriba, ancho, alto), w, h)

    def zona_centro(self):
        w, h = self.acciones.tamano_pantalla()
        return self._zona(w // 4, h // 6, w // 2, h * 2 // 3)

    def zona_alrededor(self, punto):
        px = self.vision.px
        return self._zona(punto.x - px(450), punto.y - px(450), px(700), px(900))

    def _fallo(self, nombre, cajas=(), puntos=()):
        ruta = f"{self.carpeta_registro}/fallo_borrar_{nombre}.png"
        self.ultima_captura = self.acciones.captura(ruta, cajas, puntos)
        eventos.decir(f"   Guardé la captura {ruta}: círculo = donde di clic, cuadro = donde busqué.")

    # ---------- pasos ----------
    def esperar_pagina(self):
        """Devuelve "hay", "vacia" o None."""
        nombre, caja = self.vision.esperar_alguno(["borrar/compartir", "borrar/vacio"], espera=15)
        if nombre == "borrar/vacio":
            return "vacia", None
        if nombre:
            return "hay", caja
        return None, None

    def borrar_una(self, compartir, confirmar):
        """Hace el proceso con la primera publicacion. Devuelve True si salio bien."""
        px = self.vision.px
        a_la_derecha = self._zona(compartir.left + compartir.width, compartir.top - px(15),
                                  px(120), compartir.height + px(30))
        puntos = self.vision.esperar("borrar/opciones", zona=a_la_derecha, espera=2)
        abajo = None
        if not puntos:
            abajo = self._zona(compartir.left - px(700), compartir.top + compartir.height - px(5),
                               px(700) + compartir.width + px(120), px(80))
            puntos = self.vision.esperar("borrar/opciones", zona=abajo, espera=2)
        if not puntos:
            self._fallo("opciones", cajas=[a_la_derecha, abajo])
            return False
        self.acciones.clic(puntos)

        zona = self.zona_alrededor(puntos)
        eliminar = self.vision.esperar("borrar/eliminar", zona=zona, espera=10)
        if not eliminar:
            self._fallo("eliminar", cajas=[zona], puntos=[puntos])
            self.acciones.tecla("esc")
            return False
        if not confirmar:
            self.acciones.mover(eliminar, 0.4)
            eventos.decir("   Prueba: aquí le daría clic a «Eliminar publicación». Cierro el menú.")
            self.acciones.pausa(1.5, 1.5)
            self.acciones.tecla("esc")
            return True
        self.acciones.clic(eliminar)

        boton_final = self.vision.esperar("borrar/confirmar", zona=self.zona_centro(), espera=20)
        if not boton_final:
            self._fallo("confirmar", cajas=[self.zona_centro()], puntos=[eliminar])
            self.acciones.tecla("esc")
            return False
        self.acciones.clic(boton_final)
        self.responder_motivo()
        return True

    def responder_motivo(self):
        """A veces Facebook pregunta por que lo borras. Elegimos "Prefiero no responder"."""
        if not self.vision.existe("borrar/motivo_prefiero_no_responder"):
            return
        opcion = self.vision.esperar("borrar/motivo_prefiero_no_responder", espera=4, decir=False)
        if not opcion:
            return
        eventos.decir("   Facebook preguntó el motivo: elijo «Prefiero no responder».")
        self.acciones.clic(opcion)
        if self.vision.existe("borrar/motivo_listo"):
            listo = self.vision.esperar("borrar/motivo_listo", espera=4, decir=False)
            if listo:
                self.acciones.clic(listo)

    # ---------- corrida ----------
    def correr(self, confirmar=True, maximo=20):
        """Devuelve (borradas, ok, mensaje)."""
        self.acciones.ir_a(URL_VENTAS)
        borradas = 0
        while True:
            estado, compartir = self.esperar_pagina()
            if estado == "vacia":
                mensaje = "No quedan publicaciones por borrar." if borradas else "No había publicaciones para borrar."
                eventos.decir(mensaje)
                return borradas, True, mensaje
            if estado is None:
                self._fallo("pagina")
                return borradas, False, "No reconocí la página de tus publicaciones."
            if not confirmar:
                ok = self.borrar_una(compartir, confirmar=False)
                return 0, ok, "La prueba salió bien." if ok else "La prueba falló."
            if borradas >= maximo:
                return borradas, True, f"Llegué al máximo de {maximo}."
            eventos.decir(f"Publicación {borradas + 1}:")
            if not self.borrar_una(compartir, confirmar=True):
                return borradas, False, "Algo no apareció al borrar; me detuve."
            borradas += 1
            eventos.emitir("borrada", total=borradas)
            eventos.decir(f"   Borrada. Total: {borradas}")
            self.acciones.pausa(3, 5)
            self.acciones.tecla("f5")
            self.acciones.pausa(3, 4)
