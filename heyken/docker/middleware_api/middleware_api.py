#!/usr/bin/env python3
import os
import json
import logging
import requests
from flask import Flask, request, jsonify

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/logs/middleware_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("middleware_api")

# Zmienne środowiskowe
ACTIVE_CORE_ID = os.environ.get("ACTIVE_CORE_ID", "1")
CORE1_URL = os.environ.get("CORE1_URL", "http://core1:5000")
CORE2_URL = os.environ.get("CORE2_URL", "http://core2:5000")
COMPONENT_REGISTRY_URL = os.environ.get("COMPONENT_REGISTRY_URL", "http://component_registry:5000")
LOGGER_API_URL = os.environ.get("LOGGER_API_URL", "http://logger_api:5000")
SYSTEM_MONITOR_URL = os.environ.get("SYSTEM_MONITOR_URL", "http://system_monitor:5000")

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint do sprawdzania stanu API"""
    return jsonify({
        "status": "healthy",
        "service": "middleware_api",
        "active_core": ACTIVE_CORE_ID
    })

@app.route("/proxy/<target_service>/<path:endpoint>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_request(target_service, endpoint):
    """Endpoint do przekierowywania żądań do odpowiednich usług"""
    try:
        # Określenie URL docelowego na podstawie usługi
        if target_service == "active_core":
            target_url = f"{CORE1_URL if ACTIVE_CORE_ID == '1' else CORE2_URL}/{endpoint}"
        elif target_service == "core1":
            target_url = f"{CORE1_URL}/{endpoint}"
        elif target_service == "core2":
            target_url = f"{CORE2_URL}/{endpoint}"
        elif target_service == "component_registry":
            target_url = f"{COMPONENT_REGISTRY_URL}/{endpoint}"
        elif target_service == "logger":
            target_url = f"{LOGGER_API_URL}/{endpoint}"
        elif target_service == "monitor":
            target_url = f"{SYSTEM_MONITOR_URL}/{endpoint}"
        else:
            return jsonify({"success": False, "error": f"Nieznana usługa: {target_service}"}), 400
        
        # Przekazanie metody, danych i nagłówków do usługi docelowej
        method = request.method
        headers = {key: value for key, value in request.headers if key != 'Host'}
        
        if method == "GET":
            response = requests.get(
                target_url,
                params=request.args,
                headers=headers
            )
        elif method == "POST":
            data = request.get_json(silent=True) or {}
            response = requests.post(
                target_url,
                json=data,
                headers=headers
            )
        elif method == "PUT":
            data = request.get_json(silent=True) or {}
            response = requests.put(
                target_url,
                json=data,
                headers=headers
            )
        elif method == "DELETE":
            response = requests.delete(
                target_url,
                headers=headers
            )
        
        # Logowanie żądania
        logger.info(f"Przekierowano {method} żądanie do {target_service}/{endpoint}, kod odpowiedzi: {response.status_code}")
        
        # Zwrócenie odpowiedzi z usługi docelowej
        return response.content, response.status_code, {'Content-Type': response.headers.get('Content-Type', 'application/json')}
    
    except Exception as e:
        logger.error(f"Błąd podczas przekierowywania żądania: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/cores", methods=["GET"])
def get_cores_status():
    """Endpoint do pobierania statusu obu rdzeni"""
    try:
        # Pobieranie statusu rdzenia 1
        try:
            core1_response = requests.get(f"{CORE1_URL}/health", timeout=2)
            core1_status = "active" if ACTIVE_CORE_ID == "1" else "standby"
            core1_health = core1_response.json() if core1_response.status_code == 200 else {"error": "Niedostępny"}
        except:
            core1_status = "down"
            core1_health = {"error": "Niedostępny"}
        
        # Pobieranie statusu rdzenia 2
        try:
            core2_response = requests.get(f"{CORE2_URL}/health", timeout=2)
            core2_status = "active" if ACTIVE_CORE_ID == "2" else "standby"
            core2_health = core2_response.json() if core2_response.status_code == 200 else {"error": "Niedostępny"}
        except:
            core2_status = "down"
            core2_health = {"error": "Niedostępny"}
        
        return jsonify({
            "success": True,
            "active_core": ACTIVE_CORE_ID,
            "cores": {
                "core1": {
                    "status": core1_status,
                    "health": core1_health
                },
                "core2": {
                    "status": core2_status,
                    "health": core2_health
                }
            }
        })
    
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statusu rdzeni: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/switch_core", methods=["POST"])
def switch_core():
    """Endpoint do przełączania aktywnego rdzenia"""
    try:
        data = request.json or {}
        new_core_id = data.get("core_id")
        
        if not new_core_id or new_core_id not in ["1", "2"]:
            return jsonify({"success": False, "error": "Nieprawidłowy ID rdzenia. Dozwolone wartości: 1, 2"}), 400
        
        if new_core_id == ACTIVE_CORE_ID:
            return jsonify({
                "success": True,
                "message": f"Rdzeń {new_core_id} jest już aktywny",
                "active_core": new_core_id
            })
        
        # Wywołanie API monitora systemu do przełączenia rdzenia
        try:
            response = requests.post(
                f"{SYSTEM_MONITOR_URL}/switch_core",
                json={"core_id": new_core_id},
                timeout=5
            )
            
            if response.status_code == 200:
                # Aktualizacja zmiennej środowiskowej
                global ACTIVE_CORE_ID
                ACTIVE_CORE_ID = new_core_id
                
                logger.info(f"Aktywny rdzeń przełączony na {new_core_id}")
                
                return jsonify({
                    "success": True,
                    "message": f"Rdzeń pomyślnie przełączony na {new_core_id}",
                    "active_core": new_core_id
                })
            else:
                error_msg = response.json().get("error", "Nieznany błąd")
                return jsonify({
                    "success": False,
                    "error": f"Błąd podczas przełączania rdzenia: {error_msg}"
                }), 500
                
        except Exception as e:
            logger.error(f"Błąd komunikacji z monitorem systemu: {str(e)}")
            return jsonify({"success": False, "error": f"Błąd komunikacji z monitorem systemu: {str(e)}"}), 500
    
    except Exception as e:
        logger.error(f"Błąd podczas przełączania rdzenia: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Uruchamianie Middleware API...")
    app.run(host="0.0.0.0", port=5000)
