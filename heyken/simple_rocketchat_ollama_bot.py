#!/usr/bin/env python3
"""
Prosty bot integrujący RocketChat z Ollama.
"""
import os
import sys
import json
import time
import logging
import requests
import re
from dotenv import load_dotenv

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

class RocketChatClient:
    """Klient do komunikacji z RocketChat."""
    
    def __init__(self, server_url, username, password):
        """
        Inicjalizuje klienta RocketChat.
        
        Args:
            server_url: URL serwera RocketChat
            username: Nazwa użytkownika
            password: Hasło
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth_token = None
        self.user_id = None
        self.headers = {}
        self.last_message_check = time.time()
        
    def login(self):
        """
        Loguje się do serwera RocketChat.
        
        Returns:
            bool: True jeśli logowanie się powiodło, False w przeciwnym przypadku
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/login",
                json={"user": self.username, "password": self.password}
            )
            
            if response.status_code == 200 and response.json().get("status") == "success":
                data = response.json().get("data", {})
                self.auth_token = data.get("authToken")
                self.user_id = data.get("userId")
                self.headers = {
                    "X-Auth-Token": self.auth_token,
                    "X-User-Id": self.user_id,
                    "Content-Type": "application/json"
                }
                logger.info(f"Zalogowano do RocketChat jako {self.username}")
                return True
            else:
                logger.error(f"Błąd logowania: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Wyjątek podczas logowania: {str(e)}")
            return False
            
    def send_message(self, room_id, text):
        """
        Wysyła wiadomość do pokoju.
        
        Args:
            room_id: ID pokoju
            text: Treść wiadomości
            
        Returns:
            bool: True jeśli wysłanie się powiodło, False w przeciwnym przypadku
        """
        if not self.auth_token or not self.user_id:
            logger.error("Nie zalogowano do RocketChat")
            return False
            
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/chat.postMessage",
                headers=self.headers,
                json={"roomId": room_id, "text": text}
            )
            
            if response.status_code == 200 and response.json().get("success"):
                logger.debug(f"Wysłano wiadomość do pokoju {room_id}")
                return True
            else:
                logger.error(f"Błąd wysyłania wiadomości: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Wyjątek podczas wysyłania wiadomości: {str(e)}")
            return False
            
    def get_new_messages(self):
        """
        Pobiera nowe wiadomości ze wszystkich pokojów.
        
        Returns:
            list: Lista nowych wiadomości
        """
        if not self.auth_token or not self.user_id:
            logger.error("Nie zalogowano do RocketChat")
            return []
            
        messages = []
        
        try:
            # Pobierz wiadomości bezpośrednie
            dm_response = requests.get(
                f"{self.server_url}/api/v1/im.list",
                headers=self.headers
            )
            
            if dm_response.status_code == 200 and dm_response.json().get("success"):
                direct_rooms = dm_response.json().get("ims", [])
                
                for room in direct_rooms:
                    room_messages = self._get_room_messages(room["_id"], "im.messages")
                    messages.extend(room_messages)
            
            # Pobierz wiadomości z kanałów
            channels_response = requests.get(
                f"{self.server_url}/api/v1/channels.list.joined",
                headers=self.headers
            )
            
            if channels_response.status_code == 200 and channels_response.json().get("success"):
                channels = channels_response.json().get("channels", [])
                
                for channel in channels:
                    room_messages = self._get_room_messages(channel["_id"], "channels.messages")
                    messages.extend(room_messages)
                    
            # Aktualizuj czas ostatniego sprawdzenia
            self.last_message_check = time.time()
            
            return messages
            
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania wiadomości: {str(e)}")
            return []
            
    def _get_room_messages(self, room_id, endpoint):
        """
        Pobiera wiadomości z pokoju.
        
        Args:
            room_id: ID pokoju
            endpoint: Endpoint API do pobrania wiadomości
            
        Returns:
            list: Lista wiadomości z pokoju
        """
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/{endpoint}",
                headers=self.headers,
                params={"roomId": room_id, "count": 50}
            )
            
            # Sprawdź, czy odpowiedź jest poprawnym JSON
            try:
                response_json = response.json()
            except json.JSONDecodeError:
                logger.error(f"Niepoprawna odpowiedź JSON z pokoju {room_id}: {response.text}")
                return []
                
            if response.status_code == 200 and response_json.get("success"):
                messages_data = response_json.get("messages", [])
                
                # Sprawdź, czy messages_data jest listą
                if not isinstance(messages_data, list):
                    logger.error(f"Niepoprawny format wiadomości z pokoju {room_id}: {messages_data}")
                    return []
                
                # Filtruj wiadomości nowsze niż ostatnie sprawdzenie i nie wysłane przez bota
                filtered_messages = []
                for msg in messages_data:
                    try:
                        # Sprawdź, czy msg jest słownikiem
                        if not isinstance(msg, dict):
                            continue
                            
                        # Pobierz timestamp
                        ts = msg.get("ts")
                        timestamp = 0
                        if isinstance(ts, dict) and "$date" in ts:
                            timestamp = ts["$date"] / 1000
                        
                        # Pobierz dane użytkownika
                        user = msg.get("u", {})
                        user_id = ""
                        username = ""
                        if isinstance(user, dict):
                            user_id = user.get("_id", "")
                            username = user.get("username", "")
                        
                        # Sprawdź, czy wiadomość jest nowsza niż ostatnie sprawdzenie i nie została wysłana przez bota
                        if timestamp > self.last_message_check and user_id != self.user_id:
                            filtered_messages.append({
                                "id": msg.get("_id", ""),
                                "room_id": msg.get("rid", ""),
                                "text": msg.get("msg", ""),
                                "sender_id": user_id,
                                "sender_username": username,
                                "timestamp": timestamp,
                                "is_direct": msg.get("t", "") == "d"
                            })
                    except Exception as e:
                        logger.error(f"Błąd przetwarzania wiadomości: {str(e)}")
                        continue
                
                return filtered_messages
            else:
                logger.error(f"Błąd pobierania wiadomości z pokoju {room_id}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania wiadomości z pokoju {room_id}: {str(e)}")
            return []


class OllamaClient:
    """Klient do komunikacji z Ollama."""
    
    def __init__(self, base_url, model):
        """
        Inicjalizuje klienta Ollama.
        
        Args:
            base_url: Bazowy URL API Ollama
            model: Nazwa modelu
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.is_connected = self.check_connection()
        
    def check_connection(self):
        """
        Sprawdza połączenie z API Ollama.
        
        Returns:
            bool: True jeśli połączenie jest dostępne, False w przeciwnym przypadku
        """
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get('name') for m in models]
                logger.info(f"Połączono z Ollama. Dostępne modele: {model_names}")
                
                # Sprawdź, czy wybrany model jest dostępny
                model_exists = any(m.get('name') == self.model for m in models)
                if not model_exists:
                    logger.warning(f"Model '{self.model}' nie jest dostępny w Ollama. Dostępne modele: {model_names}")
                    
                    # Jeśli model nie istnieje, ale są inne modele, użyj pierwszego dostępnego
                    if models:
                        self.model = models[0].get('name')
                        logger.info(f"Używanie modelu {self.model}")
                        
                return True
            else:
                logger.error(f"Błąd połączenia z Ollama: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Nie można połączyć się z Ollama pod adresem {self.base_url}: {str(e)}")
            return False
            
    def generate(self, prompt):
        """
        Generuje tekst za pomocą Ollama.
        
        Args:
            prompt: Prompt dla modelu
            
        Returns:
            str: Wygenerowany tekst
        """
        if not self.is_connected:
            logger.error("Nie można wygenerować tekstu: brak połączenia z Ollama")
            return "Przepraszam, nie mogę teraz odpowiedzieć. Brak połączenia z serwerem Ollama."
            
        try:
            # Użyjemy API /api/chat zamiast /api/generate, ponieważ jest bardziej niezawodne
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": self.model,
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
                    return "Przepraszam, wystąpił problem z przetwarzaniem odpowiedzi. Spróbuj ponownie później."
            else:
                logger.error(f"Błąd API Ollama: {response.status_code} - {response.text}")
                return f"Przepraszam, wystąpił błąd podczas generowania odpowiedzi (kod: {response.status_code})."
                
        except Exception as e:
            logger.error(f"Wyjątek podczas generowania tekstu: {str(e)}")
            return "Przepraszam, wystąpił nieoczekiwany błąd podczas przetwarzania Twojej wiadomości."


class SimpleBot:
    """Prosty bot integrujący RocketChat z Ollama."""
    
    def __init__(self, rocketchat_url, rocketchat_username, rocketchat_password, ollama_url, ollama_model):
        """
        Inicjalizuje bota.
        
        Args:
            rocketchat_url: URL serwera RocketChat
            rocketchat_username: Nazwa użytkownika bota w RocketChat
            rocketchat_password: Hasło bota w RocketChat
            ollama_url: URL serwera Ollama
            ollama_model: Nazwa modelu Ollama
        """
        self.rocketchat = RocketChatClient(rocketchat_url, rocketchat_username, rocketchat_password)
        self.ollama = OllamaClient(ollama_url, ollama_model)
        self.running = False
        
    def start(self, poll_interval=2.0):
        """
        Uruchamia bota.
        
        Args:
            poll_interval: Interwał sprawdzania nowych wiadomości w sekundach
        """
        if not self.rocketchat.login():
            logger.error("Nie można uruchomić bota - błąd logowania do RocketChat")
            return
            
        logger.info(f"Bot uruchomiony")
        self.running = True
        
        try:
            while self.running:
                self._process_messages()
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            logger.info("Bot zatrzymany przez użytkownika")
        except Exception as e:
            logger.error(f"Błąd podczas działania bota: {str(e)}")
        finally:
            self.running = False
            
    def stop(self):
        """Zatrzymuje bota."""
        self.running = False
        logger.info("Bot zatrzymany")
        
    def _process_messages(self):
        """Przetwarza nowe wiadomości i wysyła odpowiedzi."""
        messages = self.rocketchat.get_new_messages()
        
        for message in messages:
            # Ignoruj wiadomości od bota
            if message["sender_username"] == self.rocketchat.username:
                continue
                
            logger.info(f"Nowa wiadomość od {message['sender_username']}: {message['text']}")
            
            # Sprawdź, czy wiadomość jest skierowana do bota
            is_direct_mention = f"@{self.rocketchat.username}" in message["text"]
            is_direct_message = message["is_direct"]
            
            if not is_direct_mention and not is_direct_message:
                continue
                
            # Usuń wzmiankę o bocie z treści wiadomości
            clean_text = message["text"].replace(f"@{self.rocketchat.username}", "").strip()
            
            # Obsługa komend
            if clean_text.lower() == "pomoc" or clean_text.lower() == "help":
                self._handle_help(message)
            else:
                self._handle_chat(message, clean_text)
                
    def _handle_help(self, message):
        """
        Obsługuje komendę pomocy.
        
        Args:
            message: Wiadomość z RocketChat
        """
        help_text = """# Pomoc Heyken Bot

## Dostępne komendy:
- **pomoc** - wyświetla tę pomoc
- **Zadaj dowolne pytanie** - bot odpowie używając modelu Ollama

## Przykłady:
- Jak działa silnik spalinowy?
- Napisz prosty program w Pythonie do sortowania listy
- Wytłumacz mi koncepcję sztucznej inteligencji
"""
        self.rocketchat.send_message(message["room_id"], help_text)
        
    def _handle_chat(self, message, text):
        """
        Obsługuje wiadomość czatu.
        
        Args:
            message: Wiadomość z RocketChat
            text: Treść wiadomości
        """
        try:
            # Generowanie odpowiedzi za pomocą Ollama
            prompt = f"""
            Użytkownik {message['sender_username']} napisał:
            {text}
            
            Odpowiedz krótko i pomocnie. Jeśli użytkownik pyta o funkcje bota,
            zasugeruj użycie komendy 'pomoc' w celu uzyskania listy dostępnych komend.
            """
            
            response = self.ollama.generate(prompt)
            self.rocketchat.send_message(message["room_id"], response)
        except Exception as e:
            logger.error(f"Błąd podczas generowania odpowiedzi: {str(e)}")
            self.rocketchat.send_message(
                message["room_id"],
                "Przepraszam, wystąpił błąd podczas przetwarzania Twojej wiadomości."
            )


def main():
    """Główna funkcja uruchamiająca bota."""
    try:
        # Wczytanie zmiennych środowiskowych
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
        if os.path.exists(env_path):
            logger.info(f"Wczytywanie zmiennych środowiskowych z {env_path}")
            load_dotenv(env_path)
        else:
            logger.warning("Nie znaleziono pliku .env, używanie domyślnych wartości")
            
        # Konfiguracja RocketChat
        rocketchat_url = os.getenv("ROCKETCHAT_URL", "http://localhost:3100")
        rocketchat_username = os.getenv("ROCKETCHAT_BOT_USERNAME", "heyken_bot")
        rocketchat_password = os.getenv("ROCKETCHAT_BOT_PASSWORD", "heyken123")
        
        # Konfiguracja Ollama
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        logger.info(f"RocketChat URL: {rocketchat_url}")
        logger.info(f"RocketChat Bot: {rocketchat_username}")
        logger.info(f"Ollama URL: {ollama_url}")
        logger.info(f"Ollama Model: {ollama_model}")
        
        # Utworzenie i uruchomienie bota
        bot = SimpleBot(rocketchat_url, rocketchat_username, rocketchat_password, ollama_url, ollama_model)
        bot.start()
        
    except KeyboardInterrupt:
        logger.info("Bot zatrzymany przez użytkownika")
    except Exception as e:
        logger.error(f"Błąd podczas uruchamiania bota: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
