@echo off
title Configurar Servidor Local - Voz da Cura
echo.
echo =======================================================
echo   Configurador Automotico do Servidor Local
echo =======================================================
echo.
echo Este script vai:
echo 1. Instalar o Deno (decodificador de assinaturas do YouTube)
echo 2. Baixar e configurar o FFmpeg (mesclador de audio e video)
echo 3. Instalar os requisitos do Python (FastAPI, Uvicorn, etc.)
echo.
echo Pressione qualquer tecla para iniciar a configuracao...
pause > nul

echo.
echo [1/3] Instalando o Deno...
powershell -Command "irm https://deno.land/install.ps1 | iex"

echo.
echo [2/3] Baixando e configurando o FFmpeg...
if exist "ffmpeg.exe" (
    echo O FFmpeg ja esta configurado nesta pasta.
) else (
    echo Baixando o FFmpeg (cerca de 90MB). Por favor, aguarde...
    powershell -Command "$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'; $zip = 'ffmpeg.zip'; Invoke-WebRequest -Uri $url -OutFile $zip; Expand-Archive -Path $zip -DestinationPath 'ffmpeg_temp'; Get-ChildItem -Path 'ffmpeg_temp' -Filter 'ffmpeg.exe' -Recurse | Copy-Item -Destination '.'; Get-ChildItem -Path 'ffmpeg_temp' -Filter 'ffprobe.exe' -Recurse | Copy-Item -Destination '.'; Remove-Item -Path $zip -Force; Remove-Item -Path 'ffmpeg_temp' -Recurse -Force"
)

echo.
echo [3/3] Instalando dependencias do Python...
pip install -r requirements.txt

echo.
echo =======================================================
echo   CONFIGURACAO CONCLUIDA COM SUCESSO!
echo =======================================================
echo.
echo O computador esta pronto para rodar como servidor local!
echo Para iniciar o site localmente, dê um duplo clique no ficheiro:
echo.
echo      ==^> IniciarServidor.bat
echo.
echo E aceda ao endereço: http://localhost:8000 no seu navegador.
echo.
pause
