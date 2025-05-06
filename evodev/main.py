"""
Główny moduł EvoDev - integruje wszystkie funkcjonalności systemu
"""
import os
import sys
import json
import logging
import argparse
import re
from typing import Dict, List, Optional, Tuple, Any

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("evodev")

# Importy modułów EvoDev
try:
    from . import web_projects
except ImportError:
    logger.warning("Nie można zaimportować modułu web_projects")
    web_projects = None

class EvoDev:
    """Główna klasa EvoDev integrująca wszystkie funkcjonalności systemu"""
    
    def __init__(self):
        self.logger = logger
        self.logger.info("Inicjalizacja systemu EvoDev")
        
    def process_command(self, command: str) -> str:
        """Przetwarza polecenie użytkownika i zwraca odpowiedź"""
        self.logger.info(f"Przetwarzanie polecenia: {command}")
        
        # Sprawdź, czy polecenie dotyczy tworzenia strony testowej
        create_web_match = re.search(r'(stwórz|utwórz|zrób|wykonaj)\s+stron[ęea]\s+testow[ąa]', command.lower())
        if create_web_match:
            return self._handle_create_web_command(command)
        
        # Sprawdź, czy polecenie dotyczy uruchomienia strony
        run_web_match = re.search(r'uruchom\s+stron[ęea]', command.lower())
        if run_web_match:
            return self._handle_run_web_command(command)
        
        # Domyślna odpowiedź, jeśli nie rozpoznano polecenia
        return "Przepraszam, nie rozumiem tego polecenia. Czy mogę pomóc w czymś innym związanym z programowaniem lub administracją systemem?"
    
    def _handle_create_web_command(self, command: str) -> str:
        """Obsługuje polecenie utworzenia strony testowej"""
        if web_projects is None:
            return "Przepraszam, moduł do zarządzania projektami webowymi nie jest dostępny."
        
        # Sprawdź, czy podano port
        port_match = re.search(r'port[:\s]+(\d+)', command.lower())
        port = int(port_match.group(1)) if port_match else 8088
        
        # Sprawdź, czy podano typ projektu
        project_type = "static"  # domyślnie statyczna strona HTML
        if "react" in command.lower():
            project_type = "react"
        elif "flask" in command.lower() or "python" in command.lower():
            project_type = "flask"
        
        # Generuj nazwę projektu
        project_name = f"testowa-strona-{project_type}"
        
        # Utwórz i wdróż projekt
        success, message = web_projects.create_and_deploy_project(
            name=project_name,
            project_type=project_type,
            port=port
        )
        
        if success:
            return f"Utworzyłem stronę testową typu {project_type}. {message}"
        else:
            return f"Nie udało się utworzyć strony testowej. {message}"
    
    def _handle_run_web_command(self, command: str) -> str:
        """Obsługuje polecenie uruchomienia strony"""
        if web_projects is None:
            return "Przepraszam, moduł do zarządzania projektami webowymi nie jest dostępny."
        
        # Sprawdź, czy podano port
        port_match = re.search(r'(localhost|127\.0\.0\.1)[:/](\d+)', command.lower())
        port = int(port_match.group(2)) if port_match else 8088
        
        # Sprawdź, czy istnieje projekt z tym portem
        projects = web_projects.list_projects()
        matching_project = None
        
        for project in projects:
            if project.get("port") == port:
                matching_project = project
                break
        
        if matching_project:
            # Uruchom istniejący projekt
            project = web_projects.get_project(matching_project["name"])
            if project and project.start():
                return f"Uruchomiłem stronę {matching_project['name']} na porcie {port}. Dostępna pod adresem http://localhost:{port}"
            else:
                return f"Nie udało się uruchomić strony na porcie {port}."
        else:
            # Utwórz nowy projekt, jeśli nie istnieje
            project_name = f"testowa-strona-{port}"
            success, message = web_projects.create_and_deploy_project(
                name=project_name,
                project_type="static",
                port=port
            )
            
            if success:
                return f"Utworzyłem i uruchomiłem nową stronę testową. {message}"
            else:
                return f"Nie udało się utworzyć i uruchomić strony testowej. {message}"

def main():
    """Funkcja główna programu"""
    parser = argparse.ArgumentParser(description="EvoDev - system do automatyzacji procesów deweloperskich")
    parser.add_argument("--command", help="Polecenie do wykonania")
    args = parser.parse_args()
    
    evodev = EvoDev()
    
    if args.command:
        response = evodev.process_command(args.command)
        print(response)
    else:
        logger.info("Uruchamianie systemu EvoDev w trybie serwera")
        # Tutaj można dodać kod do uruchomienia serwera, jeśli potrzebne
        
if __name__ == "__main__":
    main()
