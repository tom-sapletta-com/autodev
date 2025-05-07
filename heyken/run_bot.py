#!/usr/bin/env python3
"""
Prosty skrypt uruchamiający bota Heyken bez instalacji pakietu.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Dodanie katalogów do ścieżki, aby można było importować moduły
sys.path.append(os.path.dirname(__file__))

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('heyken_bot.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """
    Główna funkcja uruchamiająca bota.
    """
    try:
        # Wczytanie zmiennych środowiskowych
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            logger.info(f"Wczytywanie zmiennych środowiskowych z {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("Nie znaleziono pliku .env, używanie domyślnych wartości")
            
        # Import modułów bota
        from heyken_bot.src.bot_manager import BotManager
        
        # Utworzenie i uruchomienie bota
        bot_manager = BotManager()
        
        logger.info("Bot Heyken uruchomiony")
        logger.info(f"RocketChat URL: {bot_manager.rocketchat_url}")
        logger.info(f"RocketChat Bot: {bot_manager.rocketchat_username}")
        logger.info(f"Ollama URL: {bot_manager.ollama_url}")
        logger.info(f"Ollama Model: {bot_manager.ollama_model}")
        logger.info(f"Katalog projektów: {bot_manager.projects_dir}")
        
        # Uruchomienie bota
        bot_manager.start()
        
    except KeyboardInterrupt:
        logger.info("Bot zatrzymany przez użytkownika")
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania bota: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
