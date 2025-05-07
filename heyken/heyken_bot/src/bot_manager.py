"""
Menedżer bota integrujący RocketChat z Ollama i zarządzaniem projektami.
"""
import os
import logging
import time
import re
from typing import Dict, List, Optional, Any, Union
from dotenv import load_dotenv

from .rocketchat.bot import RocketChatBot
from .rocketchat.client import Message
from .ollama.client import OllamaClient
from .project_manager.manager import ProjectManager
from .project_manager.workflow import ProjectWorkflow
from .project_manager.project import Project, ProjectStatus

logger = logging.getLogger(__name__)

class BotManager:
    """
    Menedżer bota integrujący RocketChat z Ollama i zarządzaniem projektami.
    
    Umożliwia komunikację między RocketChat a Ollama, zarządzanie projektami
    i automatyzację procesu tworzenia projektów.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicjalizuje menedżera bota.
        
        Args:
            config_path: Ścieżka do pliku konfiguracyjnego .env
        """
        # Wczytanie zmiennych środowiskowych
        if config_path:
            load_dotenv(config_path)
        else:
            load_dotenv()
            
        # Konfiguracja RocketChat
        self.rocketchat_url = os.getenv("ROCKETCHAT_URL", "http://localhost:3100")
        self.rocketchat_username = os.getenv("ROCKETCHAT_BOT_USERNAME", "heyken_bot")
        self.rocketchat_password = os.getenv("ROCKETCHAT_BOT_PASSWORD", "heyken123")
        
        # Konfiguracja Ollama
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        # Konfiguracja projektów
        self.projects_dir = os.getenv("PROJECTS_DIR", "./projects")
        
        # Inicjalizacja klientów
        self.rocketchat_bot = RocketChatBot(
            self.rocketchat_url,
            self.rocketchat_username,
            self.rocketchat_password
        )
        
        self.ollama_client = OllamaClient(
            self.ollama_url,
            self.ollama_model
        )
        
        self.project_manager = ProjectManager(self.projects_dir)
        
        # Rejestracja handlerów
        self._register_handlers()
        
    def _register_handlers(self) -> None:
        """
        Rejestruje handlery dla różnych typów wiadomości.
        """
        # Handler dla tworzenia projektu
        self.rocketchat_bot.register_handler(
            r"(?i)utwórz projekt\s+(.+)",
            self._handle_create_project
        )
        
        # Handler dla listy projektów
        self.rocketchat_bot.register_handler(
            r"(?i)pokaż projekty|lista projektów",
            self._handle_list_projects
        )
        
        # Handler dla szczegółów projektu
        self.rocketchat_bot.register_handler(
            r"(?i)pokaż projekt\s+(.+)",
            self._handle_show_project
        )
        
        # Handler dla uruchomienia workflow projektu
        self.rocketchat_bot.register_handler(
            r"(?i)uruchom projekt\s+(.+)",
            self._handle_run_project
        )
        
        # Handler dla generowania kodu
        self.rocketchat_bot.register_handler(
            r"(?i)generuj kod\s+(.+)",
            self._handle_generate_code
        )
        
        # Handler dla generowania dokumentacji
        self.rocketchat_bot.register_handler(
            r"(?i)generuj dokumentację\s+(.+)",
            self._handle_generate_documentation
        )
        
        # Handler dla pomocy
        self.rocketchat_bot.register_handler(
            r"(?i)pomoc|help",
            self._handle_help
        )
        
        # Domyślny handler
        self.rocketchat_bot.set_default_handler(self._handle_default)
        
    def start(self) -> None:
        """
        Uruchamia bota.
        """
        logger.info("Uruchamianie bota...")
        self.rocketchat_bot.start()
        
    def stop(self) -> None:
        """
        Zatrzymuje bota.
        """
        logger.info("Zatrzymywanie bota...")
        self.rocketchat_bot.stop()
        
    def _handle_create_project(self, message: Message) -> str:
        """
        Obsługuje żądanie utworzenia projektu.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        # Wyciągnięcie nazwy i opisu projektu
        match = re.search(r"(?i)utwórz projekt\s+([^:]+)(?::\s*(.+))?", message.text)
        if not match:
            return "Nie mogę utworzyć projektu. Podaj nazwę i opcjonalnie opis projektu, np. 'utwórz projekt Mój Projekt: Opis projektu'"
            
        name = match.group(1).strip()
        description = match.group(2).strip() if match.group(2) else f"Projekt {name}"
        
        try:
            # Sprawdzenie, czy projekt już istnieje
            if self.project_manager.get_project(name):
                return f"Projekt o nazwie '{name}' już istnieje. Wybierz inną nazwę."
                
            # Utworzenie projektu
            project = self.project_manager.create_project(
                name=name,
                description=description,
                creator_id=message.sender_id
            )
            
            return f"Utworzono projekt '{name}'.\nAby rozpocząć automatyczne generowanie, wpisz 'uruchom projekt {name}'."
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia projektu: {str(e)}")
            return f"Wystąpił błąd podczas tworzenia projektu: {str(e)}"
            
    def _handle_list_projects(self, message: Message) -> str:
        """
        Obsługuje żądanie listy projektów.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        projects = self.project_manager.list_projects()
        
        if not projects:
            return "Brak projektów. Utwórz nowy projekt wpisując 'utwórz projekt Nazwa Projektu: Opis projektu'."
            
        response = "Lista projektów:\n\n"
        for project in projects:
            response += f"- **{project['name']}** (status: {project['status']})\n"
            response += f"  {project['description']}\n\n"
            
        return response
        
    def _handle_show_project(self, message: Message) -> str:
        """
        Obsługuje żądanie wyświetlenia szczegółów projektu.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        match = re.search(r"(?i)pokaż projekt\s+(.+)", message.text)
        if not match:
            return "Nie mogę wyświetlić projektu. Podaj nazwę projektu, np. 'pokaż projekt Mój Projekt'"
            
        name = match.group(1).strip()
        
        project = self.project_manager.get_project(name)
        if not project:
            return f"Projekt '{name}' nie istnieje."
            
        return project.get_summary()
        
    def _handle_run_project(self, message: Message) -> str:
        """
        Obsługuje żądanie uruchomienia workflow projektu.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        match = re.search(r"(?i)uruchom projekt\s+(.+)", message.text)
        if not match:
            return "Nie mogę uruchomić projektu. Podaj nazwę projektu, np. 'uruchom projekt Mój Projekt'"
            
        name = match.group(1).strip()
        
        project = self.project_manager.get_project(name)
        if not project:
            return f"Projekt '{name}' nie istnieje."
            
        # Sprawdzenie, czy projekt jest już zakończony
        if project.status == ProjectStatus.COMPLETED:
            return f"Projekt '{name}' jest już zakończony."
            
        if project.status == ProjectStatus.FAILED:
            return f"Projekt '{name}' zakończył się niepowodzeniem. Utwórz nowy projekt."
            
        # Uruchomienie workflow w tle
        self.rocketchat_bot.send_message(
            message.room_id,
            f"Rozpoczynam automatyczne generowanie projektu '{name}'..."
        )
        
        # Utworzenie workflow
        workflow = ProjectWorkflow(project, self.ollama_client)
        
        # Funkcja callback do wysyłania aktualizacji
        def status_callback(status: ProjectStatus) -> None:
            self.rocketchat_bot.send_message(
                message.room_id,
                f"Projekt '{name}': zakończono krok {status.value}, przechodzę do następnego kroku..."
            )
            
        # Uruchomienie workflow w osobnym wątku
        import threading
        
        def run_workflow() -> None:
            success = workflow.run_to_completion(status_callback)
            
            if success:
                self.rocketchat_bot.send_message(
                    message.room_id,
                    f"Projekt '{name}' został pomyślnie wygenerowany i wdrożony.\n\n{project.get_summary()}"
                )
            else:
                self.rocketchat_bot.send_message(
                    message.room_id,
                    f"Wystąpił błąd podczas generowania projektu '{name}'.\n\n{project.get_summary()}"
                )
                
            # Zapisanie projektu
            self.project_manager.save_project(project)
            
        thread = threading.Thread(target=run_workflow)
        thread.start()
        
        return f"Rozpoczęto automatyczne generowanie projektu '{name}'. Będę informować o postępach."
        
    def _handle_generate_code(self, message: Message) -> str:
        """
        Obsługuje żądanie generowania kodu.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        match = re.search(r"(?i)generuj kod\s+(.+)", message.text)
        if not match:
            return "Nie mogę wygenerować kodu. Podaj opis kodu, np. 'generuj kod funkcja do sortowania listy'"
            
        description = match.group(1).strip()
        
        try:
            code = self.ollama_client.generate_code(description)
            return f"Wygenerowany kod:\n\n```python\n{code}\n```"
        except Exception as e:
            logger.error(f"Błąd podczas generowania kodu: {str(e)}")
            return f"Wystąpił błąd podczas generowania kodu: {str(e)}"
            
    def _handle_generate_documentation(self, message: Message) -> str:
        """
        Obsługuje żądanie generowania dokumentacji.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        match = re.search(r"(?i)generuj dokumentację\s+(.+)", message.text)
        if not match:
            return "Nie mogę wygenerować dokumentacji. Podaj opis projektu, np. 'generuj dokumentację aplikacja do zarządzania zadaniami'"
            
        description = match.group(1).strip()
        
        try:
            documentation = self.ollama_client.generate_documentation(description)
            return f"Wygenerowana dokumentacja:\n\n{documentation}"
        except Exception as e:
            logger.error(f"Błąd podczas generowania dokumentacji: {str(e)}")
            return f"Wystąpił błąd podczas generowania dokumentacji: {str(e)}"
            
    def _handle_help(self, message: Message) -> str:
        """
        Obsługuje żądanie pomocy.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        return """# Pomoc Heyken Bot

## Dostępne komendy:

### Zarządzanie projektami
- **utwórz projekt [nazwa]: [opis]** - tworzy nowy projekt
- **pokaż projekty** - wyświetla listę projektów
- **pokaż projekt [nazwa]** - wyświetla szczegóły projektu
- **uruchom projekt [nazwa]** - uruchamia automatyczne generowanie projektu

### Generowanie kodu i dokumentacji
- **generuj kod [opis]** - generuje kod na podstawie opisu
- **generuj dokumentację [opis]** - generuje dokumentację na podstawie opisu

### Inne
- **pomoc** - wyświetla tę pomoc

## Przykłady:
- utwórz projekt Aplikacja Todo: Prosta aplikacja do zarządzania zadaniami
- pokaż projekty
- pokaż projekt Aplikacja Todo
- uruchom projekt Aplikacja Todo
- generuj kod funkcja do sortowania listy
- generuj dokumentację aplikacja do zarządzania zadaniami
"""
        
    def _handle_default(self, message: Message) -> str:
        """
        Obsługuje wiadomości, które nie pasują do żadnego wzorca.
        
        Args:
            message: Wiadomość z RocketChat
            
        Returns:
            str: Odpowiedź dla użytkownika
        """
        try:
            # Sprawdzenie, czy Ollama jest dostępna
            if not hasattr(self.ollama_client, 'is_connected') or not self.ollama_client.is_connected:
                logger.warning("Ollama nie jest dostępna, używanie prostej odpowiedzi")
                return f"Cześć {message.sender_username}! Jestem botem Heyken. Obecnie nie mam połączenia z Ollama, więc moje możliwości są ograniczone. Wpisz 'pomoc', aby zobaczyć listę dostępnych komend."
            
            # Sprawdzenie, czy model jest dostępny
            model_available = False
            try:
                models_response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
                if models_response.status_code == 200:
                    models = models_response.json().get("models", [])
                    model_available = any(m.get('name') == self.ollama_model for m in models)
            except Exception as e:
                logger.error(f"Błąd podczas sprawdzania dostępności modelu: {str(e)}")
            
            if not model_available:
                logger.warning(f"Model {self.ollama_model} nie jest dostępny, używanie prostej odpowiedzi")
                return f"Cześć {message.sender_username}! Jestem botem Heyken. Model {self.ollama_model} jest obecnie niedostępny, więc moje możliwości są ograniczone. Wpisz 'pomoc', aby zobaczyć listę dostępnych komend."
            
            # Generowanie odpowiedzi za pomocą Ollama
            prompt = f"""
            Użytkownik {message.sender_username} napisał:
            {message.text}
            
            Odpowiedz krótko i pomocnie. Jeśli użytkownik pyta o funkcje bota,
            zasugeruj użycie komendy 'pomoc' w celu uzyskania listy dostępnych komend.
            """
            
            response = self.ollama_client.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Błąd podczas generowania odpowiedzi: {str(e)}")
            return "Przepraszam, nie mogę teraz odpowiedzieć. Spróbuj ponownie później lub wpisz 'pomoc', aby zobaczyć dostępne komendy."
