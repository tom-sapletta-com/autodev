#!/usr/bin/env python3
"""
Skrypt uruchamiający głównego bota Heyken z poprawnie skonfigurowanym środowiskiem.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Główna funkcja uruchamiająca bota."""
    # Ustalenie ścieżek
    current_dir = Path(__file__).parent.absolute()
    env_file = current_dir / ".env"
    
    # Sprawdzenie, czy plik .env istnieje
    if not env_file.exists():
        logger.error(f"Błąd: Plik .env nie istnieje w katalogu {current_dir}")
        return 1
    
    # Sprawdzenie, czy Ollama jest dostępne
    ollama_url = "http://localhost:11434"
    
    # Sprawdzenie, czy RocketChat jest dostępny
    rocketchat_url = "http://localhost:3100"
    
    # Instalacja wymaganych pakietów
    logger.info("Instalacja wymaganych pakietów...")
    subprocess.run([sys.executable, "-m", "pip", "install", "python-dotenv", "requests"], check=True)
    
    # Uruchomienie bota
    logger.info("Uruchamianie bota...")
    
    # Ustawienie zmiennych środowiskowych
    env = os.environ.copy()
    env["PYTHONPATH"] = str(current_dir)
    
    # Uruchomienie prostego bota
    logger.info("Uruchamianie prostego bota RocketChat-Ollama...")
    subprocess.run([sys.executable, "simple_rocketchat_ollama_bot.py"], env=env, cwd=current_dir)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
