"""Plantillas, registros e historial."""
import csv

from PIL import Image

from marketplace_bot import plantillas
from marketplace_bot.ejecutor import Ejecutor
from marketplace_bot.config import Ajustes
from marketplace_bot.modelos import Plantilla, Resultado
from marketplace_bot.motor import eventos
from marketplace_bot.registros import Corrida, leer_corridas


def test_lee_plantilla_con_crlf_y_bom(rutas):
    carpeta = rutas.plantillas / "kz"
    carpeta.mkdir()
    datos = "\ufefftitulo: 🎧 KZ EDX Pro\r\nprecio: 420\r\ncategoria: Electrónica e informática\r\nestado: Nuevo\r\n"
    (carpeta / "datos.txt").write_bytes(datos.encode())
    (carpeta / "descripcion.txt").write_bytes("✅ Linea 1\r\n\r\n💰 C$420\r\n".encode())
    Image.new("RGB", (10, 10)).save(carpeta / "02.jpg")
    Image.new("RGB", (10, 10)).save(carpeta / "01.jpg")
    p = plantillas.leer(carpeta)
    assert (p.titulo, p.precio, p.categoria) == ("🎧 KZ EDX Pro", "420", "Electrónica e informática")
    assert p.descripcion == "✅ Linea 1\n\n💰 C$420"
    assert [f.name for f in p.fotos] == ["01.jpg", "02.jpg"]
    assert plantillas.problemas(p, rutas) == []


def test_problemas_en_palabras_simples(rutas):
    p = Plantilla(carpeta=rutas.plantillas / "x", titulo="X", precio="C$ 50", categoria="Hogar", estado="Usado")
    lista = plantillas.problemas(p, rutas)
    assert "El precio debe ser solo números" in lista
    assert "No tiene fotos" in lista
    assert any("Hogar" in t for t in lista) and any("Usado" in t for t in lista)


def test_guardar_ordena_fotos_y_no_pierde_las_viejas(rutas, tmp_path):
    carpeta = rutas.plantillas / "mouse"
    carpeta.mkdir()
    for nombre, color in (("01.jpg", "red"), ("02.jpg", "blue")):
        Image.new("RGB", (10, 10), color).save(carpeta / nombre)
    nueva = tmp_path / "nueva.png"
    Image.new("RGB", (10, 10), "green").save(nueva)
    p = Plantilla(carpeta=carpeta, titulo="Mouse", precio="1000", categoria="Varios", estado="Nuevo", descripcion="Hola")
    # nuevo orden: la nueva primero, luego la 02, y se quita la 01
    guardada = plantillas.guardar(p, [nueva, carpeta / "02.jpg"])
    assert [f.name for f in guardada.fotos] == ["01.png", "02.jpg"]
    assert Image.open(guardada.fotos[0]).getpixel((0, 0)) == (0, 128, 0)
    assert Image.open(guardada.fotos[1]).getpixel((0, 0))[2] > 200
    assert not (carpeta / "_nuevas").exists()


def test_nombre_de_carpeta(rutas):
    assert plantillas.nombre_carpeta("🎧 KZ EDX Pro X — Audífonos", rutas.plantillas) == "kz-edx-pro-x-audifonos"
    (rutas.plantillas / "kz-edx-pro-x-audifonos").mkdir()
    assert plantillas.nombre_carpeta("KZ EDX Pro X — Audífonos", rutas.plantillas) == "kz-edx-pro-x-audifonos-2"


def test_firma(rutas):
    plantillas.guardar_firma(rutas, "📲 WhatsApp: 85944758\n")
    assert plantillas.leer_firma(rutas) == "📲 WhatsApp: 85944758"
    assert plantillas.listar(rutas.plantillas) == []  # firma.txt no es una plantilla


def test_corrida_honesta(rutas):
    corrida = Corrida(rutas, "publicar", [Resultado("a", "A"), Resultado("b", 'B "comillas", coma'), Resultado("c", "C")])
    corrida.resultado("a", estado="publicado")
    corrida.resultado("b", estado="trabajando")
    corrida.anotar("Artículo: A\n")
    corrida.terminar()
    estados = {r.carpeta: r.estado for r in corrida.resultados.values()}
    assert estados == {"a": "publicado", "b": "fallo", "c": "saltado"}
    filas = list(csv.reader(open(rutas.registros / "historial.csv", encoding="utf-8")))
    assert filas[0] == ["fecha", "usuario", "accion", "articulo", "resultado", "detalle"]
    assert [f[3:5] for f in filas[1:]] == [["a", "publicado"], ["b", "fallo"], ["c", "saltado"]]
    assert "Artículo: A" in rutas.ultimo_registro.read_text(encoding="utf-8")
    ultima = leer_corridas(rutas)[0]
    assert [r.estado for r in ultima["resultados"]] == ["publicado", "fallo", "saltado"]


def test_ejecutor_entiende_los_eventos(rutas, capsys):
    ejecutor = Ejecutor(rutas, Ajustes())
    corrida = Corrida(rutas, "publicar", [Resultado("kz", "KZ")])
    eventos.emitir("articulo", carpeta="kz", titulo="KZ", estado="trabajando", indice=1, total=1)
    eventos.emitir("articulo", carpeta="kz", titulo="KZ", estado="publicado", detalle="Publicado en 15 grupos")
    print("Texto normal")
    for linea in capsys.readouterr().out.splitlines(keepends=True):
        ejecutor._linea(corrida, linea)
    assert corrida.resultados["kz"].estado == "publicado"
    assert corrida.progreso == (1, 1, 1)
    assert "Texto normal" in (corrida.carpeta / "registro.txt").read_text(encoding="utf-8")


def test_la_barrita_sabe_que_paso_esta_haciendo(rutas, capsys):
    ejecutor = Ejecutor(rutas, Ajustes())
    corrida = Corrida(rutas, "borrar", [])
    eventos.paso("Confirmando")
    for linea in capsys.readouterr().out.splitlines(keepends=True):
        ejecutor._linea(corrida, linea)
    assert corrida.paso == "Confirmando"


def test_lo_que_dice_la_barrita(rutas):
    from marketplace_bot.ui.vistas.progreso import estado_barrita

    corrida = Corrida(rutas, "borrar", [])
    corrida.paso = "Confirmando"
    estado = estado_barrita(corrida)
    assert estado["titulo"] == "Borrando publicaciones viejas" and estado["paso"] == "Confirmando"
    corrida.borradas = 3
    assert "3 borradas" in estado_barrita(corrida)["titulo"]

    corrida = Corrida(rutas, "publicar", [Resultado("a", "Mouse"), Resultado("b", "KZ")])
    corrida.resultado("a", estado="publicado")
    corrida.resultado("b", estado="trabajando")
    corrida.progreso = (2, 2, 1)
    estado = estado_barrita(corrida)
    assert estado["titulo"] == "2 de 2 · KZ" and estado["valor"] == 0.5 and estado["detalle"].startswith("1 bien")


def test_las_corridas_llevan_el_usuario_y_se_filtran(rutas, monkeypatch):
    monkeypatch.setenv("USERNAME", "sarit")
    Corrida(rutas, "borrar", []).terminar()
    monkeypatch.setenv("USERNAME", "Gerald")
    mia = Corrida(rutas, "borrar", [])
    mia.terminar()
    assert mia.carpeta.name.endswith("_borrar_Gerald")
    assert len(leer_corridas(rutas)) == 2
    assert [c["usuario"] for c in leer_corridas(rutas, solo_mias=True)] == ["Gerald"]
