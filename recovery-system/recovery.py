# recovery.py

import logging
import os
import time
import subprocess
import requests
import yaml
import docker
import threading
import datetime
import json
from typing import Dict, List, Any

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("/var/log/recovery-system.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RecoverySystem:
    """System przywracania dla infrastruktury autonomicznej"""

    def __init__(self):
        self.gitlab_url = os.environ.get("GITLAB_URL", "http://gitlab:80")
        self.gitlab_token = os.environ.get("GITLAB_API_TOKEN", "")
        self.backup_dir = os.environ.get("BACKUP_DIR", "/backups")
        self.backup_interval = int(os.environ.get("BACKUP_INTERVAL", "3600"))
        self.docker_client = docker.from_env()

        # Utworzenie katalogu kopii zapasowych
        os.makedirs(self.backup_dir, exist_ok=True)

        # Uruchomienie monitoringu systemu
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()

    def _monitor_system(self):
        """Ciągłe monitorowanie stanu systemu"""
        while True:
            try:
                # Sprawdzenie stanu usług
                services_status = self._check_services_status()

                # Archiwizacja stanu
                self._archive_system_state(services_status)

                # Weryfikacja integralności systemu
                if not self._verify_system_integrity(services_status):
                    logger.warning("Wykryto problemy z integralnością systemu!")
                    self._handle_integrity_issues(services_status)

            except Exception as e:
                logger.error(f"Błąd w monitorowaniu systemu: {str(e)}")

            # Pauza przed kolejnym sprawdzeniem
            time.sleep(60)  # Sprawdzanie co minutę

    def _check_services_status(self) -> Dict[str, Dict]:
        """Sprawdzenie stanu wszystkich usług"""
        services_status = {}

        try:
            containers = self.docker_client.containers.list(all=True)

            for container in containers:
                services_status[container.name] = {
                    "status": container.status,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "created": container.attrs.get("Created", ""),
                    "health": container.attrs.get("State", {}).get("Health", {}).get("Status", "unknown")
                }

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania stanu usług: {str(e)}")

        return services_status

    def _archive_system_state(self, services_status: Dict[str, Dict]):
        """Archiwizacja aktualnego stanu systemu"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        state_file = os.path.join(self.backup_dir, f"system_state_{timestamp}.json")

        try:
            with open(state_file, "w") as f:
                json.dump({
                    "timestamp": timestamp,
                    "services": services_status
                }, f, indent=2)

        except Exception as e:
            logger.error(f"Błąd podczas archiwizacji stanu systemu: {str(e)}")

    def _verify_system_integrity(self, services_status: Dict[str, Dict]) -> bool:
        """Weryfikacja integralności systemu"""
        # Sprawdzenie krytycznych usług
        critical_services = ["gitlab", "ollama", "autonomous-system", "recovery-system"]

        for service in critical_services:
            if service not in services_status:
                logger.error(f"Krytyczna usługa {service} nie istnieje!")
                return False

            if services_status[service]["status"] != "running":
                logger.error(f"Krytyczna usługa {service} nie działa (status: {services_status[service]['status']})!")
                return False

        # Sprawdzenie dostępności GitLab API
        try:
            headers = {"Private-Token": self.gitlab_token}
            response = requests.get(f"{self.gitlab_url}/api/v4/projects", headers=headers, timeout=5)

            if response.status_code != 200:
                logger.error(f"GitLab API nie odpowiada prawidłowo (kod: {response.status_code})!")
                return False

        except Exception as e:
            logger.error(f"Błąd podczas sprawdzania dostępności GitLab API: {str(e)}")
            return False

        return True

    def _handle_integrity_issues(self, services_status: Dict[str, Dict]):
        """Obsługa problemów z integralnością systemu"""
        # Próba naprawy usług
        for service_name, service_info in services_status.items():
            if service_info["status"] != "running":
                logger.info(f"Próba naprawy usługi {service_name}...")

                try:
                    container = self.docker_client.containers.get(service_name)

                    # Jeśli kontener istnieje, ale nie działa, spróbuj go uruchomić
                    if service_info["status"] in ["exited", "created", "stopped"]:
                        container.start()
                        logger.info(f"Uruchomiono usługę {service_name}")
                    # Jeśli kontener jest w stanie błędu, spróbuj go zrestartować
                    elif service_info["status"] in ["restarting", "dead", "paused"]:
                        container.restart()
                        logger.info(f"Zrestartowano usługę {service_name}")

                except Exception as e:
                    logger.error(f"Błąd podczas naprawy usługi {service_name}: {str(e)}")

                    # Jeśli nie udało się naprawić, spróbuj przywrócić z kopii zapasowej
                    self._restore_service_from_backup(service_name)

    def _restore_service_from_backup(self, service_name: str):
        """Przywrócenie usługi z kopii zapasowej"""
        logger.info(f"Próba przywrócenia usługi {service_name} z kopii zapasowej...")

        try:
            # Wykonanie skryptu przywracania
            result = subprocess.run(
                f"/app/scripts/restore_service.sh {service_name}",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"Usługa {service_name} przywrócona pomyślnie")
            else:
                logger.error(f"Błąd podczas przywracania usługi {service_name}: {result.stderr}")

        except Exception as e:
            logger.error(f"Wyjątek podczas przywracania usługi {service_name}: {str(e)}")

    def create_backup(self):
        """Utworzenie pełnej kopii zapasowej systemu"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(self.backup_dir, f"system_backup_{timestamp}.tar.gz")

        logger.info(f"Tworzenie kopii zapasowej systemu: {backup_file}")

        try:
            # Wykonanie skryptu tworzenia kopii zapasowej
            result = subprocess.run(
                f"/app/scripts/create_backup.sh {backup_file}",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"Kopia zapasowa utworzona pomyślnie: {backup_file}")
                return True
            else:
                logger.error(f"Błąd podczas tworzenia kopii zapasowej: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Wyjątek podczas tworzenia kopii zapasowej: {str(e)}")
            return False

    def restore_system(self, backup_file: str = None):
        """Przywrócenie całego systemu z kopii zapasowej"""
        if not backup_file:
            # Jeśli nie podano pliku, użyj najnowszej kopii zapasowej
            backup_files = [f for f in os.listdir(self.backup_dir) if f.startswith("system_backup_")]
            backup_files.sort(reverse=True)  # Sortowanie malejąco według nazwy (timestamp)

            if not backup_files:
                logger.error("Brak dostępnych kopii zapasowych!")
                return False

            backup_file = os.path.join(self.backup_dir, backup_files[0])

        logger.info(f"Przywracanie systemu z kopii zapasowej: {backup_file}")

        try:
            # Wykonanie skryptu przywracania systemu
            result = subprocess.run(
                f"/app/scripts/restore_system.sh {backup_file}",
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info(f"System przywrócony pomyślnie z kopii zapasowej: {backup_file}")
                return True
            else:
                logger.error(f"Błąd podczas przywracania systemu: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Wyjątek podczas przywracania systemu: {str(e)}")
            return False