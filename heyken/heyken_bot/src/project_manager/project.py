"""
Klasa reprezentująca projekt.
"""
import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class ProjectStatus(Enum):
    """Status projektu."""
    CREATED = "created"
    DOCUMENTATION = "documentation"
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProjectFile:
    """Reprezentacja pliku w projekcie."""
    path: str
    content: str
    description: str = ""
    
    def save(self, base_dir: str) -> bool:
        """
        Zapisuje plik na dysku.
        
        Args:
            base_dir: Katalog bazowy projektu
            
        Returns:
            bool: True jeśli zapisanie się powiodło, False w przeciwnym przypadku
        """
        try:
            full_path = os.path.join(base_dir, self.path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(self.content)
                
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania pliku {self.path}: {str(e)}")
            return False


@dataclass
class Project:
    """Reprezentacja projektu."""
    name: str
    description: str
    created_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    updated_at: datetime.datetime = field(default_factory=datetime.datetime.now)
    status: ProjectStatus = ProjectStatus.CREATED
    files: Dict[str, ProjectFile] = field(default_factory=dict)
    documentation: str = ""
    plan: str = ""
    natural_language_code: str = ""
    docker_config: Dict[str, str] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    sandbox_url: str = ""
    creator_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konwertuje projekt do słownika.
        
        Returns:
            Dict[str, Any]: Słownik reprezentujący projekt
        """
        result = asdict(self)
        result["status"] = self.status.value
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        result["files"] = {path: asdict(file) for path, file in self.files.items()}
        return result
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """
        Tworzy projekt z słownika.
        
        Args:
            data: Słownik reprezentujący projekt
            
        Returns:
            Project: Utworzony projekt
        """
        # Konwersja dat
        created_at = datetime.datetime.fromisoformat(data["created_at"])
        updated_at = datetime.datetime.fromisoformat(data["updated_at"])
        
        # Konwersja statusu
        status = ProjectStatus(data["status"])
        
        # Konwersja plików
        files = {
            path: ProjectFile(**file_data)
            for path, file_data in data.get("files", {}).items()
        }
        
        # Usunięcie przetworzonych pól
        data_copy = data.copy()
        for field_name in ["created_at", "updated_at", "status", "files"]:
            if field_name in data_copy:
                del data_copy[field_name]
                
        # Utworzenie projektu
        return cls(
            **data_copy,
            created_at=created_at,
            updated_at=updated_at,
            status=status,
            files=files
        )
        
    def save(self, base_dir: str) -> bool:
        """
        Zapisuje projekt na dysku.
        
        Args:
            base_dir: Katalog bazowy dla projektów
            
        Returns:
            bool: True jeśli zapisanie się powiodło, False w przeciwnym przypadku
        """
        try:
            # Aktualizacja czasu modyfikacji
            self.updated_at = datetime.datetime.now()
            
            # Utworzenie katalogu projektu
            project_dir = os.path.join(base_dir, self.name.replace(" ", "_").lower())
            os.makedirs(project_dir, exist_ok=True)
            
            # Zapisanie metadanych projektu
            metadata_path = os.path.join(project_dir, "project.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2)
                
            # Zapisanie dokumentacji
            if self.documentation:
                docs_dir = os.path.join(project_dir, "docs")
                os.makedirs(docs_dir, exist_ok=True)
                
                with open(os.path.join(docs_dir, "README.md"), "w", encoding="utf-8") as f:
                    f.write(self.documentation)
                    
            # Zapisanie planu
            if self.plan:
                with open(os.path.join(project_dir, "PLAN.md"), "w", encoding="utf-8") as f:
                    f.write(self.plan)
                    
            # Zapisanie plików projektu
            for path, file in self.files.items():
                file.save(project_dir)
                
            # Zapisanie konfiguracji Dockera
            if self.docker_config:
                for filename, content in self.docker_config.items():
                    with open(os.path.join(project_dir, filename), "w", encoding="utf-8") as f:
                        f.write(content)
                        
            return True
        except Exception as e:
            logger.error(f"Błąd podczas zapisywania projektu {self.name}: {str(e)}")
            return False
            
    @classmethod
    def load(cls, base_dir: str, project_name: str) -> Optional["Project"]:
        """
        Wczytuje projekt z dysku.
        
        Args:
            base_dir: Katalog bazowy dla projektów
            project_name: Nazwa projektu
            
        Returns:
            Optional[Project]: Wczytany projekt lub None w przypadku błędu
        """
        try:
            project_dir = os.path.join(base_dir, project_name.replace(" ", "_").lower())
            metadata_path = os.path.join(project_dir, "project.json")
            
            if not os.path.exists(metadata_path):
                logger.error(f"Nie znaleziono pliku metadanych projektu: {metadata_path}")
                return None
                
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania projektu {project_name}: {str(e)}")
            return None
            
    def add_file(self, path: str, content: str, description: str = "") -> None:
        """
        Dodaje plik do projektu.
        
        Args:
            path: Ścieżka do pliku (względem katalogu projektu)
            content: Zawartość pliku
            description: Opis pliku
        """
        self.files[path] = ProjectFile(path, content, description)
        self.updated_at = datetime.datetime.now()
        
    def get_file(self, path: str) -> Optional[ProjectFile]:
        """
        Pobiera plik z projektu.
        
        Args:
            path: Ścieżka do pliku (względem katalogu projektu)
            
        Returns:
            Optional[ProjectFile]: Plik lub None, jeśli nie istnieje
        """
        return self.files.get(path)
        
    def update_status(self, status: ProjectStatus) -> None:
        """
        Aktualizuje status projektu.
        
        Args:
            status: Nowy status projektu
        """
        self.status = status
        self.updated_at = datetime.datetime.now()
        logger.info(f"Projekt {self.name}: zmiana statusu na {status.value}")
        
    def get_summary(self) -> str:
        """
        Generuje podsumowanie projektu.
        
        Returns:
            str: Podsumowanie projektu w formacie Markdown
        """
        files_count = len(self.files)
        
        summary = f"""# Projekt: {self.name}

## Status: {self.status.value}

## Opis
{self.description}

## Statystyki
- Utworzony: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- Ostatnia aktualizacja: {self.updated_at.strftime('%Y-%m-%d %H:%M:%S')}
- Liczba plików: {files_count}

## Pliki
"""
        
        for path, file in sorted(self.files.items()):
            summary += f"- `{path}`: {file.description or 'Brak opisu'}\n"
            
        if self.sandbox_url:
            summary += f"\n## Sandbox\n{self.sandbox_url}\n"
            
        return summary
