@echo off
title IGNIS - Serveur Multi-CIS
color 0A
cd /d "%~dp0"

echo.
echo  ============================================================
echo    IGNIS - SERVEUR MULTI-CIS
echo  ============================================================
echo.

:: Verifier que Python est disponible
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo  Telechargez Python sur https://www.python.org/downloads/
    echo  Cochez "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

:: Verifier que Flask est disponible
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installation de Flask en cours...
    pip install flask --quiet
    if errorlevel 1 (
        color 0C
        echo  [ERREUR] Impossible d'installer Flask.
        echo  Essayez manuellement : pip install flask
        pause
        exit /b 1
    )
    echo  [OK] Flask installe.
    echo.
)

:: Creer les dossiers necessaires s'ils n'existent pas
if not exist "configs"    mkdir configs
if not exist "databases"  mkdir databases
if not exist "interfaces" mkdir interfaces

echo  [OK] Dossiers verifies.
echo.
echo  Demarrage du serveur...
echo  Appuyez sur Ctrl+C pour arreter.
echo.
echo  ============================================================

:: Lancer le serveur
python serveur_multi_cis.py

echo.
echo  ============================================================
echo  Serveur arrete.
pause
