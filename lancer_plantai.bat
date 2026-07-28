@echo off
setlocal
title PlantAI - Lancement

echo ============================================
echo   PlantAI - Demarrage du site
echo ============================================
echo.

REM Se placer a la racine du projet (dossier de ce fichier .bat)
cd /d "%~dp0"

REM Verifier que l'environnement virtuel Python existe
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [ERREUR] L'environnement virtuel Python est introuvable dans backend\.venv
    echo.
    echo Avant d'utiliser ce fichier, il faut faire une seule fois :
    echo   cd backend
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [1/3] Demarrage du backend (FastAPI)...
start "PlantAI - Backend" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate && uvicorn app:app --reload"

echo [2/3] Demarrage du frontend...
start "PlantAI - Frontend" cmd /k "cd /d "%~dp0frontend" && python -m http.server 8080"

echo [3/3] Ouverture du site dans le navigateur...
timeout /t 4 /nobreak >nul
start http://localhost:8080

echo.
echo ============================================
echo   PlantAI est lance !
echo   Site : http://localhost:8080
echo.
echo   Deux fenetres noires se sont ouvertes
echo   (backend et frontend) : NE PAS LES FERMER
echo   tant que vous utilisez le site.
echo.
echo   Pour tout arreter : fermez ces deux fenetres.
echo ============================================
echo.
pause
