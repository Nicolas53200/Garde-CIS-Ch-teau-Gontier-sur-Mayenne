@echo off
title Serveur Garde CHG
color 0A
echo.
echo  ================================================
echo    DEMARRAGE DU SERVEUR GARDE CHG
echo  ================================================
echo.

:: Verifier que Python est installe
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERREUR : Python n'est pas installe ou pas dans le PATH
    echo  Telechargez Python sur https://www.python.org
    pause
    exit /b 1
)

:: Aller dans le dossier du script
cd /d "%~dp0"

echo  Demarrage en cours...
echo.
python server.py

echo.
echo  Serveur arrete.
pause
