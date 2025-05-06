#!/bin/bash
# Uniwersalny skrypt do uruchamiania systemu autodev na Linux/Mac
set -e

# Sprawdzenie zależności
command -v terraform >/dev/null 2>&1 || { echo >&2 "Terraform nie jest zainstalowany."; exit 1; }
command -v ansible >/dev/null 2>&1 || { echo >&2 "Ansible nie jest zainstalowany."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo >&2 "Docker nie jest zainstalowany."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo >&2 "Docker Compose nie jest zainstalowany."; exit 1; }

# Inicjalizacja infrastruktury
terraform init
terraform apply -auto-approve

# Deployment przez Ansible (przykład)
# ansible-playbook -i inventory.ini playbook.yml

# Uruchomienie usług docker-compose (jeśli dotyczy)
docker-compose up -d

# Uruchomienie warstwy middleware
pip install -r requirements.txt
nohup uvicorn middleware-api.app:app --host 0.0.0.0 --port 5000 &

echo "System autodev uruchomiony."
