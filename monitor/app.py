#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import sqlite3
import datetime
import threading
import subprocess
import signal
import psutil
from flask import Flask, render_template, jsonify, request, g

# Konfiguracja
PORT = int(os.environ.get('MONITOR_PORT', 8080))
DB_PATH = os.environ.get('MONITOR_DB', 'monitor.db')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('MONITOR_LOG_FILE', 'monitor.log')
APP_LOG_FILE = os.environ.get('APP_LOG_FILE', 'monitor.log')

# Konfiguracja loggera
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('evodev-monitor')

# Inicjalizacja Flask
app = Flask(__name__)

# Inicjalizacja bazy danych
def init_db():
    """Inicjalizacja bazy danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabela dla zdarzeń systemowych
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT,
            component TEXT,
            message TEXT,
            details TEXT
        )
        ''')
        
        # Tabela dla statusu systemu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_percent REAL,
            disk_usage REAL,
            docker_status TEXT
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Baza danych zainicjowana: {DB_PATH}")
    except Exception as e:
        logger.error(f"Błąd podczas inicjalizacji bazy danych: {str(e)}")

def log_event(event_type, component, message, details=None):
    """Zapisz zdarzenie do bazy danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        details_json = json.dumps(details) if details else None
        cursor.execute(
            "INSERT INTO system_events (event_type, component, message, details) VALUES (?, ?, ?, ?)",
            (event_type, component, message, details_json)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Błąd podczas zapisywania zdarzenia: {str(e)}")

def check_docker_status():
    """Sprawdź status usług Docker"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}: {{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Błąd uruchomienia Docker: {result.stderr}"
    except Exception as e:
        return f"Błąd sprawdzania statusu Docker: {str(e)}"

def monitor_system():
    """Monitoruj ogólny stan systemu i zapisz do bazy"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        docker_status = check_docker_status()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO system_status (cpu_percent, memory_percent, disk_usage, docker_status) VALUES (?, ?, ?, ?)",
            (cpu_percent, memory_percent, disk_usage, docker_status)
        )
        conn.commit()
        conn.close()
        
        logger.debug(f"Zapisano status: CPU: {cpu_percent}%, RAM: {memory_percent}%, DISK: {disk_usage}%")
    except Exception as e:
        logger.error(f"Błąd podczas monitorowania systemu: {str(e)}")

def get_stats():
    """Pobierz najnowsze statystyki z bazy danych"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Pobierz najnowszy status systemu
        cursor.execute("SELECT * FROM system_status ORDER BY timestamp DESC LIMIT 1")
        system_row = cursor.fetchone()
        system = dict(system_row) if system_row else {}
        
        # Pobierz ostatnie 10 zdarzeń
        cursor.execute("SELECT * FROM system_events ORDER BY timestamp DESC LIMIT 10")
        events = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "system": system,
            "events": events
        }
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statystyk: {str(e)}")
        return {"error": str(e)}

def monitoring_thread():
    """Wątek monitorujący"""
    while True:
        try:
            monitor_system()
        except Exception as e:
            logger.error(f"Błąd w wątku monitorującym: {str(e)}")
            log_event("ERROR", "monitor", f"Błąd monitorowania", {"error": str(e)})
        time.sleep(5)  # Monitoruj co 5 sekund

@app.route('/')
def index():
    """Strona główna"""
    return render_template('index.html')

@app.route('/logs')
def logs_view():
    """Strona z logami aplikacji"""
    return render_template('logs.html')

@app.route('/api/status')
def api_status():
    """Endpoint API zwracający aktualny status"""
    return jsonify(get_stats())

@app.route('/api/events')
def api_events():
    """Endpoint API ze zdarzeniami systemu"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM system_events ORDER BY timestamp DESC LIMIT ?", (limit,))
        events = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(events)
    except Exception as e:
        logger.error(f"Błąd podczas pobierania zdarzeń: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs')
def api_logs():
    """Endpoint API zwracający logi aplikacji"""
    try:
        # Ustaw domyślny plik logu lub pozwól na wybór
        log_file = request.args.get('file', APP_LOG_FILE)
        max_lines = request.args.get('lines', 100, type=int)
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(log_file):
            return jsonify({"error": f"Plik log {log_file} nie istnieje"}), 404
            
        # Odczytaj ostatnie linie z pliku
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Odczytaj ostatnie N linii
                all_lines = f.readlines()
                last_lines = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
                
                # Analizuj logi jako JSON jeśli to możliwe
                parsed_logs = []
                for line in last_lines:
                    try:
                        # Próbuj parsować jako JSON
                        log_entry = json.loads(line)
                        parsed_logs.append(log_entry)
                    except:
                        # Jeśli nie jest w formacie JSON, użyj jako tekst
                        parsed_logs.append({"raw": line.strip()})
                
                return jsonify({
                    "filename": log_file,
                    "total_lines": len(all_lines),
                    "displayed_lines": len(last_lines),
                    "logs": parsed_logs
                })
        except Exception as e:
            logger.error(f"Błąd podczas odczytu pliku log: {str(e)}")
            return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Błąd podczas pobierania logów: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/available_logs')
def api_available_logs():
    """Zwraca listę dostępnych plików logów"""
    log_dir = os.path.dirname(os.path.abspath(APP_LOG_FILE)) or '.'
    log_files = []
    
    # Scan for log files in the current and logs directory
    for root, _, files in os.walk(log_dir):
        for file in files:
            if file.endswith('.log'):
                log_path = os.path.join(root, file)
                size = os.path.getsize(log_path)
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(log_path)).strftime('%Y-%m-%d %H:%M:%S')
                log_files.append({
                    "filename": file,
                    "path": log_path,
                    "size": size,
                    "modified": mod_time
                })
    
    # Sprawdź również plik logu monitora
    monitor_log = os.path.abspath(LOG_FILE)
    if os.path.exists(monitor_log) and monitor_log not in [log['path'] for log in log_files]:
        size = os.path.getsize(monitor_log)
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(monitor_log)).strftime('%Y-%m-%d %H:%M:%S')
        log_files.append({
            "filename": os.path.basename(monitor_log),
            "path": monitor_log,
            "size": size,
            "modified": mod_time
        })
    
    return jsonify(log_files)

@app.route('/health')
def health():
    """Endpoint sprawdzający zdrowie aplikacji"""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})

def start_monitoring():
    """Uruchom wątek monitorujący w tle"""
    thread = threading.Thread(target=monitoring_thread)
    thread.daemon = True
    thread.start()
    logger.info("Uruchomiono wątek monitorujący")

def main():
    """Główna funkcja uruchamiająca aplikację"""
    init_db()
    
    # Zapisz zdarzenie startowe
    log_event("INFO", "monitor", "Monitor EvoDev uruchomiony", 
             {"pid": os.getpid(), "python": sys.version})
    
    # Uruchom monitoring w tle
    start_monitoring()
    
    # Uruchom aplikację Flask
    logger.info(f"Uruchamianie serwera na porcie {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == "__main__":
    main()
