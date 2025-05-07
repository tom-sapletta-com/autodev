FROM python:3.9-slim

WORKDIR /app

# Instalacja wymaganych pakietów systemowych
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Instalacja Docker CLI
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian \
    $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Tworzenie pliku głównego aplikacji
RUN echo '#!/usr/bin/env python3\n\
import os\n\
import sys\n\
import json\n\
import logging\n\
import threading\n\
import docker\n\
from flask import Flask, request, jsonify\n\
\n\
# Konfiguracja logowania\n\
logging.basicConfig(\n\
    level=logging.INFO,\n\
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",\n\
    handlers=[\n\
        logging.FileHandler("/data/sandbox_manager.log"),\n\
        logging.StreamHandler()\n\
    ]\n\
)\n\
logger = logging.getLogger("sandbox_manager")\n\
\n\
# Inicjalizacja klienta Docker\n\
docker_client = docker.from_env()\n\
\n\
app = Flask(__name__)\n\
\n\
@app.route("/status", methods=["GET"])\n\
def get_status():\n\
    """Endpoint do sprawdzania statusu piaskownicy"""\n\
    return jsonify({\n\
        "status": "running",\n\
        "name": "sandbox_manager",\n\
        "version": "1.0.0"\n\
    })\n\
\n\
@app.route("/create", methods=["POST"])\n\
def create_sandbox():\n\
    """Endpoint do tworzenia nowej piaskownicy"""\n\
    data = request.json\n\
    \n\
    sandbox_name = data.get("name", "default_sandbox")\n\
    logger.info(f"Tworzenie nowej piaskownicy: {sandbox_name}")\n\
    \n\
    return jsonify({\n\
        "success": True,\n\
        "sandbox_id": "sandbox_" + sandbox_name,\n\
        "message": f"Piaskownica {sandbox_name} utworzona pomyślnie"\n\
    })\n\
\n\
@app.route("/destroy", methods=["POST"])\n\
def destroy_sandbox():\n\
    """Endpoint do usuwania piaskownicy"""\n\
    data = request.json\n\
    \n\
    sandbox_id = data.get("sandbox_id")\n\
    logger.info(f"Usuwanie piaskownicy: {sandbox_id}")\n\
    \n\
    return jsonify({\n\
        "success": True,\n\
        "message": f"Piaskownica {sandbox_id} usunięta pomyślnie"\n\
    })\n\
\n\
if __name__ == "__main__":\n\
    logger.info("Uruchamianie Sandbox Manager...")\n\
    app.run(host="0.0.0.0", port=5000)\n\
' > /app/sandbox_manager.py

# Tworzenie katalogu na dane
RUN mkdir -p /data

# Ekspozycja portów
EXPOSE 5000

# Uruchomienie aplikacji
CMD ["python", "sandbox_manager.py"]
