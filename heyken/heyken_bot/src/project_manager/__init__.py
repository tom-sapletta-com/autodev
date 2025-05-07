"""
Moduł zarządzania projektami.

Ten moduł zawiera klasy i funkcje do zarządzania projektami,
koordynując cały proces od dokumentacji do wdrożenia.
"""

from .project import Project
from .manager import ProjectManager
from .workflow import ProjectWorkflow

__all__ = ["Project", "ProjectManager", "ProjectWorkflow"]
