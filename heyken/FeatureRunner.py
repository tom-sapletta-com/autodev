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
import uuid
import yaml
from flask import Flask, request, jsonify
from typing import Dict, List, Any, Optional

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/data/feature_runner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("feature_runner")


class FeatureRunner:
    """
    Runner do testowania nowych funkcji w piaskownicy (sandbox)
    """

    def __init__(self):
        # Wczytanie konfiguracji
        self.active_core_id = int(os.environ.get("ACTIVE_CORE_ID", "1"))
        self.test_ollama_url = os.environ.get("TEST_OLLAMA_URL", "http://test_ollama:11434")
        self.sandbox_manager_url = os.environ.get("SANDBOX_MANAGER_URL", "http://sandbox_manager:5000")

        # Inicjalizacja klientów
        self.docker_client = docker.from_env()

        # Baza danych
        self.db_conn = None
        self.init_database()

        # Inicjalizacja kolejki testów
        self.test_queue = []
        self.test_thread = threading.Thread(target=self._process_test_queue, daemon=True)
        self.test_thread.start()

        logger.info("Feature Runner initialized")

    def init_database(self):
        """
        Inicjalizacja połączenia z bazą danych
        """
        try:
            # Połączenie z bazą danych
            self.db_conn = psycopg2.connect(
                os.environ.get("DATABASE_URL",
                               "dbname=systemdb user=postgres password=postgres host=system_db")
            )

            logger.info("Database connection established")

        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")

    def log_test_result(self, component_name: str, test_name: str, version: str,
                        status: str, duration: float, details: Dict = None, logs: str = None):
        """
        Zapisanie wyników testu do bazy danych
        """
        try:
            if not self.db_conn:
                logger.warning("Database connection not available, skipping test result logging")
                return

            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO test_results
                        (component_name, test_name, version, status, duration, details, logs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (component_name, test_name, version, status, duration,
                     json.dumps(details or {}), logs)
                )

            self.db_conn.commit()
            logger.info(f"Logged test result for {component_name} - {test_name}: {status}")

        except Exception as e:
            logger.error(f"Error logging test result: {str(e)}")

    def add_feature_to_test(self, feature_config: Dict):
        """
        Dodanie nowej funkcji do kolejki testów
        """
        # Walidacja konfiguracji
        required_fields = ["name", "version", "component_type", "docker_compose"]

        for field in required_fields:
            if field not in feature_config:
                logger.error(f"Missing required field in feature config: {field}")
                return {
                    "success": False,
                    "error": f"Missing required field: {field}"
                }

        # Dodanie do kolejki testów
        self.test_queue.append(feature_config)
        logger.info(f"Added feature to test queue: {feature_config['name']} v{feature_config['version']}")

        return {
            "success": True,
            "message": f"Feature added to test queue: {feature_config['name']} v{feature_config['version']}"
        }

    def _process_test_queue(self):
        """
        Przetwarzanie kolejki testów
        """
        while True:
            if self.test_queue:
                feature_config = self.test_queue.pop(0)
                logger.info(f"Starting test for feature: {feature_config['name']} v{feature_config['version']}")

                try:
                    # Testowanie funkcji
                    self._test_feature(feature_config)

                except Exception as e:
                    logger.error(f"Error testing feature: {str(e)}")

                    # Zapisanie wyniku testu
                    self.log_test_result(
                        feature_config["name"],
                        "setup",
                        feature_config["version"],
                        "error",
                        0.0,
                        {"error": str(e)},
                        f"Exception: {str(e)}"
                    )

            # Pauza przed sprawdzeniem kolejki
            time.sleep(5)

    def _test_feature(self, feature_config: Dict):
        """
        Testowanie funkcji w piaskownicy
        """
        start_time = time.time()
        test_dir = f"/data/tests/{feature_config['name']}_{feature_config['version']}_{int(start_time)}"

        try:
            # Utworzenie katalogu testowego
            os.makedirs(test_dir, exist_ok=True)

            # Zapisanie konfiguracji Docker Compose
            docker_compose_file = os.path.join(test_dir, "docker-compose.yml")
            with open(docker_compose_file, "w") as f:
                yaml.dump(feature_config["docker_compose"], f)

            # Utworzenie pliku testowego dla Ollama
            test_file = os.path.join(test_dir, "test_spec.json")
            with open(test_file, "w") as f:
                json.dump({
                    "name": feature_config["name"],
                    "version": feature_config["version"],
                    "component_type": feature_config["component_type"],
                    "tests": feature_config.get("tests", [])
                }, f, indent=2)

            # Uruchomienie testów
            logger.info(f"Starting Docker Compose for feature: {feature_config['name']}")

            # Uruchomienie usług
            result = subprocess.run(
                f"cd {test_dir} && docker-compose up -d",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Error starting Docker Compose: {result.stderr}")
                self.log_test_result(
                    feature_config["name"],
                    "docker_compose_up",
                    feature_config["version"],
                    "error",
                    time.time() - start_time,
                    {"error": result.stderr},
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                )
                return False

            # Danie czasu na uruchomienie usług
            time.sleep(10)

            # Wykonanie testów z wykorzystaniem Ollama
            logger.info(f"Running tests with Ollama for feature: {feature_config['name']}")
            test_results = self._run_ollama_tests(feature_config, test_file)

            # Zapisanie wyników testów
            for test_name, test_result in test_results.items():
                self.log_test_result(
                    feature_config["name"],
                    test_name,
                    feature_config["version"],
                    test_result["status"],
                    test_result["duration"],
                    test_result.get("details"),
                    test_result.get("logs")
                )

            # Zatrzymanie usług
            logger.info(f"Stopping Docker Compose for feature: {feature_config['name']}")
            subprocess.run(
                f"cd {test_dir} && docker-compose down",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Sprawdzenie wyniku ogólnego
            overall_status = "success"
            for test_result in test_results.values():
                if test_result["status"] != "success":
                    overall_status = "failure"
                    break

            # Zapisanie ogólnego wyniku testu
            total_duration = time.time() - start_time
            self.log_test_result(
                feature_config["name"],
                "overall",
                feature_config["version"],
                overall_status,
                total_duration,
                {"test_results": test_results},
                f"Overall test duration: {total_duration:.2f}s"
            )

            # Przekazanie wyników do aktywnego rdzenia, jeśli testy były udane
            if overall_status == "success":
                self._notify_active_core(feature_config, test_results)

            return overall_status == "success"

        except Exception as e:
            logger.error(f"Error in test process: {str(e)}")
            self.log_test_result(
                feature_config["name"],
                "process",
                feature_config["version"],
                "error",
                time.time() - start_time,
                {"error": str(e)},
                f"Exception: {str(e)}"
            )
            return False

    def _run_ollama_tests(self, feature_config: Dict, test_file: str) -> Dict[str, Dict]:
        """
        Uruchomienie testów z wykorzystaniem Ollama
        """
        test_results = {}

        try:
            # Wczytanie specyfikacji testów
            with open(test_file, "r") as f:
                test_spec = json.load(f)

            # Jeśli brak zdefiniowanych testów, utworzymy podstawowy test
            if not test_spec.get("tests"):
                test_spec["tests"] = [{
                    "name": "basic_functionality",
                    "description": "Test podstawowej funkcjonalności",
                    "prompt": f"Przetestuj podstawową funkcjonalność komponentu {feature_config['name']} w wersji {feature_config['version']}. Sprawdź, czy działa prawidłowo i czy nie generuje błędów."
                }]

            # Uruchomienie każdego testu
            for test in test_spec["tests"]:
                test_name = test["name"]
                prompt = test["prompt"]

                logger.info(f"Running test: {test_name}")
                start_time = time.time()

                # Wywołanie Ollama do wykonania testu
                response = requests.post(
                    f"{self.test_ollama_url}/api/generate",
                    json={
                        "model": "llama3:7b",
                        "prompt": f"""
                        Testowanie komponentu systemu autonomicznego.

                        Komponent: {feature_config['name']}
                        Wersja: {feature_config['version']}
                        Typ: {feature_config['component_type']}

                        Test do wykonania: {test_name}

                        Instrukcja: {prompt}

                        Przetestuj ten komponent i określ, czy wszystko działa prawidłowo.
                        Odpowiedź musi zawierać:
                        1. Status testu: "success" lub "failure"
                        2. Szczegółowy opis wyników testu
                        3. Ewentualne problemy i błędy
                        4. Rekomendacje
                        """,
                        "stream": False
                    }
                )

                duration = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    output = result.get("response", "")

                    # Analiza wyniku
                    status = "success" if "success" in output.lower() and "failure" not in output.lower() else "failure"

                    test_results[test_name] = {
                        "status": status,
                        "duration": duration,
                        "details": {
                            "output": output
                        },
                        "logs": output
                    }
                else:
                    test_results[test_name] = {
                        "status": "error",
                        "duration": duration,
                        "details": {
                            "error": f"Ollama API error: {response.status_code} - {response.text}"
                        },
                        "logs": f"Ollama API error: {response.status_code} - {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error in Ollama tests: {str(e)}")
            test_results["ollama_test_error"] = {
                "status": "error",
                "duration": 0.0,
                "details": {"error": str(e)},
                "logs": f"Exception: {str(e)}"
            }

        return test_results

    def _notify_active_core(self, feature_config: Dict, test_results: Dict[str, Dict]):
        """
        Powiadomienie aktywnego rdzenia o pomyślnie przetestowanej funkcji
        """
        try:
            core_api_url = f"http://middleware_core{self.active_core_id}:5000/feature/deploy"

            response = requests.post(
                core_api_url,
                json={
                    "feature": feature_config,
                    "test_results": test_results
                }
            )

            if response.status_code == 200:
                logger.info(f"Active core notified about successful tests: {feature_config['name']}")
                return True
            else:
                logger.error(f"Error notifying active core: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception when notifying active core: {str(e)}")
            return False

    def generate_feature_with_external_api(self, task_description: str, feature_name: str):
        """
        Generowanie nowej funkcji z wykorzystaniem zewnętrznego API (np. Gemini, Claude)
        """
        # Tutaj można zaimplementować integrację z zewnętrznym API LLM
        # Dla przykładu, zakładamy że funkcja zwraca już utworzoną konfigurację

        # W rzeczywistej implementacji, tutaj byłoby wywołanie API Gemini lub Claude
        feature_config = self._mock_external_api_response(task_description, feature_name)

        # Dodanie do kolejki testów
        return self.add_feature_to_test(feature_config)

    def _mock_external_api_response(self, task_description: str, feature_name: str) -> Dict:
        """
        Funkcja mock do testów - w rzeczywistości byłoby tutaj wywołanie zewnętrznego API
        """
        version = "0.1.0"

        # Przykładowa konfiguracja Docker Compose
        docker_compose = {
            "version": "3.8",
            "services": {
                feature_name: {
                    "image": "python:3.9-slim",
                    "volumes": [
                        "./:/app"
                    ],
                    "command": "python /app/main.py",
                    "environment": [
                        "TASK_DESCRIPTION=" + task_description
                    ]
                }
            }
        }

        return {
            "name": feature_name,
            "version": version,
            "component_type": "service",
            "task_description": task_description,
            "docker_compose": docker_compose,
            "tests": [
                {
                    "name": "basic_functionality",
                    "description": "Test podstawowej funkcjonalności",
                    "prompt": f"Przetestuj podstawową funkcjonalność komponentu {feature_name}. Sprawdź, czy prawidłowo realizuje zadanie: {task_description}"
                }
            ]
        }


# Inicjalizacja API
app = Flask(__name__)
feature_runner = FeatureRunner()


@app.route('/test', methods=['POST'])
def add_feature_test():
    """Endpoint do dodawania nowych funkcji do testów"""
    data = request.json

    if not data.get('feature_config'):
        return jsonify({
            "success": False,
            "error": "Missing feature_config in request"
        }), 400

    result = feature_runner.add_feature_to_test(data['feature_config'])
    return jsonify(result)


@app.route('/generate', methods=['POST'])
def generate_feature():
    """Endpoint do generowania nowych funkcji z wykorzystaniem zewnętrznego API"""
    data = request.json

    task_description = data.get('task_description')
    feature_name = data.get('feature_name')

    if not task_description or not feature_name:
        return jsonify({
            "success": False,
            "error": "Missing required parameters: task_description, feature_name"
        }), 400

    result = feature_runner.generate_feature_with_external_api(task_description, feature_name)
    return jsonify(result)


@app.route('/results', methods=['GET'])
def get_test_results():
    """Endpoint do pobierania wyników testów"""
    try:
        feature_name = request.args.get('feature_name')
        limit = int(request.args.get('limit', 10))

        query = """
                SELECT component_name, \
                       test_name, \
                       version, \
                       status, \
                       duration, \
                       details, \
                       logs, \
                       timestamp
                FROM test_results
                WHERE 1 = 1 \
                """

        params = []

        if feature_name:
            query += " AND component_name = %s"
            params.append(feature_name)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        with feature_runner.db_conn.cursor() as cur:
            cur.execute(query, params)

            results = []
            for row in cur.fetchall():
                results.append({
                    "component_name": row[0],
                    "test_name": row[1],
                    "version": row[2],
                    "status": row[3],
                    "duration": row[4],
                    "details": row[5],
                    "logs": row[6],
                    "timestamp": str(row[7])
                })

        return jsonify({
            "success": True,
            "results": results
        })

    except Exception as e:
        logger.error(f"Error getting test results: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# Uruchomienie aplikacji
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)