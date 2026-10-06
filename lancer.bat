@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Ayden Transit

where py >nul 2>nul
if %errorlevel%==0 (set PYTHON=py -3) else (set PYTHON=python)

%PYTHON% --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python n'est pas installe.
    echo Installez-le depuis https://www.python.org/downloads/ en cochant "Add Python to PATH",
    echo puis relancez ce fichier.
    pause
    exit /b 1
)

if not exist .venv (
    echo Premiere installation, cela peut prendre quelques minutes...
    %PYTHON% -m venv .venv || goto erreur
)

if not exist .env copy .env.example .env >nul

.venv\Scripts\python -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto erreur
.venv\Scripts\python manage.py migrate --noinput || goto erreur
.venv\Scripts\python manage.py demo || goto erreur

echo.
echo ============================================================
echo  Ayden Transit est lance : http://127.0.0.1:8000
echo  Identifiant : admin    Mot de passe : ayden2026
echo  Laissez cette fenetre ouverte. Fermez-la pour arreter.
echo ============================================================
echo.
start "" http://127.0.0.1:8000
.venv\Scripts\python manage.py runserver 127.0.0.1:8000
goto fin

:erreur
echo.
echo Une erreur est survenue. Copiez le message ci-dessus pour obtenir de l'aide.
pause
exit /b 1

:fin
