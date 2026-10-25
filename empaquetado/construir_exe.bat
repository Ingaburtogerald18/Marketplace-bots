@echo off
rem Arma "dist\Marketplace Bot\Marketplace Bot.exe". Correlo en Windows, desde esta carpeta.
cd /d "%~dp0.."
set VENV=%LOCALAPPDATA%\MarketplaceBot\venv
"%VENV%\Scripts\python.exe" -m pip install "flet-cli==1.0.5" "pyinstaller>=6.10" || (pause & exit /b 1)
"%VENV%\Scripts\flet.exe" pack empaquetado\lanzar.py --yes --onedir ^
  --name "Marketplace Bot" --product-name "Marketplace Bot" --product-version 2.0.0 ^
  --file-description "Publica y borra tus articulos de Marketplace" ^
  --add-data "recursos;recursos" ^
  --hidden-import marketplace_bot.motor.cli ^
  --pyinstaller-build-args="--paths=src" ^
  --distpath dist
echo.
echo Si todo salio bien, esta en dist\Marketplace Bot\. Para el instalador, abri empaquetado\instalador.iss con Inno Setup.
pause
