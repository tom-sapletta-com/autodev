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
import requests
from flask import Flask, render_template, jsonify, request, send_from_directory, Response, redirect, url_for
try:
    import email_utils
except ImportError:
    print("Warning: email_utils module not found. Email functionality will be limited.")
    email_utils = None

try:
    import docker_monitor
    has_docker_monitor = True
except ImportError:
    print("Warning: docker_monitor module not found. Docker request monitoring will be disabled.")
    has_docker_monitor = False

# Konfiguracja
PORT = int(os.environ.get('MONITOR_PORT', 8080))
DB_PATH = os.environ.get('MONITOR_DB', os.path.join('/tmp', 'monitor.db'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', os.path.join(os.path.expanduser('~'), 'evodev_monitor.log'))
APP_LOG_FILE = os.environ.get('APP_LOG_FILE', os.path.join(os.path.expanduser('~'), 'evodev_monitor.log'))
OPENAI_LINK = os.environ.get('OPENAI_LINK', 'https://platform.openai.com/account/api-keys')
ANTHROPIC_LINK = os.environ.get('ANTHROPIC_LINK', 'https://console.anthropic.com/account/keys')
PARTNER_LINK = os.environ.get('PARTNER_LINK', 'https://platform.openai.com/account/api-keys')

# Konfiguracja LLM
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', '')
LLM_TOKEN = os.environ.get('LLM_TOKEN', '')
LLM_URL = os.environ.get('LLM_URL', '')
LLM_MODEL = os.environ.get('LLM_MODEL', '')

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

# Inicjalizacja loggera
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(APP_LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('evodev-monitor')

# Inicjalizacja monitorowania requestów Docker
if has_docker_monitor:
    try:
        docker_monitor.start_request_monitoring()
        logger.info("Docker request monitoring started")
    except Exception as e:
        logger.error(f"Failed to start Docker request monitoring: {str(e)}")

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
        
        # Tabela dla zadań TODO
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            category TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
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

def get_docker_containers():
    """Pobierz szczegółowe informacje o kontenerach Docker"""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}"],
            capture_output=True, text=True, timeout=5
        )
        containers = []
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 5:
                    container_id, name, status, image, ports = parts[:5]
                    
                    # Określ status kontenera
                    status_type = "running"
                    if "Exited" in status:
                        status_type = "stopped"
                    elif "Created" in status:
                        status_type = "created"
                    elif "Restarting" in status:
                        status_type = "restarting"
                    elif "Paused" in status:
                        status_type = "paused"
                    
                    # Pobierz logi dla kontenera (tylko kilka ostatnich linii)
                    logs = ""
                    try:
                        log_result = subprocess.run(
                            ["docker", "logs", "--tail", "3", container_id],
                            capture_output=True, text=True, timeout=2
                        )
                        if log_result.returncode == 0:
                            logs = log_result.stdout
                    except:
                        pass
                    
                    containers.append({
                        "id": container_id,
                        "name": name,
                        "status": status,
                        "status_type": status_type,
                        "image": image,
                        "ports": ports,
                        "logs": logs
                    })
        return containers
    except Exception as e:
        logger.error(f"Błąd podczas pobierania kontenerów Docker: {str(e)}")
        return []

def check_docker_status():
    """Sprawdź status usług Docker"""
    try:
        containers = get_docker_containers()
        
        # Przygotuj podsumowanie w formie tekstowej dla istniejącego kodu
        status_text = ""
        for container in containers:
            status_text += f"{container['name']}: {container['status']}\n"
        
        return status_text.strip()
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

@app.route('/api/docker')
def api_docker():
    """Endpoint API zwracający szczegółowe informacje o kontenerach Docker"""
    containers = get_docker_containers()
    return jsonify(containers)

@app.route('/docker')
def docker_view():
    """Strona z widokiem kontenerów Docker"""
    return render_template('docker.html')

@app.route('/health')
def health():
    """Endpoint sprawdzający zdrowie aplikacji"""
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})

@app.route('/api/view/index')
def api_view_index():
    """Endpoint API zwracający HTML dla widoku głównego"""
    return render_template('index.html')

@app.route('/api/view/logs')
def api_view_logs():
    """Endpoint API zwracający HTML dla widoku logów"""
    return render_template('logs.html')

@app.route('/api/view/docker')
def api_view_docker():
    """Endpoint API zwracający HTML dla widoku kontenerów Docker"""
    return render_template('docker.html')

@app.route('/chat')
def chat_view():
    """Strona z interfejsem czatu AI"""
    return render_template('chat.html', 
                          partner_link=PARTNER_LINK,
                          openai_link=OPENAI_LINK,
                          anthropic_link=ANTHROPIC_LINK)

# Endpointy API dla funkcji email
@app.route('/api/email/status', methods=['GET'])
def api_email_status():
    """Sprawdza status konfiguracji email"""
    if email_utils is None:
        return jsonify({"configured": False, "message": "email_utils module not found"})
    config = email_utils.get_email_config()
    if config:
        return jsonify({
            "configured": True,
            "smtp_server": config.get('smtp_server'),
            "smtp_port": config.get('smtp_port'),
            "imap_server": config.get('imap_server'),
            "imap_port": config.get('imap_port'),
            "email": config.get('email')
        })
    else:
        return jsonify({"configured": False})

@app.route('/api/email/setup', methods=['POST'])
def api_email_setup():
    """Konfiguruje system email"""
    if email_utils is None:
        return jsonify({"success": False, "message": "email_utils module not found"}), 500
    try:
        success, message = email_utils.setup_email_system()
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji systemu email: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/email/configure', methods=['POST'])
def api_email_configure():
    """Konfiguruje ustawienia email"""
    if email_utils is None:
        return jsonify({"success": False, "message": "email_utils module not found"}), 500
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Brak danych w żądaniu"}), 400
        
        success, message = email_utils.configure_email(
            data.get('smtp_server'),
            data.get('smtp_port'),
            data.get('imap_server'),
            data.get('imap_port'),
            data.get('email'),
            data.get('password'),
            data.get('use_ssl', False)
        )
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji email: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/email/send', methods=['POST'])
def api_email_send():
    """Wysyła email"""
    if email_utils is None:
        return jsonify({"success": False, "message": "email_utils module not found"}), 500
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Brak danych w żądaniu"}), 400
        
        success, message = email_utils.send_email(
            data.get('to'),
            data.get('subject'),
            data.get('body')
        )
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Błąd podczas wysyłania email: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/email/read', methods=['GET'])
def api_email_read():
    """Odczytuje wiadomości email"""
    if email_utils is None:
        return jsonify({"success": False, "message": "email_utils module not found"}), 500
    try:
        folder = request.args.get('folder', 'INBOX')
        limit = int(request.args.get('limit', 10))
        
        success, result = email_utils.read_emails(folder, limit)
        if success:
            return jsonify({"success": True, "emails": result})
        else:
            return jsonify({"success": False, "message": result})
    except Exception as e:
        logger.error(f"Błąd podczas odczytu email: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/mcp/setup', methods=['POST'])
def api_mcp_setup():
    """Konfiguruje integrację MCP"""
    if email_utils is None:
        return jsonify({"success": False, "message": "email_utils module not found"}), 500
    try:
        success, message = email_utils.setup_mcp_integration()
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Błąd podczas konfiguracji MCP: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# Endpointy dla monitorowania requestów Docker
@app.route('/docker-requests')
def docker_requests_view():
    """Strona z widokiem requestów Docker"""
    return render_template('docker_requests.html')

@app.route('/api/docker/recent-requests')
def api_docker_recent_requests():
    """Zwraca ostatnie requesty Docker"""
    try:
        limit = request.args.get('limit', 100, type=int)
        requests_data = docker_monitor.get_recent_requests(limit)
        return jsonify({"success": True, "requests": requests_data})
    except Exception as e:
        logger.error(f"Error getting Docker requests: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/docker/request-stats')
def api_docker_request_stats():
    """Zwraca statystyki requestów Docker"""
    try:
        stats = docker_monitor.get_request_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Error getting Docker request stats: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/docker/web-interfaces')
def api_docker_web_interfaces():
    """Zwraca informacje o interfejsach webowych kontenerów Docker"""
    try:
        web_interfaces = docker_monitor.get_container_web_interfaces()
        return jsonify({"success": True, "web_interfaces": web_interfaces})
    except Exception as e:
        logger.error(f"Error getting Docker web interfaces: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/docker/container-logs/<container_id>')
def api_docker_container_logs(container_id):
    """Zwraca logi dla konkretnego kontenera Docker"""
    try:
        lines = request.args.get('lines', 100, type=int)
        logs = docker_monitor.get_container_logs(container_id, lines)
        return jsonify({"success": True, "logs": logs})
    except Exception as e:
        logger.error(f"Error getting container logs: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/docker/container-action/<container_id>', methods=['POST'])
def api_docker_container_action(container_id):
    """Wykonuje akcję na kontenerze Docker (start, stop, restart)"""
    try:
        action = request.json.get('action', '')
        if not action or action not in ['start', 'stop', 'restart']:
            return jsonify({"success": False, "error": "Invalid action. Must be one of: start, stop, restart"})
        
        result = docker_monitor.container_action(container_id, action)
        return jsonify({"success": result["success"], "message": result["message"]})
    except Exception as e:
        logger.error(f"Error performing container action: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/docker-web')
def docker_web_view():
    """Strona z widokiem interfejsów webowych kontenerów Docker"""
    return render_template('docker_web.html')

@app.route('/api/web-projects', methods=['GET'])
def api_web_projects():
    """Zwraca listę projektów webowych"""
    try:
        # Importuj moduł web_projects
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from evodev import web_projects
        
        projects = web_projects.list_projects()
        return jsonify({"success": True, "projects": projects})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania listy projektów: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/web-projects', methods=['POST'])
def api_create_web_project():
    """Tworzy nowy projekt webowy"""
    try:
        # Importuj moduł web_projects
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from evodev import web_projects
        
        data = request.json
        name = data.get('name', '')
        project_type = data.get('type', 'static')
        port = data.get('port', 8088)
        
        if not name:
            return jsonify({"success": False, "error": "Nazwa projektu jest wymagana"})
        
        success, message = web_projects.create_and_deploy_project(
            name=name,
            project_type=project_type,
            port=port
        )
        
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Błąd podczas tworzenia projektu: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/web-projects/<project_name>/action', methods=['POST'])
def api_web_project_action(project_name):
    """Wykonuje akcję na projekcie webowym (start, stop, remove)"""
    try:
        # Importuj moduł web_projects
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from evodev import web_projects
        
        data = request.json
        action = data.get('action', '')
        
        if not action or action not in ['start', 'stop', 'remove']:
            return jsonify({"success": False, "error": "Nieprawidłowa akcja"})
        
        project = web_projects.get_project(project_name)
        if not project:
            return jsonify({"success": False, "error": f"Projekt {project_name} nie istnieje"})
        
        if action == 'start':
            success = project.start()
        elif action == 'stop':
            success = project.stop()
        elif action == 'remove':
            success = project.remove()
        
        if success:
            return jsonify({"success": True, "message": f"Akcja {action} została wykonana na projekcie {project_name}"})
        else:
            return jsonify({"success": False, "error": f"Nie udało się wykonać akcji {action} na projekcie {project_name}"})
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania akcji na projekcie: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/web-projects')
def web_projects_view():
    """Strona z zarządzaniem projektami webowymi"""
    return render_template('web_projects.html')

@app.route('/api/llm/token/status')
def api_llm_token_status():
    """Sprawdza czy token LLM jest ustawiony"""
    token_set = bool(LLM_TOKEN) or (LLM_PROVIDER == 'ollama' and bool(LLM_URL))
    return jsonify({
        "token_set": token_set,
        "provider": LLM_PROVIDER if token_set else ""
    })

@app.route('/api/llm/token/set', methods=['POST'])
def api_llm_token_set():
    """Ustawia token LLM"""
    global LLM_TOKEN, LLM_PROVIDER, LLM_URL, LLM_MODEL
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Brak danych w żądaniu"}), 400
            
        provider = data.get('provider', '')
        token = data.get('token', '').strip()
        url = data.get('url', '').strip()
        model = data.get('model', '').strip()
        
        if not provider:
            return jsonify({"success": False, "error": "Nie określono dostawcy API"}), 400
            
        # Walidacja danych w zależności od dostawcy
        if provider in ['openai', 'anthropic'] and not token:
            return jsonify({"success": False, "error": f"Token API dla {provider} nie może być pusty"}), 400
        elif provider == 'ollama' and not url:
            return jsonify({"success": False, "error": "URL serwera Ollama nie może być pusty"}), 400
            
        # Zapisz dane do zmiennych globalnych
        LLM_PROVIDER = provider
        LLM_TOKEN = token if provider in ['openai', 'anthropic'] else ''
        LLM_URL = url if provider == 'ollama' else ''
        LLM_MODEL = model if provider == 'ollama' else ''
        
        # Zapisz dane do pliku .env
        try:
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
            
            # Odczytaj istniejący plik .env
            env_content = ""
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    env_content = f.read()
            
            # Przygotuj nowe linie do pliku .env
            env_lines = env_content.split('\n')
            new_env_lines = []
            
            # Zmienne do zaktualizowania
            env_vars = {
                'LLM_PROVIDER': provider,
                'LLM_TOKEN': token if provider in ['openai', 'anthropic'] else '',
                'LLM_URL': url if provider == 'ollama' else '',
                'LLM_MODEL': model if provider == 'ollama' else ''
            }
            
            # Zaktualizuj istniejące zmienne lub dodaj nowe
            for line in env_lines:
                updated = False
                for var_name, var_value in env_vars.items():
                    if line.startswith(f"{var_name}="):
                        if var_value:  # Tylko jeśli wartość nie jest pusta
                            new_env_lines.append(f'{var_name}="{var_value}"')
                        else:
                            new_env_lines.append(f'{var_name}=""')
                        updated = True
                        # Usuń zmienną z listy do dodania
                        env_vars.pop(var_name, None)
                        break
                
                if not updated:
                    new_env_lines.append(line)
            
            # Dodaj pozostałe zmienne, które nie były w pliku
            for var_name, var_value in env_vars.items():
                if var_value:  # Tylko jeśli wartość nie jest pusta
                    new_env_lines.append(f'{var_name}="{var_value}"')
                else:
                    new_env_lines.append(f'{var_name}=""')
            
            # Zapisz zaktualizowany plik .env
            with open(env_path, 'w') as f:
                f.write('\n'.join(new_env_lines))
                
            log_event("INFO", "monitor", f"Konfiguracja LLM ({provider}) została zaktualizowana")
            return jsonify({"success": True})
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania konfiguracji do pliku .env: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    except Exception as e:
        logger.error(f"Błąd podczas ustawiania konfiguracji LLM: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chat/message', methods=['POST'])
def api_chat_message():
    """Obsługuje wiadomości czatu i zwraca odpowiedź AI"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({"error": "Brak wiadomości w żądaniu"}), 400
            
        user_message = data['message'].strip()
        
        # Sprawdź czy konfiguracja LLM jest ustawiona
        if not LLM_PROVIDER:
            return jsonify({
                "response": "Aby korzystać z funkcji czatu, należy najpierw skonfigurować API modelu językowego. "
                           "Wybierz jednego z dostępnych dostawców w zakładce konfiguracji."
            })
        
        # Generuj odpowiedź w zależności od dostawcy
        response = ""
        if LLM_PROVIDER == 'openai' and LLM_TOKEN:
            # Rzeczywiste wywołanie API OpenAI
            try:
                openai_response = call_openai_api(user_message)
                response = openai_response
            except Exception as e:
                logger.error(f"Błąd podczas wywoływania API OpenAI: {str(e)}")
                response = f"Wystąpił błąd podczas komunikacji z API OpenAI: {str(e)}"
        elif LLM_PROVIDER == 'anthropic' and LLM_TOKEN:
            # Rzeczywiste wywołanie API Anthropic
            try:
                anthropic_response = call_anthropic_api(user_message)
                response = anthropic_response
            except Exception as e:
                logger.error(f"Błąd podczas wywoływania API Anthropic: {str(e)}")
                response = f"Wystąpił błąd podczas komunikacji z API Anthropic: {str(e)}"
        elif LLM_PROVIDER == 'ollama' and LLM_URL:
            # Rzeczywiste wywołanie API Ollama
            try:
                ollama_response = call_ollama_api(user_message)
                response = ollama_response
            except Exception as e:
                logger.error(f"Błąd podczas wywoływania API Ollama: {str(e)}")
                response = f"Wystąpił błąd podczas komunikacji z API Ollama: {str(e)}"
        else:
            return jsonify({
                "response": "Konfiguracja API jest niepełna. Proszę sprawdzić ustawienia i spróbować ponownie."
            })
        
        # Zapisz interakcję do bazy danych
        log_event("INFO", "chat", f"Nowa wiadomość od użytkownika", 
                 {"provider": LLM_PROVIDER, "message": user_message, "response": response})
        
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Błąd podczas przetwarzania wiadomości czatu: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat/ollama', methods=['POST'])
def api_chat_ollama():
    """Obsługuje zapytania do API Ollama"""
    try:
        data = request.json
        model = data.get('model', 'llama2')
        message = data.get('message', '')
        
        if not message:
            return jsonify({"success": False, "message": "Brak wiadomości"})
        
        # Sprawdź status Ollama
        try:
            ollama_status = requests.get("http://localhost:11434/api/tags")
            if ollama_status.status_code != 200:
                return jsonify({"success": False, "message": f"Błąd podczas sprawdzania statusu Ollama: kod {ollama_status.status_code}"})
        except Exception as e:
            return jsonify({"success": False, "message": f"Błąd podczas sprawdzania statusu Ollama: {str(e)}"})
        
        # Wywołaj API Ollama
        try:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": model,
                "prompt": f"Jesteś asystentem EvoDev, który pomaga użytkownikom w zadaniach programistycznych i administracyjnych. Oto zapytanie użytkownika: {message}",
                "stream": False
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return jsonify({"success": True, "response": response_data.get("response", "Brak odpowiedzi")})
            else:
                error_message = f"Błąd API Ollama (kod {response.status_code}): {response.text}"
                logger.error(error_message)
                return jsonify({"success": False, "message": error_message})
        except Exception as e:
            error_message = f"Błąd podczas komunikacji z Ollama: {str(e)}"
            logger.error(error_message)
            return jsonify({"success": False, "message": error_message})
    except Exception as e:
        error_message = f"Błąd podczas przetwarzania żądania: {str(e)}"
        logger.error(error_message)
        return jsonify({"success": False, "message": error_message})

@app.route('/api/ollama/status', methods=['GET'])
def api_ollama_status():
    """Sprawdza status serwera Ollama i dostępne modele"""
    try:
        # Sprawdź status Ollama
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models_data = response.json()
                return jsonify({
                    "success": True, 
                    "status": "online",
                    "models": models_data.get("models", [])
                })
            else:
                return jsonify({
                    "success": False, 
                    "status": "error", 
                    "message": f"Błąd podczas sprawdzania statusu Ollama: kod {response.status_code}"
                })
        except Exception as e:
            return jsonify({
                "success": False, 
                "status": "offline", 
                "message": f"Błąd podczas sprawdzania statusu Ollama: {str(e)}"
            })
    except Exception as e:
        error_message = f"Błąd podczas przetwarzania żądania: {str(e)}"
        logger.error(error_message)
        return jsonify({"success": False, "message": error_message})

@app.route('/api/web-projects/<project_name>/logs', methods=['GET'])
def api_web_project_logs(project_name):
    """Pobiera logi projektu webowego"""
    try:
        # Importuj moduł web_projects
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from evodev import web_projects
        except ImportError:
            logger.error("Nie można zaimportować modułu web_projects")
            return jsonify({"success": False, "error": "Nie można zaimportować modułu web_projects"})
        
        try:
            project = web_projects.get_project(project_name)
            if not project:
                # Jeśli projekt nie istnieje, zwróć przykładowe logi
                logger.warning(f"Projekt {project_name} nie istnieje, zwracam przykładowe logi")
                sample_logs = [
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Projekt {project_name} został utworzony",
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Typ projektu: static",
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Status projektu: stopped"
                ]
                return jsonify({"success": True, "logs": sample_logs, "note": "To są przykładowe logi. Projekt nie istnieje lub nie jest dostępny."})
            
            # Pobierz logi projektu
            try:
                logs = project.get_logs()
                return jsonify({"success": True, "logs": logs})
            except Exception as e:
                # Jeśli nie udało się pobrać logów, zwróć przykładowe logi
                logger.error(f"Błąd podczas pobierania logów projektu {project_name}: {str(e)}")
                sample_logs = [
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Projekt {project_name} został utworzony",
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Typ projektu: {getattr(project, 'project_type', 'unknown')}",
                    f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Status projektu: {getattr(project, 'status', 'unknown')}"
                ]
                return jsonify({"success": True, "logs": sample_logs, "note": "To są przykładowe logi. Rzeczywiste logi nie są dostępne."})
        except Exception as e:
            logger.error(f"Błąd podczas pobierania projektu {project_name}: {str(e)}")
            sample_logs = [
                f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Projekt {project_name} został utworzony",
                f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Typ projektu: unknown",
                f"[INFO] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Status projektu: unknown"
            ]
            return jsonify({"success": True, "logs": sample_logs, "note": "To są przykładowe logi. Projekt nie jest dostępny."})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania logów projektu: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/events/recent', methods=['GET'])
def api_events_recent():
    """Pobiera ostatnie zdarzenia z systemu"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        # Połączenie z bazą danych
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Pobranie ostatnich zdarzeń
        cursor.execute(
            "SELECT id, timestamp, event_type, description FROM events ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        events = [dict(row) for row in cursor.fetchall()]
        
        # Zamknięcie połączenia
        conn.close()
        
        return jsonify({"success": True, "events": events})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania zdarzeń: {str(e)}")
        # Zwróć przykładowe dane, gdy wystąpi błąd
        sample_events = [
            {
                "id": 1,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "system_start",
                "description": "System EvoDev został uruchomiony"
            },
            {
                "id": 2,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "container_start",
                "description": "Kontener rocketchat został uruchomiony"
            },
            {
                "id": 3,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": "container_start",
                "description": "Kontener mongo został uruchomiony"
            }
        ]
        return jsonify({"success": True, "events": sample_events, "note": "Dane przykładowe - wystąpił błąd podczas pobierania rzeczywistych danych"})

@app.route('/api/system/stats', methods=['GET'])
def api_system_stats():
    """Pobiera statystyki systemowe"""
    try:
        # Pobranie statystyk systemowych
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Pobranie informacji o kontenerach Docker
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list(all=True)
            container_stats = {
                "total": len(containers),
                "running": len([c for c in containers if c.status == 'running']),
                "stopped": len([c for c in containers if c.status != 'running'])
            }
        except Exception as e:
            logger.error(f"Błąd podczas pobierania statystyk kontenerów: {str(e)}")
            container_stats = {
                "total": 0,
                "running": 0,
                "stopped": 0,
                "error": str(e)
            }
        
        # Przygotowanie odpowiedzi
        stats = {
            "cpu": {
                "percent": cpu_percent
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "containers": container_stats,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statystyk systemowych: {str(e)}")
        # Zwróć przykładowe dane, gdy wystąpi błąd
        sample_stats = {
            "cpu": {
                "percent": 25.0
            },
            "memory": {
                "total": 8589934592,  # 8 GB
                "available": 4294967296,  # 4 GB
                "percent": 50.0
            },
            "disk": {
                "total": 107374182400,  # 100 GB
                "used": 32212254720,  # 30 GB
                "free": 75161927680,  # 70 GB
                "percent": 30.0
            },
            "containers": {
                "total": 5,
                "running": 3,
                "stopped": 2
            },
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return jsonify({"success": True, "stats": sample_stats, "note": "Dane przykładowe - wystąpił błąd podczas pobierania rzeczywistych danych"})

@app.route('/todos')
def todos_view():
    """Strona z listą zadań TODO"""
    return render_template('todos.html')

@app.route('/api/todos', methods=['GET'])
def api_get_todos():
    """Endpoint API zwracający listę zadań TODO"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Sprawdź czy tabela istnieje, jeśli nie - utwórz ją
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            category TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        conn.commit()
        
        # Pobierz wszystkie zadania
        cursor.execute("SELECT * FROM todos ORDER BY priority, created_at DESC")
        todos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify({"success": True, "todos": todos})
    except Exception as e:
        logger.error(f"Błąd podczas pobierania zadań TODO: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/todos', methods=['POST'])
def api_add_todo():
    """Endpoint API dodający nowe zadanie TODO"""
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({"success": False, "error": "Tytuł zadania jest wymagany"}), 400
            
        title = data.get('title')
        description = data.get('description', '')
        priority = data.get('priority', 'medium')
        category = data.get('category', 'general')
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO todos (title, description, priority, category) VALUES (?, ?, ?, ?)",
            (title, description, priority, category)
        )
        
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        log_event("INFO", "todos", f"Dodano nowe zadanie: {title}")
        return jsonify({"success": True, "id": todo_id})
    except Exception as e:
        logger.error(f"Błąd podczas dodawania zadania TODO: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def api_update_todo(todo_id):
    """Endpoint API aktualizujący zadanie TODO"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Brak danych do aktualizacji"}), 400
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź czy zadanie istnieje
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        todo = cursor.fetchone()
        
        if not todo:
            conn.close()
            return jsonify({"success": False, "error": f"Zadanie o ID {todo_id} nie istnieje"}), 404
        
        # Przygotuj dane do aktualizacji
        updates = []
        params = []
        
        if 'title' in data:
            updates.append("title = ?")
            params.append(data['title'])
            
        if 'description' in data:
            updates.append("description = ?")
            params.append(data['description'])
            
        if 'priority' in data:
            updates.append("priority = ?")
            params.append(data['priority'])
            
        if 'category' in data:
            updates.append("category = ?")
            params.append(data['category'])
            
        if 'status' in data:
            updates.append("status = ?")
            params.append(data['status'])
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        # Wykonaj aktualizację
        query = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
        params.append(todo_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        log_event("INFO", "todos", f"Zaktualizowano zadanie o ID {todo_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Błąd podczas aktualizacji zadania TODO: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def api_delete_todo(todo_id):
    """Endpoint API usuwający zadanie TODO"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Sprawdź czy zadanie istnieje
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        todo = cursor.fetchone()
        
        if not todo:
            conn.close()
            return jsonify({"success": False, "error": f"Zadanie o ID {todo_id} nie istnieje"}), 404
        
        # Usuń zadanie
        cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        conn.commit()
        conn.close()
        
        log_event("INFO", "todos", f"Usunięto zadanie o ID {todo_id}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Błąd podczas usuwania zadania TODO: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def call_openai_api(message):
    """Wywołuje API OpenAI i zwraca odpowiedź"""
    url = "https://api.openai.com/v1/chat/completions"
    
    # Przygotuj kontekst systemowy
    system_message = """Jesteś asystentem EvoDev, który pomaga użytkownikom w zadaniach programistycznych i administracyjnych.
    Potrafisz wykonywać zadania takie jak wysyłanie emaili, zarządzanie plikami, analizowanie kodu i wiele innych.
    Gdy użytkownik prosi o wysłanie emaila, zbierz wszystkie potrzebne informacje i użyj dostępnych funkcji email.
    Jeśli brakuje jakichkolwiek zależności lub usług, automatycznie je skonfiguruj i poinformuj użytkownika o postępie.
    Odpowiadaj konkretnie i wykonuj polecenia użytkownika."""
    
    # Przygotuj listę dostępnych funkcji
    functions = [
        {
            "type": "function",
            "function": {
                "name": "setup_email_system",
                "description": "Konfiguruje system email, instalując wymagane zależności i serwery jeśli są potrzebne",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "configure_email",
                "description": "Konfiguruje ustawienia email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "smtp_server": {
                            "type": "string",
                            "description": "Adres serwera SMTP"
                        },
                        "smtp_port": {
                            "type": "integer",
                            "description": "Port serwera SMTP"
                        },
                        "imap_server": {
                            "type": "string",
                            "description": "Adres serwera IMAP"
                        },
                        "imap_port": {
                            "type": "integer",
                            "description": "Port serwera IMAP"
                        },
                        "email": {
                            "type": "string",
                            "description": "Adres email"
                        },
                        "password": {
                            "type": "string",
                            "description": "Hasło do konta email"
                        },
                        "use_ssl": {
                            "type": "boolean",
                            "description": "Czy używać SSL"
                        }
                    },
                    "required": ["smtp_server", "smtp_port", "imap_server", "imap_port", "email", "password"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "Wysyła email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Adres email odbiorcy"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Temat wiadomości"
                        },
                        "body": {
                            "type": "string",
                            "description": "Treść wiadomości"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_emails",
                "description": "Odczytuje wiadomości email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "description": "Folder do odczytania (domyślnie: INBOX)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maksymalna liczba wiadomości do odczytania (domyślnie: 10)"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "setup_mcp_integration",
                "description": "Konfiguruje integrację z protokołem MCP (Model Context Protocol)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {LLM_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message}
        ],
        "tools": functions,
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        
        # Sprawdź, czy model chce wywołać funkcję
        message_content = response_data["choices"][0]["message"]
        
        if "tool_calls" in message_content:
            # Model chce wywołać funkcję
            function_calls = message_content["tool_calls"]
            results = []
            
            for call in function_calls:
                function_name = call["function"]["name"]
                function_args = json.loads(call["function"]["arguments"])
                
                # Wywołaj odpowiednią funkcję
                result = handle_function_call(function_name, function_args)
                results.append(result)
            
            # Utwórz nowe zapytanie z wynikami funkcji
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": message},
                message_content,
            ]
            
            # Dodaj wyniki funkcji
            for i, result in enumerate(results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": function_calls[i]["id"],
                    "content": json.dumps(result)
                })
            
            # Wyślij drugie zapytanie z wynikami funkcji
            payload["messages"] = messages
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data["choices"][0]["message"]["content"]
            else:
                error_message = f"Błąd API OpenAI (kod {response.status_code}): {response.text}"
                logger.error(error_message)
                raise Exception(error_message)
        
        return response_data["choices"][0]["message"]["content"]
    else:
        error_message = f"Błąd API OpenAI (kod {response.status_code}): {response.text}"
        logger.error(error_message)
        raise Exception(error_message)

def handle_function_call(function_name, args):
    """Obsługuje wywołania funkcji z API OpenAI"""
    try:
        if email_utils is None:
            return {"success": False, "message": "Funkcje email nie są dostępne. Zainstaluj wymagane zależności."}
            
        if function_name == "setup_email_system":
            success, message = email_utils.setup_email_system()
            return {"success": success, "message": message}
        
        elif function_name == "configure_email":
            success, message = email_utils.configure_email(
                args.get("smtp_server"),
                args.get("smtp_port"),
                args.get("imap_server"),
                args.get("imap_port"),
                args.get("email"),
                args.get("password"),
                args.get("use_ssl", False)
            )
            return {"success": success, "message": message}
        
        elif function_name == "send_email":
            success, message = email_utils.send_email(
                args.get("to"),
                args.get("subject"),
                args.get("body")
            )
            return {"success": success, "message": message}
        
        elif function_name == "read_emails":
            success, result = email_utils.read_emails(
                args.get("folder", "INBOX"),
                args.get("limit", 10)
            )
            if success:
                return {"success": True, "emails": result}
            else:
                return {"success": False, "message": result}
        
        elif function_name == "setup_mcp_integration":
            success, message = email_utils.setup_mcp_integration()
            return {"success": success, "message": message}
        
        else:
            return {"success": False, "message": f"Nieznana funkcja: {function_name}"}
    
    except Exception as e:
        logger.error(f"Błąd podczas wykonywania funkcji {function_name}: {str(e)}")
        return {"success": False, "message": f"Błąd: {str(e)}"}

def call_anthropic_api(message):
    """Wywołuje API Anthropic i zwraca odpowiedź"""
    url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "x-api-key": LLM_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": message
            }
        ],
        "system": "Jesteś asystentem EvoDev, który pomaga użytkownikom w zadaniach programistycznych i administracyjnych."
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        return response_data["content"][0]["text"]
    else:
        error_message = f"Błąd API Anthropic (kod {response.status_code}): {response.text}"
        logger.error(error_message)
        raise Exception(error_message)

def call_ollama_api(message):
    """Wywołuje API Ollama i zwraca odpowiedź"""
    url = f"{LLM_URL}/api/generate"
    
    payload = {
        "model": LLM_MODEL or "llama2",
        "prompt": f"Jesteś asystentem EvoDev, który pomaga użytkownikom w zadaniach programistycznych i administracyjnych. Oto zapytanie użytkownika: {message}",
        "stream": False
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        response_data = response.json()
        return response_data["response"]
    else:
        error_message = f"Błąd API Ollama (kod {response.status_code}): {response.text}"
        logger.error(error_message)
        raise Exception(error_message)

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
