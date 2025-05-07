#!/usr/bin/env python3
import os
import time
import json
import logging
import psycopg2
import threading
import socket
import requests
import schedule
from datetime import datetime
from flask import Flask, request, jsonify
from prometheus_client import start_http_server, Gauge, Counter

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/logs/system_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("system_monitor")

# Inicjalizacja zmiennych konfiguracyjnych
ACTIVE_CORE_ID = os.environ.get("ACTIVE_CORE_ID", "1")
DB_HOST = os.environ.get("DB_HOST", "system_db")
DB_NAME = os.environ.get("DB_NAME", "systemdb")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

# Metryki Prometheus
system_health = Gauge("system_health", "Overall system health (0-100)")
component_status = Gauge("component_status", "Status of individual components (0=down, 1=up)", ["component"])
api_requests = Counter("api_requests", "Count of API requests", ["endpoint"])
errors = Counter("errors", "Count of errors", ["type"])

# Połączenie z bazą danych
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except Exception as e:
        logger.error(f"Błąd połączenia z bazą danych: {str(e)}")
        errors.labels("database").inc()
        return None

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

# Lista komponentów systemu do monitorowania
system_components = [
    {"name": "core_manager", "url": f"http://core{ACTIVE_CORE_ID}:5000/health", "required": True},
    {"name": "feature_runner", "url": "http://feature_runner:5000/health", "required": True},
    {"name": "sandbox_manager", "url": "http://sandbox_manager:5000/status", "required": True},
    {"name": "component_registry", "url": "http://component_registry:5000/components", "required": True},
    {"name": "logger_api", "url": "http://logger_api:5000/logs?limit=1", "required": True},
    {"name": "system_db", "check_func": lambda: get_db_connection() is not None, "required": True}
]

# Stan systemu
system_state = {
    "overall_health": 100,
    "components": {},
    "last_updated": datetime.now().isoformat(),
    "active_core": ACTIVE_CORE_ID
}

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint do sprawdzania stanu zdrowia systemu"""
    api_requests.labels("/health").inc()
    return jsonify(system_state)

@app.route("/components", methods=["GET"])
def get_components():
    """Endpoint do pobierania statusu komponentów"""
    api_requests.labels("/components").inc()
    return jsonify({
        "success": True,
        "components": system_state["components"]
    })

@app.route("/switch_core", methods=["POST"])
def switch_core():
    """Endpoint do zmiany aktywnego rdzenia"""
    api_requests.labels("/switch_core").inc()
    data = request.json
    new_core_id = data.get("core_id")
    
    if not new_core_id:
        return jsonify({"success": False, "error": "Brak wymaganego pola: core_id"}), 400
    
    # Symulacja przełączenia rdzenia
    global ACTIVE_CORE_ID
    old_core_id = ACTIVE_CORE_ID
    ACTIVE_CORE_ID = new_core_id
    
    logger.info(f"Przełączenie rdzenia z {old_core_id} na {new_core_id}")
    
    # Aktualizacja stanu systemu
    system_state["active_core"] = ACTIVE_CORE_ID
    
    # Logowanie przełączenia rdzenia
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO activity_logs (core_id, log_type, action, status, details) VALUES (%s, %s, %s, %s, %s)",
                    (old_core_id, "core_switch", "switch_core", "success", json.dumps({"new_core_id": new_core_id}))
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Błąd podczas logowania przełączenia rdzenia: {str(e)}")
            errors.labels("database").inc()
        finally:
            conn.close()
    
    return jsonify({
        "success": True,
        "message": f"Rdzeń przełączony z {old_core_id} na {new_core_id}"
    })

def check_component_health(component):
    """Sprawdza stan zdrowia pojedynczego komponentu"""
    try:
        if "url" in component:
            response = requests.get(component["url"], timeout=5)
            is_healthy = response.status_code == 200
        elif "check_func" in component:
            is_healthy = component["check_func"]()
        else:
            is_healthy = False
        
        status = "up" if is_healthy else "down"
        system_state["components"][component["name"]] = {
            "status": status,
            "last_checked": datetime.now().isoformat()
        }
        
        component_status.labels(component["name"]).set(1 if is_healthy else 0)
        
        if not is_healthy and component["required"]:
            logger.warning(f"Komponent {component['name']} jest niedostępny!")
            errors.labels("component").inc()
        
        return is_healthy
    
    except Exception as e:
        logger.error(f"Błąd podczas sprawdzania komponentu {component['name']}: {str(e)}")
        system_state["components"][component["name"]] = {
            "status": "error",
            "error": str(e),
            "last_checked": datetime.now().isoformat()
        }
        component_status.labels(component["name"]).set(0)
        errors.labels("monitoring").inc()
        return False

def update_system_health():
    """Aktualizuje stan zdrowia całego systemu"""
    try:
        total_components = len(system_components)
        healthy_components = 0
        
        for component in system_components:
            if check_component_health(component):
                healthy_components += 1
        
        # Obliczanie ogólnego stanu zdrowia systemu
        health_percentage = (healthy_components / total_components) * 100
        system_state["overall_health"] = health_percentage
        system_state["last_updated"] = datetime.now().isoformat()
        
        system_health.set(health_percentage)
        
        # Logowanie stanu systemu
        logger.info(f"Stan zdrowia systemu: {health_percentage:.1f}% ({healthy_components}/{total_components} komponentów działa)")
        
        if health_percentage < 100:
            unhealthy = [c["name"] for c in system_components if system_state["components"].get(c["name"], {}).get("status") != "up"]
            logger.warning(f"Niedostępne komponenty: {', '.join(unhealthy)}")
    
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji stanu zdrowia systemu: {str(e)}")
        errors.labels("health_update").inc()

def monitor_thread():
    """Wątek monitorujący stan systemu"""
    logger.info("Rozpoczęcie monitorowania systemu")
    
    # Ustawienie harmonogramu
    schedule.every(30).seconds.do(update_system_health)
    
    # Pierwsze uruchomienie
    update_system_health()
    
    # Pętla monitorowania
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Uruchomienie serwera Prometheus
    start_http_server(9090)
    logger.info("Uruchomiono serwer metryczny Prometheus na porcie 9090")
    
    # Uruchomienie wątku monitorującego
    threading.Thread(target=monitor_thread, daemon=True).start()
    
    # Uruchomienie aplikacji Flask
    logger.info("Uruchamianie System Monitor API...")
    app.run(host="0.0.0.0", port=5000)
