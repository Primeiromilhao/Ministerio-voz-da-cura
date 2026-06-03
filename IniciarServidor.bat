@echo off
title Servidor Baixador - Ministerio Voz da Cura
echo.
echo =======================================================
echo   Iniciando o Servidor do Baixador - Voz da Cura
echo =======================================================
echo.
echo O servidor ficara ativo no endereco: http://localhost:8000
echo Mantenha esta janela aberta enquanto estiver a usar o site.
echo.
cd /d "%~dp0"
python main.py
pause
