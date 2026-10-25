"""Borrar y publicar sin tocar el mouse de verdad."""
import json

from PIL import Image

from conftest import BOTONES, pantalla
from marketplace_bot.motor import eventos, navegador
from marketplace_bot.motor.borrar import BorrarBot
from marketplace_bot.motor.publicar import FaltaBoton, PublicarBot, preparar_fotos
from marketplace_bot.motor.vision import Vision


# ---------- borrar ----------
def test_borrar_con_pagina_vacia_termina_bien(acciones, tmp_path):
    """24 de octubre: no había nada que borrar y el bot lo daba como error."""
    bot = BorrarBot(Vision(BOTONES, capturar=pantalla("borrar_pagina_vacia")), acciones, tmp_path)
    borradas, ok, mensaje = bot.correr(confirmar=True, maximo=20)
    assert (borradas, ok) == (0, True)
    assert "No había publicaciones" in mensaje
    assert not [h for h in acciones.hechas if h[0] == "captura"]  # sin captura de error


def test_borrar_reconoce_que_hay_publicaciones(acciones, tmp_path):
    bot = BorrarBot(Vision(BOTONES, capturar=pantalla("borrar_publicacion")), acciones, tmp_path)
    estado, caja = bot.esperar_pagina()
    assert estado == "hay" and caja is not None


def test_borrar_prueba_encuentra_el_menu(acciones, tmp_path):
    """Prueba: clic en "..." y busca "Eliminar publicacion" (con la captura del menu abierto)."""
    capturas = {"actual": "borrar_publicacion"}
    imagenes = {n: Image.open(f"tests/capturas/{n}.png").convert("RGB")
                for n in ("borrar_publicacion", "borrar_menu_opciones")}
    vision = Vision(BOTONES, capturar=lambda: imagenes[capturas["actual"]])
    bot = BorrarBot(vision, acciones, tmp_path)
    estado, compartir = bot.esperar_pagina()
    # Despues del clic en "...", la pantalla muestra el menu.
    acciones.clic = lambda punto: (acciones.hechas.append(("clic", (punto,))), capturas.update(actual="borrar_menu_opciones"))
    bot.zona_alrededor = lambda punto: None  # la captura del menu es de otra pantalla: buscamos en toda
    assert bot.borrar_una(compartir, confirmar=False)


# ---------- publicar ----------
def test_fotos_reducidas(tmp_path):
    grande = tmp_path / "grande.jpg"
    Image.new("RGB", (4032, 3024), "blue").save(grande)
    chica = tmp_path / "chica.png"
    Image.new("RGB", (800, 600), "red").save(chica)
    nombres = preparar_fotos([grande, chica], tmp_path / "subir")
    assert nombres == ["01.jpg", "02.jpg"]
    assert max(Image.open(tmp_path / "subir" / "01.jpg").size) == 1600
    assert Image.open(tmp_path / "subir" / "02.jpg").size == (800, 600)


def _plantilla(carpeta, titulo):
    carpeta.mkdir(parents=True)
    (carpeta / "datos.txt").write_text(f"titulo: {titulo}\nprecio: 100\ncategoria: Varios\nestado: Nuevo\n", "utf-8")
    Image.new("RGB", (100, 100)).save(carpeta / "01.jpg")
    return carpeta


def test_un_articulo_que_falla_no_detiene_a_los_demas(acciones, tmp_path, capsys):
    carpetas = [_plantilla(tmp_path / n, n.upper()) for n in ("uno", "dos", "tres")]
    bot = PublicarBot(Vision(BOTONES, capturar=pantalla("borrar_pagina_vacia")), acciones, tmp_path, tmp_path / "s")
    intentos = []

    def publicar_uno(plantilla, confirmar):
        intentos.append(plantilla.nombre)
        if plantilla.nombre == "dos":
            raise FaltaBoton("No encontré «precio» en la pantalla")
        return "Publicado en 5 grupos"

    bot.publicar_uno = publicar_uno
    fallidas = bot.correr(carpetas, confirmar=True, reintentar=True, pausa=(0, 0))
    assert fallidas == ["dos"]
    assert intentos == ["uno", "dos", "tres", "dos"]  # reintenta una vez el que fallo
    lineas = [eventos.leer_linea(linea)[0] for linea in capsys.readouterr().out.splitlines()]
    finales = [(e["carpeta"], e["estado"]) for e in lineas if e and e["tipo"] == "articulo" and e["estado"] != "trabajando"]
    assert finales == [("uno", "publicado"), ("dos", "fallo"), ("tres", "publicado"), ("dos", "fallo")]
    assert any(h[0] == "captura" and "fallo_r1_02_dos" in h[1][0] for h in acciones.hechas)


def test_falta_recorte_explica_que_hacer(acciones, tmp_path):
    bot = PublicarBot(Vision(BOTONES, capturar=pantalla("borrar_pagina_vacia")), acciones, tmp_path, tmp_path)
    try:
        bot.buscar("crear/categorias/Hogar")
    except FaltaBoton as e:
        assert "Falta el recorte" in str(e)
    else:
        raise AssertionError("debía fallar")


def test_cierra_globos_despues_de_escribir(acciones, tmp_path):
    """24 de octubre: el globo "Saved info" de Edge tapó el formulario."""
    bot = PublicarBot(Vision(BOTONES, capturar=pantalla("publicar_lista_estados")), acciones, tmp_path, tmp_path)
    bot.clic = lambda *a, **k: None
    bot.escribir("crear/titulo", "Pantalla M558")
    assert [h[0] for h in acciones.hechas] == ["pegar", "cerrar_globos"]


# ---------- navegador ----------
class Ventana:
    def __init__(self, titulo):
        self.title = titulo


def test_elige_la_ventana_del_perfil_pedido():
    ventanas = [Ventana("Facebook - Personal - Microsoft​ Edge"), Ventana("Facebook and 6 more pages - Work - Microsoft Edge")]
    ventana, aviso = navegador.elegir(ventanas, "Work - Microsoft Edge")
    assert "Work" in ventana.title and not aviso


def test_avisa_si_hay_varios_perfiles_con_facebook():
    ventanas = [Ventana("Facebook - Personal - Microsoft Edge"), Ventana("(1) Facebook - Work - Microsoft Edge")]
    _, aviso = navegador.elegir(ventanas, "")
    assert "varios perfiles" in aviso


def test_no_usa_otra_cuenta_si_no_encuentra_la_elegida():
    try:
        navegador.elegir([Ventana("Facebook - Google Chrome")], "Work - Microsoft Edge")
    except navegador.NavegadorNoEncontrado:
        pass
    else:
        raise AssertionError("debía negarse")


def test_perfil_del_titulo():
    assert navegador.perfil("Facebook and 6 more pages - Work - Microsoft Edge") == "Work - Microsoft Edge"
    assert navegador.perfil("(1) Facebook - Google Chrome") == "Google Chrome"


# ---------- eventos ----------
def test_eventos_ida_y_vuelta(capsys):
    eventos.emitir("articulo", carpeta="kz", estado="publicado", titulo="🎧 KZ")
    evento, texto = eventos.leer_linea(capsys.readouterr().out.strip())
    assert texto is None and evento["titulo"] == "🎧 KZ"
    assert eventos.leer_linea("hola\n") == (None, "hola\n")
    assert json.loads('{"a": 1}') == {"a": 1}


def test_espera_que_la_pagina_deje_de_moverse(acciones, tmp_path):
    """25 de octubre: un aviso cargó arriba y corrió todo; el bot buscó el "..." donde ya no estaba."""
    quieta = Image.open("tests/capturas/borrar_publicacion.png").convert("RGB")
    corrida = Image.new("RGB", quieta.size, (24, 25, 26))
    corrida.paste(quieta.crop((0, 0, quieta.width, quieta.height - 60)), (0, 60))
    vistas = [quieta, corrida, corrida]  # primero arriba, luego se corre 60 px y se queda
    vision = Vision(BOTONES, capturar=lambda: vistas.pop(0) if len(vistas) > 1 else vistas[0])
    estado, caja = BorrarBot(vision, acciones, tmp_path).esperar_pagina()
    original = Vision(BOTONES, capturar=lambda: quieta).buscar("borrar/compartir")
    assert estado == "hay" and caja.top - original.top == 60


def test_si_falla_recarga_una_vez_y_sigue(acciones, tmp_path):
    bot = BorrarBot(Vision(BOTONES, capturar=pantalla("borrar_publicacion")), acciones, tmp_path)
    intentos = []

    def borrar_una(compartir, confirmar):
        intentos.append(1)
        return len(intentos) != 2  # la segunda falla una vez

    bot.borrar_una = borrar_una
    borradas, ok, mensaje = bot.correr(confirmar=True, maximo=3)
    assert (borradas, ok) == (3, True) and len(intentos) == 4
    assert [h for h in acciones.hechas if h[0] == "tecla" and h[1][0] == "f5"]


def test_minimiza_la_ventana_del_bot_si_tapa_facebook():
    class V(Ventana):
        isMinimized = False

        def minimize(self):
            self.isMinimized = True

    bot, barrita, edge = V("Marketplace bot"), V("Marketplace bot - progreso"), V("Facebook - Microsoft Edge")
    navegador.apartar_ventana_del_bot([bot, barrita, edge])
    assert bot.isMinimized and not barrita.isMinimized and not edge.isMinimized


def test_responde_vendiste_este_articulo(acciones, tmp_path):
    """25 de octubre: Facebook pregunta "¿Vendiste este artículo?" antes de eliminar."""
    vision = Vision(BOTONES, capturar=pantalla("borrar_vendiste"))
    opcion = vision.buscar("borrar/motivo_prefiero_no_responder")
    siguiente = vision.buscar("borrar/motivo_siguiente", parecido=0.75)
    assert opcion and siguiente and siguiente.x > opcion.x and siguiente.y > opcion.y
    # Despues del clic en "Siguiente" el cuadro desaparece.
    vistas = {"actual": "borrar_vendiste"}
    imagenes = {n: Image.open(f"tests/capturas/{n}.png").convert("RGB") for n in ("borrar_vendiste", "borrar_publicacion")}
    vision.capturar = lambda: imagenes[vistas["actual"]]
    clic_original = acciones.clic

    def clic(punto):
        clic_original(punto)
        if punto == siguiente:
            vistas["actual"] = "borrar_publicacion"

    acciones.clic = clic
    bot = BorrarBot(vision, acciones, tmp_path)
    bot.zona_centro = lambda: None  # la captura es solo el cuadro
    assert bot.responder_motivo(opcion)
    clics = [h[1][0] for h in acciones.hechas if h[0] == "clic"]
    assert clics[0][0] < opcion.left  # el circulito
    assert clics[1] == siguiente


def test_termina_solo_cuando_ya_no_queda_nada(acciones, tmp_path):
    """25 de octubre: borró todas y se quedó esperando en vez de terminar."""
    imagenes = {n: Image.open(f"tests/capturas/{n}.png").convert("RGB")
                for n in ("borrar_publicacion", "borrar_confirmacion", "borrar_pagina_vacia")}
    vista = {"actual": "borrar_publicacion"}
    bot = BorrarBot(Vision(BOTONES, capturar=lambda: imagenes[vista["actual"]]), acciones, tmp_path)

    def borrar_una(compartir, confirmar):
        vista["actual"] = "borrar_confirmacion"  # lista vacia sin el mensaje: no hay "Compartir"
        return True

    tecla_original = acciones.tecla

    def tecla(nombre):
        tecla_original(nombre)
        if nombre == "f5":
            vista["actual"] = "borrar_pagina_vacia"

    bot.borrar_una, acciones.tecla = borrar_una, tecla
    borradas, ok, mensaje = bot.correr(confirmar=True)
    assert (borradas, ok) == (1, True) and "No quedan" in mensaje


def test_espera_que_un_boton_se_vaya():
    vision = Vision(BOTONES, capturar=pantalla("borrar_publicacion"))
    assert not vision.esperar_que_se_vaya("borrar/compartir", espera=0.5)
    vacia = Image.new("RGB", (400, 300), (24, 25, 26))
    assert Vision(BOTONES, capturar=lambda: vacia).esperar_que_se_vaya("borrar/compartir", espera=0.5)


def test_el_registro_dice_cuanto_tarda_cada_paso(capsys):
    eventos.paso("Marcando grupos")
    salida = capsys.readouterr().out
    assert '"paso"' in salida and " s] Marcando grupos" in salida


def test_diagnostico_dice_lo_mas_parecido():
    vision = Vision(BOTONES, capturar=pantalla("borrar_publicacion"), escala=1.5)
    valor, tamano = vision.diagnostico("borrar/compartir")
    assert valor > 0.95 and tamano == 1.0 and vision.escala == 1.5
