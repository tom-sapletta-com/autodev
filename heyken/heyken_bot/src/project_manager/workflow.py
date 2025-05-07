"""
Workflow projektu.
"""
import os
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from .project import Project, ProjectStatus
from ..ollama.client import OllamaClient

logger = logging.getLogger(__name__)

class ProjectWorkflow:
    """
    Workflow projektu.
    
    Koordynuje proces tworzenia projektu, od dokumentacji do wdrożenia.
    """
    
    def __init__(self, project: Project, ollama_client: OllamaClient):
        """
        Inicjalizuje workflow projektu.
        
        Args:
            project: Projekt
            ollama_client: Klient Ollama
        """
        self.project = project
        self.ollama = ollama_client
        self.status_handlers = {
            ProjectStatus.CREATED: self._handle_created,
            ProjectStatus.DOCUMENTATION: self._handle_documentation,
            ProjectStatus.PLANNING: self._handle_planning,
            ProjectStatus.CODING: self._handle_coding,
            ProjectStatus.TESTING: self._handle_testing,
            ProjectStatus.DEPLOYMENT: self._handle_deployment,
        }
        
    def advance(self) -> bool:
        """
        Przechodzi do następnego kroku workflow.
        
        Returns:
            bool: True jeśli przejście się powiodło, False w przeciwnym przypadku
        """
        current_status = self.project.status
        
        if current_status == ProjectStatus.COMPLETED or current_status == ProjectStatus.FAILED:
            logger.warning(f"Projekt {self.project.name} jest już zakończony (status: {current_status.value})")
            return False
            
        handler = self.status_handlers.get(current_status)
        if not handler:
            logger.error(f"Brak handlera dla statusu {current_status.value}")
            return False
            
        try:
            success = handler()
            if success:
                logger.info(f"Projekt {self.project.name}: krok {current_status.value} zakończony pomyślnie")
                return True
            else:
                logger.error(f"Projekt {self.project.name}: krok {current_status.value} zakończony niepowodzeniem")
                self.project.update_status(ProjectStatus.FAILED)
                return False
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania kroku {current_status.value} dla projektu {self.project.name}: {str(e)}")
            self.project.update_status(ProjectStatus.FAILED)
            return False
            
    def run_to_completion(self, callback: Optional[Callable[[ProjectStatus], None]] = None) -> bool:
        """
        Wykonuje wszystkie kroki workflow aż do zakończenia.
        
        Args:
            callback: Opcjonalna funkcja wywoływana po każdym kroku
            
        Returns:
            bool: True jeśli wszystkie kroki się powiodły, False w przeciwnym przypadku
        """
        while self.project.status not in [ProjectStatus.COMPLETED, ProjectStatus.FAILED]:
            current_status = self.project.status
            success = self.advance()
            
            if callback:
                callback(current_status)
                
            if not success:
                return False
                
        return self.project.status == ProjectStatus.COMPLETED
        
    def _handle_created(self) -> bool:
        """
        Obsługuje krok CREATED.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        # Przejście do kroku dokumentacji
        self.project.update_status(ProjectStatus.DOCUMENTATION)
        return True
        
    def _handle_documentation(self) -> bool:
        """
        Obsługuje krok DOCUMENTATION.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        try:
            # Generowanie dokumentacji
            documentation = self.ollama.generate_documentation(self.project.description)
            self.project.documentation = documentation
            
            # Dodanie dokumentacji jako pliku
            self.project.add_file(
                "docs/README.md",
                documentation,
                "Dokumentacja projektu"
            )
            
            # Przejście do kroku planowania
            self.project.update_status(ProjectStatus.PLANNING)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas generowania dokumentacji: {str(e)}")
            return False
            
    def _handle_planning(self) -> bool:
        """
        Obsługuje krok PLANNING.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        try:
            # Generowanie planu implementacji
            prompt = f"""
            Na podstawie poniższego opisu projektu, stwórz szczegółowy plan implementacji w języku naturalnym.
            Plan powinien zawierać logiczne kroki, które należy wykonać, aby zaimplementować projekt.
            
            Opis projektu:
            {self.project.description}
            
            Dokumentacja:
            {self.project.documentation}
            
            Plan powinien być podzielony na sekcje:
            1. Struktura projektu
            2. Główne komponenty
            3. Interfejsy i API
            4. Przepływ danych
            5. Kroki implementacji
            6. Testy
            """
            
            plan = self.ollama.generate(prompt)
            self.project.plan = plan
            
            # Dodanie planu jako pliku
            self.project.add_file(
                "PLAN.md",
                plan,
                "Plan implementacji projektu"
            )
            
            # Przejście do kroku kodowania
            self.project.update_status(ProjectStatus.CODING)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas generowania planu: {str(e)}")
            return False
            
    def _handle_coding(self) -> bool:
        """
        Obsługuje krok CODING.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        try:
            # Konwersja planu na kod
            prompt = f"""
            Na podstawie poniższego planu implementacji, wygeneruj kod źródłowy projektu.
            
            Opis projektu:
            {self.project.description}
            
            Plan implementacji:
            {self.project.plan}
            
            Wygeneruj kod dla wszystkich niezbędnych plików, w tym:
            1. Pliki źródłowe
            2. Testy
            3. Konfigurację
            4. Dokumentację
            
            Dla każdego pliku, podaj jego ścieżkę i zawartość w formacie:
            
            ### ŚCIEŻKA/DO/PLIKU.py ###
            ```python
            # Zawartość pliku
            ```
            """
            
            code_response = self.ollama.generate(prompt)
            self.project.natural_language_code = code_response
            
            # Parsowanie odpowiedzi i dodanie plików
            current_file = None
            current_content = []
            
            for line in code_response.split("\n"):
                if line.startswith("### ") and line.endswith(" ###"):
                    # Zapisz poprzedni plik
                    if current_file and current_content:
                        file_content = "\n".join(current_content)
                        self.project.add_file(current_file, file_content, f"Wygenerowany plik: {current_file}")
                        current_content = []
                    
                    # Ustaw nowy plik
                    current_file = line.strip("# ").strip()
                elif current_file:
                    # Usuń znaczniki kodu Markdown
                    if line.startswith("```") and (len(line) == 3 or line[3:].strip() in ["python", "javascript", "html", "css", "json", "yaml", "bash", "sh"]):
                        continue
                    if line == "```":
                        continue
                    current_content.append(line)
                    
            # Zapisz ostatni plik
            if current_file and current_content:
                file_content = "\n".join(current_content)
                self.project.add_file(current_file, file_content, f"Wygenerowany plik: {current_file}")
            
            # Przejście do kroku testowania
            self.project.update_status(ProjectStatus.TESTING)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas generowania kodu: {str(e)}")
            return False
            
    def _handle_testing(self) -> bool:
        """
        Obsługuje krok TESTING.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        try:
            # Analiza kodu i generowanie testów
            test_results = {}
            
            for path, file in self.project.files.items():
                # Pomijamy pliki dokumentacji i konfiguracji
                if path.startswith("docs/") or path == "PLAN.md" or not path.endswith((".py", ".js")):
                    continue
                    
                # Analiza kodu
                analysis = self.ollama.analyze_code(file.content, "python" if path.endswith(".py") else "javascript")
                
                # Generowanie testów
                tests = self.ollama.generate_test_cases(file.content, "python" if path.endswith(".py") else "javascript")
                
                # Dodanie testów jako plików
                test_path = f"tests/test_{os.path.basename(path)}"
                self.project.add_file(test_path, tests, f"Testy dla {path}")
                
                # Zapisanie wyników analizy
                test_results[path] = {
                    "analysis": analysis,
                    "test_path": test_path
                }
                
            self.project.test_results = test_results
            
            # Przejście do kroku wdrożenia
            self.project.update_status(ProjectStatus.DEPLOYMENT)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas testowania: {str(e)}")
            return False
            
    def _handle_deployment(self) -> bool:
        """
        Obsługuje krok DEPLOYMENT.
        
        Returns:
            bool: True jeśli krok się powiódł, False w przeciwnym przypadku
        """
        try:
            # Generowanie konfiguracji Dockera
            docker_config = self.ollama.generate_docker_config(
                f"""
                Opis projektu:
                {self.project.description}
                
                Plan implementacji:
                {self.project.plan}
                
                Struktura plików:
                {', '.join(self.project.files.keys())}
                """,
                "python"
            )
            
            self.project.docker_config = docker_config
            
            # Dodanie plików konfiguracyjnych Dockera
            for filename, content in docker_config.items():
                self.project.add_file(filename, content, f"Konfiguracja Dockera: {filename}")
                
            # Symulacja wdrożenia w środowisku sandbox
            self.project.sandbox_url = f"http://localhost:8080/{self.project.name.replace(' ', '_').lower()}"
            
            # Zakończenie workflow
            self.project.update_status(ProjectStatus.COMPLETED)
            return True
        except Exception as e:
            logger.error(f"Błąd podczas wdrażania: {str(e)}")
            return False
