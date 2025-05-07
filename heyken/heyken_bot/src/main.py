"""
Główny skrypt uruchamiający bota Heyken.
"""
import os
import sys
import logging
import argparse
from dotenv import load_dotenv

from .bot_manager import BotManager

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
    parser = argparse.ArgumentParser(description='Heyken Bot - Automatyzacja tworzenia projektów')
    parser.add_argument('--env', type=str, help='Ścieżka do pliku .env')
    args = parser.parse_args()
    
    try:
        # Wczytanie zmiennych środowiskowych
        if args.env:
            env_path = args.env
        else:
            # Sprawdzenie, czy plik .env istnieje w katalogu nadrzędnym
            parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '.env')
            if os.path.exists(parent_env):
                env_path = parent_env
            else:
                env_path = None
                
        if env_path:
            logger.info(f"Wczytywanie zmiennych środowiskowych z {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("Nie znaleziono pliku .env, używanie domyślnych wartości")
            
        # Utworzenie i uruchomienie bota
        bot_manager = BotManager(env_path)
        
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
