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
from flask import Flask, render_template, jsonify, request, g
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
DB_PATH = os.environ.get('MONITOR_DB', 'monitor.db')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('MONITOR_LOG_FILE', 'monitor.log')
APP_LOG_FILE = os.environ.get('APP_LOG_FILE', 'monitor.log')
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

@app.route('/api/docker/requests/recent', methods=['GET'])
def api_docker_recent_requests():
    """Zwraca ostatnie requesty Docker"""
    if not has_docker_monitor:
        return jsonify({"success": False, "message": "Docker request monitoring not available"}), 404
    
    limit = request.args.get('limit', 100, type=int)
    requests = docker_monitor.get_recent_requests(limit)
    return jsonify({"success": True, "requests": requests})

@app.route('/api/docker/requests/stats', methods=['GET'])
def api_docker_request_stats():
    """Zwraca statystyki requestów Docker"""
    if not has_docker_monitor:
        return jsonify({"success": False, "message": "Docker request monitoring not available"}), 404
    
    stats = docker_monitor.get_request_stats()
    return jsonify({"success": True, "stats": stats})

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
