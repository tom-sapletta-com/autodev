#!/usr/bin/env python3
import os
import sys
import json
import logging
import threading
import docker
from flask import Flask, request, jsonify

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/logs/sandbox_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sandbox_manager")

# Inicjalizacja klienta Docker
try:
    docker_client = docker.from_env()
    logger.info("Połączono z Docker API")
except Exception as e:
    logger.error(f"Błąd podczas łączenia z Docker API: {str(e)}")
    docker_client = None

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

# Lista aktywnych piaskownic
active_sandboxes = {}

@app.route("/status", methods=["GET"])
def get_status():
    """Endpoint do sprawdzania statusu menedżera piaskownic"""
    sandbox_statuses = {}
    for sandbox_id, sandbox_info in active_sandboxes.items():
        try:
            container = docker_client.containers.get(sandbox_info["container_id"])
            sandbox_statuses[sandbox_id] = {
                "status": container.status,
                "created": sandbox_info["created"],
                "feature_id": sandbox_info["feature_id"]
            }
        except Exception as e:
            sandbox_statuses[sandbox_id] = {
                "status": "error",
                "error": str(e)
            }
    
    return jsonify({
        "success": True,
        "docker_connected": docker_client is not None,
        "active_sandboxes": len(active_sandboxes),
        "sandboxes": sandbox_statuses
    })

@app.route("/create", methods=["POST"])
def create_sandbox():
    """Endpoint do tworzenia nowej piaskownicy"""
    if not docker_client:
        return jsonify({"success": False, "error": "Brak połączenia z Docker API"}), 500
    
    try:
        data = request.json
        feature_id = data.get("feature_id")
        code = data.get("code")
        
        if not feature_id or not code:
            return jsonify({"success": False, "error": "Brak wymaganych pól: feature_id, code"}), 400
        
        # Tworzenie unikalnego ID dla piaskownicy
        sandbox_id = f"sandbox_{feature_id}_{os.urandom(4).hex()}"
        
        # Tworzenie tymczasowego pliku z kodem
        code_path = f"/tmp/{sandbox_id}.py"
        with open(code_path, "w") as f:
            f.write(code)
        
        # Tworzenie kontenera piaskownicy
        container = docker_client.containers.run(
            image="python:3.9-slim",
            command=f"python /code/{sandbox_id}.py",
            volumes={
                code_path: {"bind": f"/code/{sandbox_id}.py", "mode": "ro"},
                "/logs": {"bind": "/logs", "mode": "rw"}
            },
            network="sandbox_network",
            detach=True,
            name=sandbox_id,
            remove=True
        )
        
        active_sandboxes[sandbox_id] = {
            "container_id": container.id,
            "feature_id": feature_id,
            "created": str(container.attrs["Created"])
        }
        
        logger.info(f"Utworzono piaskownicę: {sandbox_id} dla feature: {feature_id}")
        
        # Uruchomienie wątku monitorującego
        threading.Thread(target=monitor_sandbox, args=(sandbox_id, container.id, feature_id)).start()
        
        return jsonify({
            "success": True,
            "sandbox_id": sandbox_id,
            "container_id": container.id,
            "status": container.status
        })
    
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia piaskownicy: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/stop/<sandbox_id>", methods=["POST"])
def stop_sandbox(sandbox_id):
    """Endpoint do zatrzymywania piaskownicy"""
    if not docker_client:
        return jsonify({"success": False, "error": "Brak połączenia z Docker API"}), 500
    
    try:
        if sandbox_id not in active_sandboxes:
            return jsonify({"success": False, "error": "Piaskownica nie znaleziona"}), 404
        
        container_id = active_sandboxes[sandbox_id]["container_id"]
        
        try:
            container = docker_client.containers.get(container_id)
            container.stop(timeout=5)
            logger.info(f"Zatrzymano piaskownicę: {sandbox_id}")
        except Exception as e:
            logger.warning(f"Błąd podczas zatrzymywania kontenera {container_id}: {str(e)}")
        
        # Usunięcie tymczasowego pliku
        try:
            os.remove(f"/tmp/{sandbox_id}.py")
        except:
            pass
        
        # Usunięcie piaskownicy z listy aktywnych
        del active_sandboxes[sandbox_id]
        
        return jsonify({"success": True, "message": f"Piaskownica {sandbox_id} zatrzymana"})
    
    except Exception as e:
        logger.error(f"Błąd podczas zatrzymywania piaskownicy: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def monitor_sandbox(sandbox_id, container_id, feature_id):
    """Funkcja monitorująca stan piaskownicy"""
    try:
        container = docker_client.containers.get(container_id)
        result = container.wait()
        exit_code = result["StatusCode"]
        
        logger.info(f"Piaskownica {sandbox_id} zakończyła działanie z kodem: {exit_code}")
        
        # Zapisanie logów
        logs = container.logs().decode("utf-8")
        log_file = f"/logs/sandbox_{feature_id}.log"
        with open(log_file, "a") as f:
            f.write(f"\n--- Piaskownica {sandbox_id} ---\n")
            f.write(logs)
        
        # Usunięcie piaskownicy z listy aktywnych
        if sandbox_id in active_sandboxes:
            del active_sandboxes[sandbox_id]
        
        # Usunięcie tymczasowego pliku
        try:
            os.remove(f"/tmp/{sandbox_id}.py")
        except:
            pass
        
    except Exception as e:
        logger.error(f"Błąd podczas monitorowania piaskownicy {sandbox_id}: {str(e)}")

if __name__ == "__main__":
    logger.info("Uruchamianie Sandbox Manager...")
    app.run(host="0.0.0.0", port=5000)
