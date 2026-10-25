"""Borra tus publicaciones de Marketplace, una por una.

Por cada publicacion:
  1. Espera la pagina de ventas: o aparece "Compartir" (hay publicaciones) o el
     mensaje "Cuando empieces a vender..." (ya no queda nada: terminamos bien).
  2. Clic en el "..." a la derecha de "Compartir" (o en la linea de abajo,
     cuando una publicacion vieja muestra "Volver a publicar").
  3. "Eliminar publicacion" cerca del menu y el "Eliminar" azul del centro.
  4. Si Facebook pregunta "¿Vendiste este articulo?", elige "Prefiero no
     responder" y "Siguiente".
  5. Espera a que Facebook quite la publicacion de la lista y sigue con la
     siguiente, sin recargar (recargar costaba unos 7 s por publicacion). Si
     algo no aparece, recarga la pagina y prueba una vez mas.
"""
from . import eventos

URL_VENTAS = "https://www.facebook.com/marketplace/you/selling"
TOPE = 300  # aunque pidan "todas", nunca mas de esto en una corrida


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
    def esperar_pagina(self, espera=15):
        """Devuelve ("hay", caja de Compartir), ("vacia", None) o (None, None).

        Solo da por buena la posicion de "Compartir" cuando dos miradas seguidas
        la ven en el mismo lugar: mientras la pagina carga, Facebook agrega
        avisos arriba y todo se corre hacia abajo (25 de octubre: el bot buscó el
        "..." donde ya no estaba).
        """
        import time

        limite = time.time() + espera
        anterior = None
        while True:
            restante = max(0.5, limite - time.time())
            nombre, caja = self.vision.esperar_alguno(["borrar/compartir", "borrar/vacio"], espera=restante)
            if nombre == "borrar/vacio":
                return "vacia", None
            if not nombre:
                return None, None
            if anterior and abs(caja.left - anterior.left) <= self.vision.px(4) \
                    and abs(caja.top - anterior.top) <= self.vision.px(4):
                return "hay", caja
            if time.time() > limite:
                return "hay", caja  # sigue moviendose; probamos igual
            anterior = caja
            self.acciones.pausa(0.3, 0.3)

    def borrar_una(self, compartir, confirmar):
        """Hace el proceso con la primera publicacion. Devuelve True si salio bien."""
        px = self.vision.px
        a_la_derecha = self._zona(compartir.left + compartir.width, compartir.top - px(15),
                                  px(120), compartir.height + px(30))
        eventos.paso("Abriendo el menú «…»")
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

        eventos.paso("Buscando «Eliminar publicación»")
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
        eventos.paso("Confirmando")

        # Facebook muestra el "Eliminar" azul, o primero pregunta "¿Vendiste este
        # articulo?" (25 de octubre) y hay que elegir una opcion y darle "Siguiente".
        centro = self.zona_centro()
        nombre, caja = self.vision.esperar_alguno(
            ["borrar/confirmar", "borrar/motivo_prefiero_no_responder"], zona=centro, espera=20)
        if nombre is None:
            self._fallo("confirmar", cajas=[centro], puntos=[eliminar])
            self.acciones.tecla("esc")
            return False
        if nombre == "borrar/confirmar":
            self.acciones.clic(caja)
            opcion = self.esperar_que_cierre(centro)
            return self.responder_motivo(opcion) if opcion else True
        return self.responder_motivo(caja)

    def esperar_que_cierre(self, centro, espera=3):
        """Despues del "Eliminar" azul: o se cierra el cuadro, o Facebook pregunta si
        lo vendiste. Devuelve la opcion «Prefiero no responder» o None si se cerro.
        (Antes esperaba siempre 3 s a la pregunta aunque no viniera.)"""
        import time

        limite = time.time() + espera
        while time.time() < limite:
            pantalla = self.vision.pantalla(centro)
            opcion = self.vision.buscar("borrar/motivo_prefiero_no_responder", pantalla=pantalla)
            if opcion:
                return opcion
            if not self.vision.buscar("borrar/confirmar", pantalla=pantalla):
                self.acciones.pausa(0.4, 0.4)  # por si la pregunta tarda un poquito en salir
                return self.vision.buscar("borrar/motivo_prefiero_no_responder", zona=centro)
            self.acciones.pausa(0.2, 0.2)
        return None

    def responder_motivo(self, opcion):
        """Facebook pregunto si lo vendiste: elegimos «Prefiero no responder» y «Siguiente»."""
        px = self.vision.px
        eventos.decir("   Facebook preguntó si lo vendiste: elijo «Prefiero no responder».")
        eventos.paso("Respondiendo «¿Vendiste este artículo?»")
        self.acciones.clic((opcion.left - px(20), opcion.y))  # el circulito a la izquierda del texto
        self.acciones.pausa(0.3, 0.5)
        # "Siguiente" queda abajo a la derecha de las opciones, en el mismo cuadro.
        zona = self._zona(opcion.left, opcion.top, px(600), px(160))
        siguiente = self.vision.esperar("borrar/motivo_siguiente", zona=zona, espera=4, parecido=0.75)
        if siguiente:
            self.acciones.clic(siguiente)
        else:
            # Al elegir la opcion el boton cambia de color y puede no reconocerse:
            # le damos donde siempre esta (medido en la captura del 25 de octubre).
            eventos.decir("   No reconocí «Siguiente»; le doy clic donde suele estar.")
            self.acciones.clic((opcion.x + px(370), opcion.y + px(75)))
        # A veces despues todavia pide el "Eliminar" azul.
        centro = self.zona_centro()
        boton_final = self.vision.esperar("borrar/confirmar", zona=centro, espera=4, decir=False)
        if boton_final:
            self.acciones.clic(boton_final)
        # Si la pregunta sigue en pantalla, no se borro.
        if self.vision.esperar("borrar/motivo_prefiero_no_responder", zona=centro, espera=0.5, decir=False):
            self._fallo("motivo", cajas=[zona], puntos=[opcion])
            self.acciones.tecla("esc")
            return False
        return True

    # ---------- corrida ----------
    def recargar(self):
        eventos.decir("   Recargo la página y pruebo otra vez.")
        eventos.paso("Recargando la página")
        self.acciones.tecla("esc")
        self.acciones.tecla("f5")
        self.acciones.pausa(3, 4)

    def correr(self, confirmar=True, maximo=0):
        """Devuelve (borradas, ok, mensaje). maximo=0 borra todas."""
        maximo = min(maximo, TOPE) if maximo > 0 else TOPE
        eventos.paso("Abriendo tus publicaciones")
        self.acciones.ir_a(URL_VENTAS)
        borradas = 0
        recargue = False  # un solo reintento recargando por publicacion
        while True:
            # Recien borrada una, Facebook deja la lista vacia sin el mensaje de "no
            # hay nada": si en 5 s no aparece nada, recargamos (25 de octubre: se
            # quedaba esperando al final en vez de terminar).
            estado, compartir = self.esperar_pagina(espera=5 if borradas and not recargue else 15)
            if estado == "vacia":
                mensaje = "No quedan publicaciones por borrar." if borradas else "No había publicaciones para borrar."
                eventos.decir(mensaje)
                return borradas, True, mensaje
            if estado is None:
                if not recargue:
                    recargue = True
                    self.vision.escala = None  # por si el tamano guardado de esta PC ya no sirve
                    self.recargar()
                    continue
                for nombre in ("borrar/compartir", "borrar/vacio"):
                    valor, tamano = self.vision.diagnostico(nombre)
                    eventos.decir(f"   Lo más parecido a «{nombre.split('/')[-1]}»: {valor:.0%} "
                                  f"(tamaño {tamano:.0%}; hace falta {self.vision.parecido:.0%})")
                self._fallo("pagina")
                return borradas, False, "No reconocí la página de tus publicaciones."
            if not confirmar:
                ok = self.borrar_una(compartir, confirmar=False)
                return 0, ok, "La prueba salió bien." if ok else "La prueba falló."
            if borradas >= maximo:
                return borradas, True, f"Llegué al máximo de {maximo}."
            eventos.decir(f"Publicación {borradas + 1}:")
            if not self.borrar_una(compartir, confirmar=True):
                if not recargue:
                    recargue = True
                    self.recargar()
                    continue
                return borradas, False, "Algo no apareció al borrar; me detuve."
            recargue = False
            borradas += 1
            eventos.emitir("borrada", total=borradas)
            eventos.decir(f"   Borrada. Total: {borradas}")
            eventos.paso("Esperando que Facebook la quite de la lista")
            self.acciones.pausa(0.6, 1.0)
