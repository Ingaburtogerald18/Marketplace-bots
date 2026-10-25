"""Crea publicaciones de Marketplace llenando el formulario de Facebook.

Por cada plantilla: abre la pagina de crear articulo, sube las fotos, llena
titulo, precio, categoria, estado y descripcion, marca los grupos y le da
"Publicar".

Cambios respecto a la version anterior:
- Despues de pegar cada texto presiona Esc: cierra el globo de autocompletar
  del navegador (el "Saved info" de Edge que tapo el formulario).
- Baja la pagina desde el centro del formulario, no desde donde estaba el
  titulo antes de subir las fotos.
- Si un articulo falla, guarda su captura y sigue con el siguiente. Al final
  reintenta una vez los que fallaron.
- Las fotos se reducen a 1600 px antes de subirlas (mas rapido).
"""
import shutil
import time
from pathlib import Path

from PIL import Image, ImageOps

from .. import plantillas as plantillas_mod
from . import eventos

URL_CREAR = "https://www.facebook.com/marketplace/create/item"
LADO_MAXIMO = 1600


VENTANA_ABRIR = ("Abrir", "Open")  # la ventana de Windows para elegir archivos

class FaltaBoton(Exception):
    pass


try:
    from pyautogui import FailSafeException
except Exception:  # noqa: BLE001 - sin pantalla (pruebas en Linux) pyautogui no carga
    class FailSafeException(Exception):
        pass


def preparar_fotos(fotos, destino, reducir=True):
    """Copia las fotos a una carpeta temporal, reducidas si hace falta. Devuelve los nombres."""
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True, exist_ok=True)
    nombres = []
    for i, foto in enumerate(fotos, 1):
        nombre = f"{i:02d}.jpg"
        with Image.open(foto) as imagen:
            imagen = ImageOps.exif_transpose(imagen).convert("RGB")
            if reducir and max(imagen.size) > LADO_MAXIMO:
                imagen.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.LANCZOS)
            imagen.save(destino / nombre, quality=88)
        nombres.append(nombre)
    return nombres


class PublicarBot:
    def __init__(self, vision, acciones, carpeta_registro, carpeta_subidas, max_grupos=20, reducir_fotos=True):
        self.vision = vision
        self.acciones = acciones
        self.carpeta_registro = Path(carpeta_registro)
        self.carpeta_subidas = Path(carpeta_subidas)
        self.max_grupos = max_grupos
        self.reducir_fotos = reducir_fotos
        self.formulario = None  # punto dentro del formulario donde se usa la rueda
        self.fotos_listas = 0  # hora a partir de la cual las fotos ya deberian estar subidas
        self.formulario_a_medias = False

    # ---------- ayudas ----------
    def _bajar(self):
        if self.formulario:
            self.acciones.rueda(self.formulario, -200)
            time.sleep(0.4)
        else:
            time.sleep(0.3)

    def buscar(self, nombre, espera=6, bajando=False, mientras=None):
        if not self.vision.existe(nombre):
            raise FaltaBoton(f"Falta el recorte del botón «{nombre}». Mandá la captura de este fallo para recortarlo.")
        caja = self.vision.esperar(nombre, espera=espera, mientras=mientras or (self._bajar if bajando else None))
        if not caja:
            raise FaltaBoton(f"No encontré «{nombre.split('/')[-1]}» en la pantalla")
        return caja

    def clic(self, nombre, **kwargs):
        caja = self.buscar(nombre, **kwargs)
        self.acciones.clic(caja)
        self.acciones.pausa(0.3, 0.6)
        return caja

    def escribir(self, campo, texto):
        self.clic(campo, bajando=True)
        self.acciones.pegar(texto)
        self.acciones.cerrar_globos()

    # ---------- pasos ----------
    def subir_fotos(self, plantilla):
        carpeta = self.carpeta_subidas / plantilla.nombre
        nombres = preparar_fotos(plantilla.fotos, carpeta, self.reducir_fotos)
        self.clic("crear/agregar_fotos", espera=15)
        # Esperamos a que se abra la ventana "Abrir" de Windows en vez de 2 s fijos.
        if not self.acciones.esperar_ventana(VENTANA_ABRIR, espera=6):
            time.sleep(1.5)
        self.acciones.pegar(str(carpeta))
        self.acciones.tecla("enter")
        time.sleep(0.8)
        self.acciones.pegar(" ".join(f'"{n}"' for n in nombres))
        self.acciones.tecla("enter")
        self.acciones.esperar_ventana(VENTANA_ABRIR, abierta=False, espera=6)
        # Las fotos terminan de subir mientras llenamos lo demas; antes de "Siguiente"
        # nos aseguramos de que haya pasado al menos este tiempo.
        self.fotos_listas = time.time() + 2 + (0.8 if self.reducir_fotos else 1.6) * len(nombres)
        time.sleep(1)

    def elegir_opcion(self, campo, subcarpeta, valor):
        abierto = self.clic(campo, bajando=True)
        # Facebook abre la lista debajo del campo, o encima si el campo esta en la
        # mitad de abajo de la pantalla. Si la opcion no se ve, bajamos dentro de la lista.
        _, alto = self.acciones.tamano_pantalla()
        paso = self.vision.px(150)
        lista = (abierto.x, abierto.y - paso if abierto.y > alto / 2 else abierto.y + paso)

        def bajar_lista():
            self.acciones.rueda(lista, -200)
            time.sleep(0.4)

        self.clic(f"crear/{subcarpeta}/{valor}", espera=12, mientras=bajar_lista)

    def poner_descripcion(self, texto):
        # "Mas detalles" a veces ya viene abierta y a veces no. Primero buscamos
        # Descripcion bajando la pagina; si no aparece, subimos, abrimos
        # "Mas detalles" y volvemos a buscar.
        for intento in range(3):
            try:
                self.clic("crear/descripcion", espera=4, bajando=True)
                break
            except FaltaBoton:
                if intento == 2:
                    raise
                self.acciones.rueda(self.formulario, 2000)  # volver arriba del formulario
                time.sleep(0.8)
                self.clic("crear/mas_detalles", bajando=True)
        self.acciones.pegar(texto)
        self.acciones.cerrar_globos()

    def marcar_grupos(self):
        marcados = 0
        sin_nuevos = 0
        while marcados < self.max_grupos and sin_nuevos < 2:
            casillas = self.vision.buscar_todas("crear/casilla", parecido=0.9)
            sin_nuevos = 0 if casillas else sin_nuevos + 1
            for caja in casillas:
                self.acciones.mover(caja, 0.08)
                self.acciones.pyautogui.click()
                marcados += 1
                time.sleep(0.15)
                if marcados >= self.max_grupos:
                    break
            self.acciones.rueda(self.formulario, -300)
            time.sleep(0.5)
        eventos.decir(f"   Grupos marcados: {marcados}")
        return marcados

    def pasar_a_grupos(self):
        """Clic en "Siguiente" hasta que la pantalla cambie (si las fotos no habian
        terminado de subir, Facebook todavia no deja pasar)."""
        for _ in range(4):
            self.clic("crear/siguiente", espera=15, bajando=True)
            if self.vision.esperar_que_se_vaya("crear/siguiente", espera=5):
                self.acciones.pausa(0.8, 1.2)  # que carguen los grupos
                return
            eventos.decir("   «Siguiente» sigue en pantalla; espero y pruebo otra vez.")
        raise FaltaBoton("Di clic en «Siguiente» y la página no avanzó")

    def publicar_uno(self, plantilla, confirmar):
        eventos.decir(f"Artículo: {plantilla.titulo} ({len(plantilla.fotos)} fotos)")
        eventos.paso("Abriendo «Crear publicación»")
        self.acciones.ir_a(URL_CREAR)
        titulo = self.vision.esperar("crear/titulo", espera=20)  # tambien espera a que cargue
        if not titulo and self.formulario_a_medias:
            # El articulo anterior fallo con el formulario lleno: el navegador puede
            # preguntar "¿Salir de la pagina?". Enter elige "Salir".
            self.acciones.tecla("enter")
            titulo = self.vision.esperar("crear/titulo", espera=20)
        if not titulo and self.vision.escala:
            self.vision.escala = None  # por si el tamano guardado de esta PC ya no sirve
            titulo = self.vision.esperar("crear/titulo", espera=8)
        if not titulo:
            valor, tamano = self.vision.diagnostico("crear/titulo")
            eventos.decir(f"   Lo más parecido a «titulo»: {valor:.0%} (tamaño {tamano:.0%})")
            raise FaltaBoton("No cargó la página para crear el artículo")
        self.formulario_a_medias = True
        # La rueda se usa en el centro del panel del formulario (a la altura del
        # titulo en horizontal, a media pantalla en vertical).
        _, alto = self.acciones.tamano_pantalla()
        self.formulario = (titulo.x, int(alto * 0.55))

        eventos.paso(f"Subiendo {len(plantilla.fotos)} fotos")
        self.subir_fotos(plantilla)
        eventos.paso("Escribiendo título y precio")
        self.escribir("crear/titulo", plantilla.titulo)
        self.escribir("crear/precio", plantilla.precio)
        eventos.paso(f"Categoría: {plantilla.categoria}")
        self.elegir_opcion("crear/categoria", "categorias", plantilla.categoria)
        eventos.paso(f"Estado: {plantilla.estado}")
        self.elegir_opcion("crear/estado", "estados", plantilla.estado)
        if plantilla.descripcion:
            eventos.paso("Pegando la descripción")
            self.poner_descripcion(plantilla.descripcion)

        faltan = self.fotos_listas - time.time()
        if faltan > 0:
            eventos.paso("Esperando que terminen de subir las fotos")
            time.sleep(faltan)
        self.pasar_a_grupos()
        eventos.paso("Marcando grupos")
        grupos = self.marcar_grupos()
        eventos.paso("Publicando" if confirmar else "Prueba: no publico")

        if not confirmar:
            boton = self.buscar("crear/publicar", espera=10)
            self.acciones.mover(boton, 0.4)
            eventos.decir("   MODO PRUEBA: aquí le daría clic a «Publicar». No publiqué nada.")
            return f"Prueba completa ({grupos} grupos)"
        # Si el boton sigue en pantalla despues del clic, no se publico: reintentamos.
        # Esperamos a que desaparezca (antes eran 5 a 8 s fijos).
        for intento in range(3):
            self.clic("crear/publicar", espera=10)
            if self.vision.esperar_que_se_vaya("crear/publicar", espera=12):
                self.acciones.pausa(1, 1.5)
                eventos.decir("   Publicado.")
                self.formulario_a_medias = False
                return f"Publicado en {grupos} grupos"
            eventos.decir(f"   «Publicar» sigue en pantalla, intento {intento + 2}...")
        raise FaltaBoton("Di clic en «Publicar» 3 veces y no se publicó")

    def correr(self, carpetas, confirmar, reintentar=True, pausa=(5, 10)):
        """Publica cada carpeta. Devuelve la lista de carpetas que fallaron."""
        lista = [plantillas_mod.leer(c) for c in carpetas]
        eventos.emitir("inicio", total=len(lista), articulos=[p.nombre for p in lista])
        fallidas = self._ronda(lista, confirmar, pausa, numero=1)
        if fallidas and reintentar:
            eventos.decir(f"\nReintento una vez los que fallaron ({len(fallidas)})...")
            fallidas = self._ronda(fallidas, confirmar, pausa, numero=2)
        return [p.nombre for p in fallidas]

    def _ronda(self, lista, confirmar, pausa, numero):
        fallidas = []
        for i, plantilla in enumerate(lista, 1):
            eventos.emitir("articulo", carpeta=plantilla.nombre, titulo=plantilla.titulo,
                           estado="trabajando", indice=i, total=len(lista), ronda=numero)
            try:
                detalle = self.publicar_uno(plantilla, confirmar)
                eventos.emitir("articulo", carpeta=plantilla.nombre, titulo=plantilla.titulo,
                               estado="publicado" if confirmar else "probado", detalle=detalle)
            except FailSafeException:
                raise
            except Exception as e:  # noqa: BLE001 - un articulo malo no detiene a los demas
                captura = self.acciones.captura(
                    self.carpeta_registro / f"fallo_r{numero}_{i:02d}_{plantilla.nombre}.png")
                eventos.decir(f"   ✖ {e}. Guardé la captura y sigo con el siguiente.")
                eventos.emitir("articulo", carpeta=plantilla.nombre, titulo=plantilla.titulo,
                               estado="fallo", detalle=str(e), captura=captura)
                fallidas.append(plantilla)
                self.acciones.tecla("esc")  # cerrar la ventana de Windows o un menu que haya quedado abierto
            if i < len(lista):
                self.acciones.pausa(*pausa)
        return fallidas
