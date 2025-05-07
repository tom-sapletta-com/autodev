"""
Menedżer projektów.
"""
import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Any, Union
from .project import Project, ProjectStatus

logger = logging.getLogger(__name__)

class ProjectManager:
    """
    Menedżer projektów.
    
    Zarządza projektami, umożliwiając ich tworzenie, wczytywanie, zapisywanie i listowanie.
    """
    
    def __init__(self, projects_dir: str):
        """
        Inicjalizuje menedżera projektów.
        
        Args:
            projects_dir: Katalog bazowy dla projektów
        """
        self.projects_dir = projects_dir
        os.makedirs(projects_dir, exist_ok=True)
        self.projects: Dict[str, Project] = {}
        self._load_projects()
        
    def _load_projects(self) -> None:
        """
        Wczytuje projekty z dysku.
        """
        try:
            for item in os.listdir(self.projects_dir):
                project_dir = os.path.join(self.projects_dir, item)
                if os.path.isdir(project_dir):
                    metadata_path = os.path.join(project_dir, "project.json")
                    if os.path.exists(metadata_path):
                        project = Project.load(self.projects_dir, item)
                        if project:
                            self.projects[project.name] = project
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania projektów: {str(e)}")
            
    def create_project(self, name: str, description: str, creator_id: str = "") -> Project:
        """
        Tworzy nowy projekt.
        
        Args:
            name: Nazwa projektu
            description: Opis projektu
            creator_id: ID twórcy projektu
            
        Returns:
            Project: Utworzony projekt
        """
        if name in self.projects:
            raise ValueError(f"Projekt o nazwie '{name}' już istnieje")
            
        project = Project(name=name, description=description, creator_id=creator_id)
        self.projects[name] = project
        project.save(self.projects_dir)
        logger.info(f"Utworzono projekt: {name}")
        return project
        
    def get_project(self, name: str) -> Optional[Project]:
        """
        Pobiera projekt o podanej nazwie.
        
        Args:
            name: Nazwa projektu
            
        Returns:
            Optional[Project]: Projekt lub None, jeśli nie istnieje
        """
        return self.projects.get(name)
        
    def save_project(self, project: Project) -> bool:
        """
        Zapisuje projekt na dysku.
        
        Args:
            project: Projekt do zapisania
            
        Returns:
            bool: True jeśli zapisanie się powiodło, False w przeciwnym przypadku
        """
        return project.save(self.projects_dir)
        
    def delete_project(self, name: str) -> bool:
        """
        Usuwa projekt.
        
        Args:
            name: Nazwa projektu
            
        Returns:
            bool: True jeśli usunięcie się powiodło, False w przeciwnym przypadku
        """
        if name not in self.projects:
            logger.warning(f"Próba usunięcia nieistniejącego projektu: {name}")
            return False
            
        try:
            project_dir = os.path.join(self.projects_dir, name.replace(" ", "_").lower())
            if os.path.exists(project_dir):
                import shutil
                shutil.rmtree(project_dir)
                
            del self.projects[name]
            logger.info(f"Usunięto projekt: {name}")
            return True
        except Exception as e:
            logger.error(f"Błąd podczas usuwania projektu {name}: {str(e)}")
            return False
            
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę projektów.
        
        Returns:
            List[Dict[str, Any]]: Lista projektów w formie słowników
        """
        return [
            {
                "name": project.name,
                "description": project.description,
                "status": project.status.value,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "files_count": len(project.files),
                "creator_id": project.creator_id
            }
            for project in self.projects.values()
        ]
        
    def get_project_by_creator(self, creator_id: str) -> List[Project]:
        """
        Zwraca projekty utworzone przez podanego użytkownika.
        
        Args:
            creator_id: ID twórcy projektu
            
        Returns:
            List[Project]: Lista projektów
        """
        return [
            project for project in self.projects.values()
            if project.creator_id == creator_id
        ]
        
    def get_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        """
        Zwraca projekty o podanym statusie.
        
        Args:
            status: Status projektów
            
        Returns:
            List[Project]: Lista projektów
        """
        return [
            project for project in self.projects.values()
            if project.status == status
        ]
