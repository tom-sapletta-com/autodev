#!/usr/bin/env python3
import os
import json
import time
import sqlite3
import logging
import threading
import subprocess
import docker
from datetime import datetime
import re

logger = logging.getLogger('evodev-monitor')

# Database configuration
DB_PATH = os.environ.get('MONITOR_DB', 'monitor.db')

def init_db():
    """Initialize the database for Docker request monitoring"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create table for Docker requests
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS docker_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        source_container TEXT,
        destination_container TEXT,
        request_type TEXT,
        request_path TEXT,
        status_code INTEGER,
        response_time REAL,
        request_size INTEGER,
        response_size INTEGER
    )
    ''')
    
    conn.commit()
    conn.close()

def start_request_monitoring():
    """Start monitoring Docker container network requests"""
    try:
        # Initialize the database
        init_db()
        
        # Start tcpdump in a separate thread to capture network traffic
        thread = threading.Thread(target=_monitor_network_traffic)
        thread.daemon = True
        thread.start()
        
        logger.info("Docker request monitoring started")
        return True
    except Exception as e:
        logger.error(f"Failed to start Docker request monitoring: {str(e)}")
        return False

def _monitor_network_traffic():
    """Monitor network traffic between Docker containers using tcpdump"""
    try:
        client = docker.from_env()
        network = client.networks.list(names=['evodev_default'])[0]
        
        # Get container IPs
        container_ips = {}
        for container in client.containers.list():
            try:
                container_info = client.api.inspect_container(container.id)
                if 'evodev_default' in container_info['NetworkSettings']['Networks']:
                    ip = container_info['NetworkSettings']['Networks']['evodev_default']['IPAddress']
                    container_ips[ip] = container.name
            except Exception as e:
                logger.error(f"Error getting container IP: {str(e)}")
        
        # Start tcpdump to capture HTTP traffic
        cmd = [
            "tcpdump", 
            "-i", "docker0", 
            "-nn", 
            "-A",
            "tcp port 80 or tcp port 8080 or tcp port 3000 or tcp port 443",
            "-l"
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Process tcpdump output
        current_request = {}
        for line in process.stdout:
            try:
                # Parse tcpdump output to extract request information
                if "HTTP/" in line:
                    # Extract source and destination IPs
                    parts = line.split()
                    if len(parts) >= 5:
                        src_ip = parts[2].split('.')[0:4]
                        src_ip = '.'.join(src_ip)
                        dst_ip = parts[4].split('.')[0:4]
                        dst_ip = '.'.join(dst_ip)
                        
                        # Map IPs to container names
                        src_container = container_ips.get(src_ip, src_ip)
                        dst_container = container_ips.get(dst_ip, dst_ip)
                        
                        # Extract request type and path
                        if "GET" in line:
                            req_type = "GET"
                            path = line.split("GET ")[1].split(" HTTP")[0]
                        elif "POST" in line:
                            req_type = "POST"
                            path = line.split("POST ")[1].split(" HTTP")[0]
                        elif "PUT" in line:
                            req_type = "PUT"
                            path = line.split("PUT ")[1].split(" HTTP")[0]
                        elif "DELETE" in line:
                            req_type = "DELETE"
                            path = line.split("DELETE ")[1].split(" HTTP")[0]
                        else:
                            # Response
                            if "HTTP/" in line and "200" in line:
                                status_code = 200
                            elif "HTTP/" in line and "404" in line:
                                status_code = 404
                            elif "HTTP/" in line and "500" in line:
                                status_code = 500
                            else:
                                status_code = 0
                            
                            if current_request:
                                current_request["status_code"] = status_code
                                current_request["timestamp"] = datetime.now().isoformat()
                                current_request["response_time"] = time.time() - current_request.get("start_time", time.time())
                                
                                # Save to database
                                save_request(current_request)
                                current_request = {}
                            continue
                        
                        # Create new request
                        current_request = {
                            "source_container": src_container,
                            "destination_container": dst_container,
                            "request_type": req_type,
                            "request_path": path,
                            "start_time": time.time(),
                            "request_size": len(line),
                            "response_size": 0
                        }
            except Exception as e:
                logger.error(f"Error processing network traffic: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in network traffic monitoring: {str(e)}")

def save_request(request_data):
    """Save request information to the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO docker_requests 
        (timestamp, source_container, destination_container, request_type, 
        request_path, status_code, response_time, request_size, response_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_data.get("timestamp"),
            request_data.get("source_container"),
            request_data.get("destination_container"),
            request_data.get("request_type"),
            request_data.get("request_path"),
            request_data.get("status_code", 0),
            request_data.get("response_time", 0),
            request_data.get("request_size", 0),
            request_data.get("response_size", 0)
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error saving request to database: {str(e)}")

def get_recent_requests(limit=100):
    """Get recent Docker container requests"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM docker_requests
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        requests = [dict(row) for row in rows]
        
        conn.close()
        return requests
    except Exception as e:
        logger.error(f"Error getting recent requests: {str(e)}")
        return []

def get_request_stats():
    """Get statistics about Docker container requests"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get container interaction counts
        cursor.execute('''
        SELECT 
            source_container, 
            destination_container, 
            COUNT(*) as request_count,
            AVG(response_time) as avg_response_time
        FROM docker_requests
        GROUP BY source_container, destination_container
        ORDER BY request_count DESC
        ''')
        
        interactions = [dict(row) for row in cursor.fetchall()]
        
        # Get request types distribution
        cursor.execute('''
        SELECT 
            request_type, 
            COUNT(*) as count
        FROM docker_requests
        GROUP BY request_type
        ''')
        
        request_types = [dict(row) for row in cursor.fetchall()]
        
        # Get status code distribution
        cursor.execute('''
        SELECT 
            status_code, 
            COUNT(*) as count
        FROM docker_requests
        GROUP BY status_code
        ''')
        
        status_codes = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "interactions": interactions,
            "request_types": request_types,
            "status_codes": status_codes
        }
    except Exception as e:
        logger.error(f"Error getting request stats: {str(e)}")
        return {
            "interactions": [],
            "request_types": [],
            "status_codes": []
        }

def get_container_web_interfaces():
    """Get information about web interfaces for Docker containers"""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)  # Pobierz wszystkie kontenery, nie tylko uruchomione
        
        web_interfaces = []
        
        for container in containers:
            try:
                container_info = client.api.inspect_container(container.id)
                
                # Sprawdź, czy kontener należy do projektu EvoDev
                labels = container_info['Config']['Labels']
                is_evodev = False
                
                if labels and ('com.docker.compose.project' in labels):
                    project = labels['com.docker.compose.project']
                    if project.lower() == 'evodev':
                        is_evodev = True
                
                # Jeśli nie jest częścią projektu EvoDev, pomijamy
                if not is_evodev:
                    continue
                
                # Pobierz informacje o portach
                ports = container_info['NetworkSettings']['Ports']
                
                # Sprawdź, czy kontener ma otwarte porty webowe
                web_ports = []
                if ports:
                    for port, bindings in ports.items():
                        if bindings:
                            port_number = port.split('/')[0]
                            # Sprawdź, czy to potencjalnie port webowy (80, 8080, 3000, 443, etc.)
                            if port_number in ['80', '8080', '3000', '443', '4000', '5000', '8000', '8888', '9000']:
                                host_port = bindings[0]['HostPort']
                                protocol = 'https' if port_number == '443' else 'http'
                                web_ports.append({
                                    'container_port': port_number,
                                    'host_port': host_port,
                                    'url': f"{protocol}://localhost:{host_port}"
                                })
                
                # Sprawdź, czy kontener ma etykietę wskazującą na interfejs webowy
                is_web_app = False
                app_type = None
                
                if labels:
                    if 'com.docker.compose.service' in labels:
                        service_name = labels['com.docker.compose.service']
                        if any(web_app in service_name.lower() for web_app in ['web', 'ui', 'app', 'frontend', 'dashboard', 'chat', 'rocket']):
                            is_web_app = True
                            app_type = service_name
                
                # Sprawdź nazwę kontenera, czy wskazuje na aplikację webową
                container_name = container.name.lower()
                if any(web_app in container_name for web_app in ['web', 'ui', 'app', 'frontend', 'dashboard', 'chat', 'rocket']):
                    is_web_app = True
                    app_type = app_type or re.sub(r'[^a-zA-Z0-9]', '', container_name)
                
                # Dodaj wszystkie kontenery EvoDev, niezależnie od tego, czy mają interfejs webowy
                web_interfaces.append({
                    'id': container.id,
                    'name': container.name,
                    'status': container.status,
                    'web_ports': web_ports,
                    'is_web_app': is_web_app or len(web_ports) > 0,
                    'app_type': app_type or (labels.get('com.docker.compose.service') if labels else None),
                    'image': container.image.tags[0] if container.image.tags else str(container.image.id),
                    'restart_count': container_info['RestartCount'] if 'RestartCount' in container_info else 0,
                    'created': container_info['Created'],
                    'started_at': container_info['State'].get('StartedAt', ''),
                    'is_evodev': True
                })
            
            except Exception as e:
                logger.error(f"Error getting web interface info for container {container.name}: {str(e)}")
        
        return web_interfaces
    
    except Exception as e:
        logger.error(f"Error getting container web interfaces: {str(e)}")
        return []

def get_container_logs(container_id, lines=100):
    """Get logs for a specific Docker container"""
    try:
        client = docker.from_env()
        container = client.containers.get(container_id)
        
        # Pobierz informacje o kontenerze
        container_info = client.api.inspect_container(container_id)
        container_state = container_info['State']
        
        # Sprawdź status kontenera
        status = container_state.get('Status', 'unknown')
        restarting = container_state.get('Restarting', False)
        exit_code = container_state.get('ExitCode', 0)
        
        # Dodaj informacje o statusie do logów
        status_info = f"Status: {status}\n"
        if restarting:
            status_info += "Kontener jest w trakcie restartu.\n"
        if exit_code != 0:
            status_info += f"Ostatni kod wyjścia: {exit_code}\n"
        
        # Pobierz logi
        try:
            logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
            
            # Jeśli nie ma logów, dodaj informację
            if not logs.strip():
                logs = "Brak dostępnych logów dla tego kontenera."
            
            return status_info + logs
        except Exception as log_error:
            logger.error(f"Error getting container logs content: {str(log_error)}")
            return status_info + f"Błąd podczas pobierania treści logów: {str(log_error)}"
            
    except docker.errors.NotFound:
        return "Kontener nie został znaleziony. Mógł zostać usunięty."
    except Exception as e:
        logger.error(f"Error getting container logs: {str(e)}")
        return f"Błąd podczas pobierania logów: {str(e)}"

def container_action(container_id, action):
    """Perform action on a Docker container (start, stop, restart)"""
    try:
        client = docker.from_env()
        
        try:
            container = client.containers.get(container_id)
        except docker.errors.NotFound:
            return {"success": False, "message": "Kontener nie został znaleziony"}
        
        # Wykonaj akcję na kontenerze
        if action == 'start':
            if container.status == 'running':
                return {"success": True, "message": "Kontener jest już uruchomiony"}
            container.start()
            return {"success": True, "message": f"Kontener {container.name} został uruchomiony"}
        
        elif action == 'stop':
            if container.status != 'running':
                return {"success": True, "message": "Kontener jest już zatrzymany"}
            container.stop()
            return {"success": True, "message": f"Kontener {container.name} został zatrzymany"}
        
        elif action == 'restart':
            container.restart()
            return {"success": True, "message": f"Kontener {container.name} został zrestartowany"}
        
        else:
            return {"success": False, "message": f"Nieznana akcja: {action}"}
    
    except Exception as e:
        logger.error(f"Error performing container action: {str(e)}")
        return {"success": False, "message": f"Błąd podczas wykonywania akcji: {str(e)}"}

# Start monitoring when module is imported
if __name__ != "__main__":
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error initializing Docker monitor database: {str(e)}")
