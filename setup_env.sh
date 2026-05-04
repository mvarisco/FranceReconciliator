#!/bin/bash
set -e

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Ambiente virtuale creato e dipendenze installate."
echo "Usa 'source .venv/bin/activate' per attivare l'ambiente."     