#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 n'est pas installé : https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Première installation, cela peut prendre quelques minutes..."
    python3 -m venv .venv
fi

[ -f .env ] || cp .env.example .env

.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py demo

echo
echo "============================================================"
echo " Ayden Transit est lancé : http://127.0.0.1:8000"
echo " Identifiant : admin    Mot de passe : ayden2026"
echo " Ctrl+C pour arrêter."
echo "============================================================"
echo

( sleep 2; (command -v open >/dev/null && open http://127.0.0.1:8000) || (command -v xdg-open >/dev/null && xdg-open http://127.0.0.1:8000) || true ) &
.venv/bin/python manage.py runserver 127.0.0.1:8000
