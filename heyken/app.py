import os
import sys
import json
import time
import logging
import threading
import requests
import docker
import psycopg2
import subprocess
from flask import Flask, request, jsonify
from typing import Dict, List, Any, Optional

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/logs/core_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("core_manager")


class CoreManager:
    """
    Menedżer rdzenia systemu autonomicznego
    """

    def __init__(self):
        # Wczytanie konfiguracji
        self.core_id = int(os.environ.get("CORE_ID", "1"))
        self.is_active = os.environ.get("IS_ACTIVE", "false").lower() == "true"
        self.gitlab_url = os.environ.get("GITLAB_URL", "http://gitlab")
        self.ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")

        # Inicjalizacja klientów
        self.docker_client = docker.from_env()

        # Status systemu
        self.system_status = {
            "core_id": self.core_id,
            "is_active": self.is_active,
            "services": {},
            "last_health_check": 0,
            "status": "initializing"
        }

        # Baza danych
        self.db_conn = None
        self.init_database()

        # Uruchomienie monitorowania
        if self.is_active:
            self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
            self.monitor_thread.start()

        logger.info(f"Core Manager {self.core_id} initialized. Active: {self.is_active}")

    def init_database(self):
        """
        Inicjalizacja połączenia z bazą danych
        """
        try:
            # Połączenie z bazą danych
            self.db_conn = psycopg2.connect(
                "dbname=systemdb user=postgres password=postgres host=system_db"
            )

            # Utworzenie podstawowych tabel, jeśli nie istnieją
            with self.db_conn.cursor() as cur:
                # Tabela dla logów aktywności
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS activity_logs
                            (
                                id        SERIAL PRIMARY KEY,
                                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                core_id   INTEGER      NOT NULL,
                                log_type  VARCHAR(50)  NOT NULL,
                                action    VARCHAR(255) NOT NULL,
                                details JSONB,
                                status    VARCHAR(50)  NOT NULL
                            )
                            """)

                # Tabela dla historii poleceń
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS command_history
                            (
                                id            SERIAL PRIMARY KEY,
                                timestamp     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                core_id       INTEGER     NOT NULL,
                                command_type  VARCHAR(50) NOT NULL,
                                command       TEXT        NOT NULL,
                                params JSONB,
                                result_status VARCHAR(50),
                                result_data JSONB
                            )
                            """)

                # Tabela dla wersji komponentów
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS component_versions
                            (
                                id             SERIAL PRIMARY KEY,
                                component_name VARCHAR(255) NOT NULL,
                                version        VARCHAR(50)  NOT NULL,
                                git_commit     VARCHAR(255),
                                timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                status         VARCHAR(50)  NOT NULL,
                                core_id        INTEGER      NOT NULL,
                                metadata JSONB
                            )
                            """)

                # Tabela dla wyników testów
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS test_results
                            (
                                id             SERIAL PRIMARY KEY,
                                timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                component_name VARCHAR(255) NOT NULL,
                                test_name      VARCHAR(255) NOT NULL,
                                version        VARCHAR(50)  NOT NULL,
                                status         VARCHAR(50)  NOT NULL,
                                duration       FLOAT,
                                details JSONB,
                                logs           TEXT
                            )
                            """)

            self.db_conn.commit()
            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            # Bez bazy danych system może działać, ale w ograniczonym zakresie

    def log_activity(self, log_type: str, action: str, details: Dict = None, status: str = "success"):
        """
        Zapisanie informacji o aktywności do bazy danych
        """
        try:
            if not self.db_conn:
                logger.warning("Database connection not available, skipping activity logging")
                return

            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO activity_logs (core_id, log_type, action, details, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (self.core_id, log_type, action, json.dumps(details or {}), status)
                )

            self.db_conn.commit()

        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")

    def log_command(self, command_type: str, command: str, params: Dict = None):
        """
        Zapisanie informacji o wykonanym poleceniu
        """
        try:
            if not self.db_conn:
                logger.warning("Database connection not available, skipping command logging")
                return None

            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO command_history (core_id, command_type, command, params)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (self.core_id, command_type, command, json.dumps(params or {}))
                )

                command_id = cur.fetchone()[0]

            self.db_conn.commit()
            return command_id

        except Exception as e:
            logger.error(f"Error logging command: {str(e)}")
            return None

    def update_command_result(self, command_id: int, status: str, data: Dict = None):
        """
        Aktualizacja wyniku wykonania polecenia
        """
        try:
            if not self.db_conn:
                logger.warning("Database connection not available, skipping command result update")
                return

            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE command_history
                    SET result_status = %s,
                        result_data   = %s
                    WHERE id = %s
                    """,
                    (status, json.dumps(data or {}), command_id)
                )

            self.db_conn.commit()

        except Exception as e:
            logger.error(f"Error updating command result: {str(e)}")

    def register_component_version(self, component_name: str, version: str,
                                   git_commit: str = None, status: str = "active",
                                   metadata: Dict = None):
        """
        Rejestracja nowej wersji komponentu
        """
        try:
            if not self.db_conn:
                logger.warning("Database connection not available, skipping component registration")
                return

            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO component_versions
                        (component_name, version, git_commit, status, core_id, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (component_name, version, git_commit, status, self.core_id,
                     json.dumps(metadata or {}))
                )

            self.db_conn.commit()
            logger.info(f"Registered component {component_name} version {version}")

        except Exception as e:
            logger.error(f"Error registering component version: {str(e)}")

    def _monitor_system(self):
        """
        Ciągłe monitorowanie stanu systemu
        """
        while True:
            try:
                # Sprawdzenie stanu kontenerów
                containers = self.docker_client.containers.list()
                core_containers = [c for c in containers if f"core{self.core_id}" in c.name]

                service_status = {}
                for container in core_containers:
                    service_status[container.name] = {
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown"
                    }

                # Aktualizacja statusu
                self.system_status["services"] = service_status
                self.system_status["last_health_check"] = time.time()
                self.system_status["status"] = "running"

                # Zapisanie statusu do pliku współdzielonego
                self._save_status_to_shared()

                # Sprawdzenie, czy rdzeń powinien być aktywny
                self._check_active_status()

            except Exception as e:
                logger.error(f"Error in system monitoring: {str(e)}")
                self.system_status["status"] = "error"

            # Pauza przed kolejnym sprawdzeniem
            time.sleep(30)

    def _save_status_to_shared(self):
        """
        Zapisanie statusu do współdzielonego pliku
        """
        try:
            status_file = f"/shared/core{self.core_id}_status.json"

            with open(status_file, "w") as f:
                json.dump(self.system_status, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving status to shared file: {str(e)}")

    def _check_active_status(self):
        """
        Sprawdzenie, czy rdzeń powinien być aktywny
        """
        try:
            active_core_file = "/shared/active_core"

            if os.path.exists(active_core_file):
                with open(active_core_file, "r") as f:
                    active_core_data = f.read().strip()

                # Ekstrakcja numeru aktywnego rdzenia
                import re
                match = re.search(r'Active core: (\d+)', active_core_data)
                if match:
                    active_core = int(match.group(1))

                    # Porównanie z bieżącym ID
                    should_be_active = (active_core == self.core_id)

                    if should_be_active != self.is_active:
                        logger.info(f"Active status change: {self.is_active} -> {should_be_active}")

                        if should_be_active:
                            self._activate_core()
                        else:
                            self._deactivate_core()

        except Exception as e:
            logger.error(f"Error checking active status: {str(e)}")

    def _activate_core(self):
        """
        Aktywacja rdzenia
        """
        logger.info(f"Activating core {self.core_id}")

        try:
            # Uruchomienie wszystkich usług
            result = subprocess.run(
                f"docker-compose -f /app/docker-compose.core{self.core_id}.yml up -d",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.is_active = True
                self.system_status["is_active"] = True
                logger.info(f"Core {self.core_id} activated successfully")
                self.log_activity("core", "activate", status="success")
            else:
                logger.error(f"Error activating core: {result.stderr}")
                self.log_activity("core", "activate",
                                  {"error": result.stderr}, status="error")

        except Exception as e:
            logger.error(f"Exception during core activation: {str(e)}")
            self.log_activity("core", "activate",
                              {"error": str(e)}, status="error")

    def _deactivate_core(self):
        """
        Dezaktywacja rdzenia
        """
        logger.info(f"Deactivating core {self.core_id}")

        try:
            # Zatrzymanie wszystkich usług oprócz Core Manager
            result = subprocess.run(
                f"docker-compose -f /app/docker-compose.core{self.core_id}.yml stop",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.is_active = False
                self.system_status["is_active"] = False
                logger.info(f"Core {self.core_id} deactivated successfully")
                self.log_activity("core", "deactivate", status="success")
            else:
                logger.error(f"Error deactivating core: {result.stderr}")
                self.log_activity("core", "deactivate",
                                  {"error": result.stderr}, status="error")

        except Exception as e:
            logger.error(f"Exception during core deactivation: {str(e)}")
            self.log_activity("core", "deactivate",
                              {"error": str(e)}, status="error")

    def execute_command(self, command_type: str, command: str, params: Dict = None):
        """
        Wykonanie polecenia w rdzeniu
        """
        logger.info(f"Executing command: {command_type} - {command}")

        # Zapisanie polecenia w historii
        command_id = self.log_command(command_type, command, params)

        try:
            # Wykonanie polecenia w zależności od typu
            if command_type == "shell":
                return self._execute_shell_command(command_id, command, params)
            elif command_type == "docker":
                return self._execute_docker_command(command_id, command, params)
            elif command_type == "gitlab":
                return self._execute_gitlab_command(command_id, command, params)
            elif command_type == "ollama":
                return self._execute_ollama_command(command_id, command, params)
            else:
                logger.warning(f"Unknown command type: {command_type}")
                self.update_command_result(command_id, "error",
                                           {"error": f"Unknown command type: {command_type}"})
                return {"success": False, "error": f"Unknown command type: {command_type}"}

        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            self.update_command_result(command_id, "error", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _execute_shell_command(self, command_id: int, command: str, params: Dict = None):
        """
        Wykonanie polecenia powłoki
        """
        # Dodanie zabezpieczeń przed niebezpiecznymi poleceniami
        forbidden_commands = ["rm -rf", "mkfs", "dd", ":(){ :|:& };:"]

        for fc in forbidden_commands:
            if fc in command:
                self.update_command_result(command_id, "error",
                                           {"error": f"Forbidden command: {fc}"})
                return {"success": False, "error": f"Forbidden command: {fc}"}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )

            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }

            status = "success" if result.returncode == 0 else "error"
            self.update_command_result(command_id, status, output)

            return {
                "success": result.returncode == 0,
                "output": output
            }

        except Exception as e:
            self.update_command_result(command_id, "error", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _execute_docker_command(self, command_id: int, command: str, params: Dict = None):
        """
        Wykonanie polecenia Docker
        """
        try:
            if command == "ps":
                containers = self.docker_client.containers.list()
                container_info = [{
                    "name": c.name,
                    "image": c.image.tags[0] if c.image.tags else "unknown",
                    "status": c.status,
                    "id": c.short_id
                } for c in containers]

                self.update_command_result(command_id, "success", {"containers": container_info})
                return {"success": True, "containers": container_info}

            elif command == "start":
                container_name = params.get("container")
                if not container_name:
                    self.update_command_result(command_id, "error",
                                               {"error": "Container name not provided"})
                    return {"success": False, "error": "Container name not provided"}

                container = self.docker_client.containers.get(container_name)
                container.start()

                self.update_command_result(command_id, "success",
                                           {"message": f"Container {container_name} started"})
                return {"success": True, "message": f"Container {container_name} started"}

            elif command == "stop":
                container_name = params.get("container")
                if not container_name:
                    self.update_command_result(command_id, "error",
                                               {"error": "Container name not provided"})
                    return {"success": False, "error": "Container name not provided"}

                container = self.docker_client.containers.get(container_name)
                container.stop()

                self.update_command_result(command_id, "success",
                                           {"message": f"Container {container_name} stopped"})
                return {"success": True, "message": f"Container {container_name} stopped"}

            elif command == "logs":
                container_name = params.get("container")
                if not container_name:
                    self.update_command_result(command_id, "error",
                                               {"error": "Container name not provided"})
                    return {"success": False, "error": "Container name not provided"}

                container = self.docker_client.containers.get(container_name)
                logs = container.logs(tail=100).decode("utf-8")

                self.update_command_result(command_id, "success", {"logs": logs})
                return {"success": True, "logs": logs}

            else:
                self.update_command_result(command_id, "error",
                                           {"error": f"Unknown Docker command: {command}"})
                return {"success": False, "error": f"Unknown Docker command: {command}"}

        except Exception as e:
            self.update_command_result(command_id, "error", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _execute_gitlab_command(self, command_id: int, command: str, params: Dict = None):
        """
        Wykonanie polecenia GitLab
        """
        try:
            # Token GitLab powinien być przechowywany w bezpieczny sposób
            gitlab_token = os.environ.get("GITLAB_API_TOKEN", "")
            headers = {"Private-Token": gitlab_token}

            if command == "create_project":
                project_name = params.get("name")
                if not project_name:
                    self.update_command_result(command_id, "error",
                                               {"error": "Project name not provided"})
                    return {"success": False, "error": "Project name not provided"}

                response = requests.post(
                    f"{self.gitlab_url}/api/v4/projects",
                    headers=headers,
                    json={
                        "name": project_name,
                        "description": params.get("description", ""),
                        "visibility": params.get("visibility", "private")
                    }
                )

                if response.status_code == 201:
                    project_data = response.json()
                    self.update_command_result(command_id, "success", project_data)
                    return {"success": True, "project": project_data}
                else:
                    error = f"GitLab API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            elif command == "create_file":
                project_id = params.get("project_id")
                file_path = params.get("file_path")
                content = params.get("content")

                if not project_id or not file_path or not content:
                    error = "Missing required parameters: project_id, file_path, content"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

                response = requests.post(
                    f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/files/{file_path}",
                    headers=headers,
                    json={
                        "branch": params.get("branch", "master"),
                        "content": content,
                        "commit_message": params.get("commit_message", "Add new file")
                    }
                )

                if response.status_code in [201, 200]:
                    self.update_command_result(command_id, "success", response.json())
                    return {"success": True, "result": response.json()}
                else:
                    error = f"GitLab API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            elif command == "get_pipeline":
                project_id = params.get("project_id")
                pipeline_id = params.get("pipeline_id")

                if not project_id or not pipeline_id:
                    error = "Missing required parameters: project_id, pipeline_id"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

                response = requests.get(
                    f"{self.gitlab_url}/api/v4/projects/{project_id}/pipelines/{pipeline_id}",
                    headers=headers
                )

                if response.status_code == 200:
                    self.update_command_result(command_id, "success", response.json())
                    return {"success": True, "pipeline": response.json()}
                else:
                    error = f"GitLab API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            else:
                self.update_command_result(command_id, "error",
                                           {"error": f"Unknown GitLab command: {command}"})
                return {"success": False, "error": f"Unknown GitLab command: {command}"}

        except Exception as e:
            self.update_command_result(command_id, "error", {"error": str(e)})
            return {"success": False, "error": str(e)}

    def _execute_ollama_command(self, command_id: int, command: str, params: Dict = None):
        """
        Wykonanie polecenia Ollama
        """
        try:
            if command == "generate":
                prompt = params.get("prompt")
                model = params.get("model", "llama3:7b")

                if not prompt:
                    self.update_command_result(command_id, "error",
                                               {"error": "Prompt not provided"})
                    return {"success": False, "error": "Prompt not provided"}

                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    self.update_command_result(command_id, "success", result)
                    return {"success": True, "result": result}
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            elif command == "list_models":
                response = requests.get(f"{self.ollama_url}/api/tags")

                if response.status_code == 200:
                    models = response.json().get("models", [])
                    self.update_command_result(command_id, "success", {"models": models})
                    return {"success": True, "models": models}
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            elif command == "pull_model":
                model = params.get("model")

                if not model:
                    self.update_command_result(command_id, "error",
                                               {"error": "Model name not provided"})
                    return {"success": False, "error": "Model name not provided"}

                response = requests.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model}
                )

                if response.status_code == 200:
                    self.update_command_result(command_id, "success",
                                               {"message": f"Model {model} pulled successfully"})
                    return {"success": True, "message": f"Model {model} pulled successfully"}
                else:
                    error = f"Ollama API error: {response.status_code} - {response.text}"
                    self.update_command_result(command_id, "error", {"error": error})
                    return {"success": False, "error": error}

            else:
                self.update_command_result(command_id, "error",
                                           {"error": f"Unknown Ollama command: {command}"})
                return {"success": False, "error": f"Unknown Ollama command: {command}"}

        except Exception as e:
            self.update_command_result(command_id, "error", {"error": str(e)})
            return {"success": False, "error": str(e)}


# Inicjalizacja API
app = Flask(__name__)
core_manager = CoreManager()


@app.route('/status', methods=['GET'])
def get_status():
    """Endpoint do pobierania statusu rdzenia"""
    return jsonify(core_manager.system_status)


@app.route('/execute', methods=['POST'])
def execute_command():
    """Endpoint do wykonywania poleceń"""
    data = request.json

    command_type = data.get('command_type')
    command = data.get('command')
    params = data.get('params')

    if not command_type or not command:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: command_type, command"
        }), 400

    result = core_manager.execute_command(command_type, command, params)
    return jsonify(result)


@app.route('/components', methods=['GET'])
def list_components():
    """Endpoint do listowania zarejestrowanych komponentów"""
    try:
        with core_manager.db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT component_name, version, timestamp, status
                FROM component_versions
                WHERE core_id = %s
                ORDER BY timestamp DESC
                """,
                (core_manager.core_id,)
            )

            components = []
            for row in cur.fetchall():
                components.append({
                    "name": row[0],
                    "version": row[1],
                    "timestamp": str(row[2]),
                    "status": row[3]
                })

        return jsonify({
            "success": True,
            "components": components
        })

    except Exception as e:
        logger.error(f"Error listing components: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/logs', methods=['GET'])
def get_logs():
    """Endpoint do pobierania logów aktywności"""
    try:
        limit = request.args.get('limit', 100)

        with core_manager.db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT timestamp, log_type, action, details, status
                FROM activity_logs
                WHERE core_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (core_manager.core_id, limit)
            )

            logs = []
            for row in cur.fetchall():
                logs.append({
                    "timestamp": str(row[0]),
                    "type": row[1],
                    "action": row[2],
                    "details": row[3],
                    "status": row[4]
                })

        return jsonify({
            "success": True,
            "logs": logs
        })

    except Exception as e:
        logger.error(f"Error getting logs: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Uruchomienie aplikacji
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)