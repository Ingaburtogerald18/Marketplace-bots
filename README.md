# Marketplace bot

Publica y borra tus articulos de Facebook Marketplace moviendo el mouse sobre tu
Chrome ya abierto (usa tu sesion tal cual).

## Primera vez en una PC
1. Instala Python desde python.org (marca "Add python.exe to PATH").
2. Doble clic en `Instalar.bat`.

## Uso diario
1. Abre Chrome con tu Facebook, maximizado, zoom 100%.
2. Doble clic en `Marketplace Bot.bat`.
3. En la ventana:
   - **Nueva / Editar / Duplicar**: plantillas con titulo, precio, categoria,
     estado, descripcion y fotos (la 1a es la portada; las HEIC del iPhone se
     convierten solas a JPG).
   - Clic en la columna **Publicar** para marcar lo que sale hoy (se guarda solo
     en esta PC).
   - **Prueba**: llena todo sin publicar. **Publicar marcados**, **Borrar
     publicaciones** y **Borrar y publicar** hacen el trabajo de verdad.
4. Mientras el bot trabaja, no muevas el mouse. Para detenerlo, lleva el mouse a
   una esquina de la pantalla o usa **Detener**.

## Compartir con otra persona (Google Drive)
Pon esta carpeta en Google Drive para escritorio y compartela con su correo.
Cada PC hace su propio `Instalar.bat` (el entorno de Python se guarda fuera de
la carpeta compartida). Si en otra PC el bot no encuentra un boton, guarda
`falta_<boton>.png` para recortarlo.

## Como reconoce los botones
El bot busca en pantalla las imagenes de `Botones/`. Cada categoria o estado que
uses necesita su imagen en `Botones/Crear/categorias/` o `Botones/Crear/estados/`.
