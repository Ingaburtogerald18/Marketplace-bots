"""Encontrar la ventana del navegador con Facebook y ponerla al frente.

Si en Ajustes elegiste una ventana (por ejemplo "Personal - Microsoft Edge"),
solo se usa una ventana cuyo titulo tenga ese texto: asi el bot nunca publica
en otro perfil u otra cuenta por accidente.
"""
import sys
import time

NAVEGADORES = ("Google Chrome", "Brave", "Microsoft Edge", "Opera", "Firefox")


class NavegadorNoEncontrado(Exception):
    pass


def _titulo(ventana):
    # Edge escribe "Microsoft​ Edge" con un espacio invisible en el titulo.
    return ventana.title.replace("​", "").strip()


def _ventanas():
    if sys.platform != "win32":
        return []
    try:
        import pygetwindow as gw
    except ImportError:
        return []
    return [v for v in gw.getAllWindows() if v.title.strip()]


def es_navegador(titulo):
    return any(n in titulo for n in NAVEGADORES)


def listar():
    """Titulos de las ventanas de navegador abiertas (las de Facebook primero)."""
    titulos = [_titulo(v) for v in _ventanas() if es_navegador(_titulo(v))]
    return sorted(set(titulos), key=lambda t: ("Facebook" not in t, t))


def perfil(titulo):
    """De "Facebook - Work - Microsoft Edge" saca "Work - Microsoft Edge" (perfil + navegador)."""
    partes = [p.strip() for p in titulo.split(" - ")]
    for i, parte in enumerate(partes):
        if es_navegador(parte):
            return " - ".join(partes[max(0, i - 1):i + 1]) if i >= 2 else parte
    return titulo


def elegir(ventanas, filtro=""):
    """Elige la ventana a usar. Devuelve (ventana, aviso)."""
    navegadores = [v for v in ventanas if es_navegador(_titulo(v))]
    if filtro:
        propias = [v for v in navegadores if filtro.lower() in _titulo(v).lower()]
        if not propias:
            raise NavegadorNoEncontrado(
                f"No encontré la ventana «{filtro}» que elegiste en Ajustes. "
                "Abrí ese navegador con Facebook o cambiá la ventana en Ajustes.")
        navegadores = propias
    con_facebook = [v for v in navegadores if "Facebook" in _titulo(v)]
    candidatas = con_facebook or navegadores
    if not candidatas:
        raise NavegadorNoEncontrado("No encontré ningún navegador abierto. Abrí Facebook en Chrome, Edge o Brave.")
    aviso = ""
    perfiles = {perfil(_titulo(v)) for v in con_facebook}
    if not filtro and len(perfiles) > 1:
        aviso = ("Hay Facebook abierto en varios perfiles (" + ", ".join(sorted(perfiles)) +
                 "). Uso el primero; elegí el correcto en Ajustes para no equivocarme de cuenta.")
    return candidatas[0], aviso


def _al_frente(hwnd):
    """Pone la ventana al frente. Windows bloquea esto si lo pide un programa que
    no esta al frente, asi que usamos los trucos de siempre: simular la tecla Alt
    y "engancharnos" a la ventana que si esta al frente."""
    import ctypes

    import pyautogui

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    pyautogui.press("alt")
    actual = user32.GetForegroundWindow()
    hilo_actual = user32.GetWindowThreadProcessId(actual, None)
    mi_hilo = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(hilo_actual, mi_hilo, True)
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        user32.AttachThreadInput(hilo_actual, mi_hilo, False)
    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    time.sleep(0.8)
    return user32.GetForegroundWindow() == hwnd


def preparar(url, filtro=""):
    """Deja Facebook al frente. Si no hay ventana elegida y Windows no deja
    traerla, abre la pagina con el navegador predeterminado."""
    ventanas = _ventanas()
    try:
        ventana, aviso = elegir(ventanas, filtro)
    except NavegadorNoEncontrado:
        if filtro:
            raise
        print("No vi ningún navegador; abro Facebook en tu navegador predeterminado...", flush=True)
        import webbrowser

        webbrowser.open(url)
        time.sleep(7)
        return ""
    if aviso:
        print("⚠ " + aviso, flush=True)
    print(f"Pongo al frente: {_titulo(ventana)}", flush=True)
    for _ in range(3):
        try:
            if _al_frente(ventana._hWnd):
                time.sleep(1)
                return _titulo(ventana)
        except Exception as e:  # noqa: BLE001 - seguimos intentando
            print(f"   (no pude: {e})", flush=True)
        time.sleep(0.5)
    if filtro:
        raise NavegadorNoEncontrado("Windows no me dejó poner el navegador al frente. Dale clic y probá otra vez.")
    print("   Windows no me dejó poner el navegador al frente; abro Facebook en el predeterminado.", flush=True)
    import webbrowser

    webbrowser.open(url)
    time.sleep(7)
    return ""
