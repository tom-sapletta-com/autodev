#!/usr/bin/env python3
"""
Prosty skrypt testowy do sprawdzenia, czy Ollama działa i może generować odpowiedzi.
"""
import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_ollama_connection(base_url):
    """
    Sprawdza połączenie z Ollama.
    
    Args:
        base_url: Bazowy URL API Ollama
        
    Returns:
        bool: True jeśli połączenie jest dostępne, False w przeciwnym przypadku
    """
    try:
        url = f"{base_url}/api/tags"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            logger.info(f"Połączono z Ollama. Dostępne modele: {[m.get('name') for m in models]}")
            return True, models
        else:
            logger.error(f"Błąd połączenia z Ollama: {response.status_code} - {response.text}")
            return False, []
    except Exception as e:
        logger.error(f"Nie można połączyć się z Ollama pod adresem {base_url}: {str(e)}")
        return False, []

def generate_text(base_url, model, prompt):
    """
    Generuje tekst za pomocą Ollama.
    
    Args:
        base_url: Bazowy URL API Ollama
        model: Nazwa modelu
        prompt: Prompt dla modelu
        
    Returns:
        str: Wygenerowany tekst
    """
    try:
        # Użyjemy API /api/chat zamiast /api/generate, ponieważ jest bardziej niezawodne
        url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        logger.info(f"Wysyłanie żądania do Ollama: {json.dumps(payload)}")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            try:
                return response.json().get("message", {}).get("content", "")
            except json.JSONDecodeError:
                # Spróbujmy przetworzyć odpowiedź jako tekst
                logger.warning("Nie można przetworzyć odpowiedzi jako JSON, próba przetworzenia jako tekst")
                return response.text
        else:
            logger.error(f"Błąd API Ollama: {response.status_code} - {response.text}")
            return f"Błąd API Ollama: {response.status_code}"
    except Exception as e:
        logger.error(f"Wyjątek podczas generowania tekstu: {str(e)}")
        return f"Błąd: {str(e)}"

def generate_text_stream(base_url, model, prompt):
    """
    Generuje tekst za pomocą Ollama w trybie strumieniowym.
    
    Args:
        base_url: Bazowy URL API Ollama
        model: Nazwa modelu
        prompt: Prompt dla modelu
        
    Returns:
        str: Wygenerowany tekst
    """
    try:
        url = f"{base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False  # Wyłączamy tryb strumieniowy, aby otrzymać pełną odpowiedź
        }
        
        logger.info(f"Wysyłanie żądania do Ollama: {json.dumps(payload)}")
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            try:
                return response.json().get("response", "")
            except json.JSONDecodeError:
                # Spróbujmy przetworzyć odpowiedź jako tekst
                logger.warning("Nie można przetworzyć odpowiedzi jako JSON, próba przetworzenia jako tekst")
                return response.text
        else:
            logger.error(f"Błąd API Ollama: {response.status_code} - {response.text}")
            return f"Błąd API Ollama: {response.status_code}"
    except Exception as e:
        logger.error(f"Wyjątek podczas generowania tekstu: {str(e)}")
        return f"Błąd: {str(e)}"

def main():
    """
    Główna funkcja testująca połączenie z Ollama.
    """
    try:
        # Wczytanie zmiennych środowiskowych
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            logger.info(f"Wczytywanie zmiennych środowiskowych z {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("Nie znaleziono pliku .env, używanie domyślnych wartości")
            
        # Konfiguracja Ollama
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        logger.info(f"Ollama URL: {ollama_url}")
        logger.info(f"Ollama Model: {ollama_model}")
        
        # Sprawdzenie połączenia z Ollama
        connected, models = check_ollama_connection(ollama_url)
        
        if not connected:
            logger.error("Nie można połączyć się z Ollama")
            return
            
        # Sprawdzenie, czy model jest dostępny
        model_names = [m.get('name') for m in models]
        if ollama_model not in model_names:
            logger.warning(f"Model {ollama_model} nie jest dostępny")
            
            if not models:
                logger.info("Brak dostępnych modeli. Pobieranie modelu llama3...")
                os.system(f"docker exec -it ollama ollama pull llama3")
                
            if models:
                logger.info(f"Dostępne modele: {model_names}")
                ollama_model = models[0].get('name')
                logger.info(f"Używanie modelu {ollama_model}")
        
        # Test generowania tekstu za pomocą API chat
        prompt = "Powiedz 'Cześć, jestem botem Heyken!' po polsku"
        logger.info(f"Testowanie generowania tekstu (API chat) z promptem: {prompt}")
        
        response = generate_text(ollama_url, ollama_model, prompt)
        logger.info(f"Odpowiedź z API chat: {response}")
        
        # Test generowania tekstu za pomocą API generate
        logger.info(f"Testowanie generowania tekstu (API generate) z promptem: {prompt}")
        
        response_stream = generate_text_stream(ollama_url, ollama_model, prompt)
        logger.info(f"Odpowiedź z API generate: {response_stream}")
        
    except KeyboardInterrupt:
        logger.info("Test przerwany przez użytkownika")
    except Exception as e:
        logger.error(f"Błąd podczas testu: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
