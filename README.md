# Marketplace bot 2.0

Publica y borra tus artículos de Facebook Marketplace moviendo el mouse sobre tu
navegador ya abierto (usa tu sesión tal cual: Chrome, Edge o Brave).

## Primera vez en una PC
1. Instalá Python desde python.org (marcá "Add python.exe to PATH").
2. Doble clic en `Instalar.bat` (la primera vez descarga la ventana nueva, tarda un poco).

## Uso diario
1. Abrí Facebook en tu navegador (zoom 100 %).
2. Doble clic en **`Abrir Marketplace Bot.bat`**.
3. En **Plantillas** marcá «Publicar hoy» en lo que sale hoy.
4. En **Hoy** revisá el semáforo y dale **Renovar mis publicaciones**
   (o «Solo publicar», «Solo borrar», «Probar sin publicar»).
5. Mientras trabaja queda una barrita arriba con el progreso. No toqués el mouse.
   Para detenerlo: botón **Detener** o llevá el mouse a una esquina.
6. Al terminar ves qué salió bien y qué falló, con la captura del fallo y el botón
   «Reintentar los que fallaron». Todo queda en **Historial**.

Si tenés Facebook abierto en varios perfiles (por ejemplo «Work» y «Personal»),
elegí cuál usar en **Ajustes › Cuenta y navegador**.

Si usás Edge, apagá «Guardar y rellenar información personal»
(`edge://settings/personalinfo`): su globo tapaba el formulario.

Si la ventana no abre, usá `Diagnostico.bat`: muestra el error.

## Carpetas

```
Marketplace bots/
├─ Abrir Marketplace Bot.bat   abre la ventana
├─ Instalar.bat                instala lo necesario (una vez por PC)
├─ Diagnostico.bat             abre la ventana con consola, para ver errores
├─ publicaciones/              las plantillas (una carpeta por artículo) + firma.txt
├─ recursos/botones/           recortes de los botones de Facebook
│  ├─ borrar/                  compartir, opciones, eliminar, confirmar, vacio
│  └─ crear/                   campos del formulario, categorias/, estados/
├─ registros/                  lo que pasó cada vez (solo en esta PC, no va a git)
├─ src/marketplace_bot/        el programa
│  ├─ config.py                rutas y ajustes
│  ├─ modelos.py               Plantilla y Resultado
│  ├─ plantillas.py            leer, guardar, duplicar plantillas
│  ├─ registros.py             registro por corrida e historial
│  ├─ ejecutor.py              corre el motor y cuenta lo que pasa
│  ├─ motor/                   lo que mueve el mouse (no sabe nada de la ventana)
│  │  ├─ vision.py             busca botones (tamaños, modo claro/oscuro, idioma)
│  │  ├─ acciones.py           mouse, teclado, portapapeles, capturas
│  │  ├─ navegador.py          encuentra la ventana y el perfil correctos
│  │  ├─ borrar.py
│  │  ├─ publicar.py
│  │  └─ cli.py                línea de comandos del motor
│  └─ ui/                      la ventana (Flet): app.py + vistas/
├─ tests/                      pruebas con capturas reales de Facebook
├─ docs/capturas/              capturas de referencia
└─ empaquetado/                para armar el .exe y el instalador
```

## Plantillas
Cada carpeta de `publicaciones/` es un artículo:
- `datos.txt`: `titulo:`, `precio:` (solo números), `categoria:`, `estado:`
- `descripcion.txt`: el texto tal cual se pega en Facebook
- `01.jpg`, `02.jpg`…: las fotos en orden (la primera es la portada, máximo 10)

`publicaciones/firma.txt` es tu bloque de contacto: el editor lo agrega con un botón.

## Cómo reconoce los botones
El bot busca en pantalla las imágenes de `recursos/botones/`. Cada categoría o
estado necesita su recorte en `crear/categorias/` o `crear/estados/`. Si Facebook
está en otro idioma, el mismo botón puede tener una variante `nombre_en.png`.
Los recortes deben ser solo el botón, sin el borde de la tarjeta: así sirven en
modo claro y oscuro.

Cuando algo falla, la captura queda en `registros/<fecha>/` con un círculo donde
dio clic y un cuadro donde buscó. Esa captura sirve para recortar lo que falte.

## Sin ventana (para pruebas)
```
set PYTHONPATH=src
python -m marketplace_bot motor publicar --solo kz-edx-pro          (prueba)
python -m marketplace_bot motor publicar --solo kz-edx-pro --confirmar
python -m marketplace_bot motor borrar --confirmar --max 5
python -m marketplace_bot motor ventanas
```

## Pruebas
```
pip install pytest
python -m pytest
```
Cada error real se guarda en `tests/capturas/` y se agrega una prueba, para que
lo que ya funcionaba no se vuelva a romper.

## El .exe
`empaquetado\construir_exe.bat` arma `dist\Marketplace Bot\` y
`empaquetado\instalador.iss` (Inno Setup) arma el instalador. El .exe guarda las
plantillas en `Documentos\Marketplace Bot` o en la carpeta que elijas en Ajustes.
