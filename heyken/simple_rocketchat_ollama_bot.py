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

class RocketChatLogHandler(logging.Handler):
    """Custom logging handler that sends logs to RocketChat channels."""
    
    def __init__(self, server_url, username, password, channel_names=["heyken-logs", "logs"]):
        """
        Initialize the RocketChat log handler.
        
        Args:
            server_url: URL of the RocketChat server
            username: Username for authentication
            password: Password for authentication
            channel_names: List of channel names to send logs to
        """
        super().__init__()
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.channel_names = channel_names if isinstance(channel_names, list) else [channel_names]
        self.auth_token = None
        self.user_id = None
        self.channel_ids = {}  # Dictionary of channel_name -> channel_id
        self.headers = {}
        self.initialized = False
        self.login_attempts = 0
        self.max_login_attempts = 5
        self.buffer = []  # Buffer for logs before initialization
        
    def initialize(self):
        """Initialize the handler by logging in and finding the channel IDs."""
        if self.initialized or self.login_attempts >= self.max_login_attempts:
            return self.initialized
            
        self.login_attempts += 1
        
        try:
            # Login to RocketChat
            response = requests.post(
                f"{self.server_url}/api/v1/login",
                json={"user": self.username, "password": self.password}
            )
            
            if response.status_code != 200 or response.json().get("status") != "success":
                print(f"RocketChatLogHandler: Login failed: {response.text}")
                return False
                
            data = response.json().get("data", {})
            self.auth_token = data.get("authToken")
            self.user_id = data.get("userId")
            self.headers = {
                "X-Auth-Token": self.auth_token,
                "X-User-Id": self.user_id,
                "Content-Type": "application/json"
            }
            
            # Find all channel IDs
            response = requests.get(
                f"{self.server_url}/api/v1/channels.list",
                headers=self.headers
            )
            
            if response.status_code != 200 or not response.json().get("success"):
                print(f"RocketChatLogHandler: Failed to get channels: {response.text}")
                return False
                
            channels = response.json().get("channels", [])
            
            # Process each channel in our list
            for channel_name in self.channel_names:
                channel_found = False
                
                # Look for the channel in the list
                for channel in channels:
                    if channel.get("name") == channel_name:
                        self.channel_ids[channel_name] = channel.get("_id")
                        channel_found = True
                        print(f"RocketChatLogHandler: Found channel '{channel_name}'")
                        break
                
                # If channel not found, try to create it
                if not channel_found:
                    print(f"RocketChatLogHandler: Channel '{channel_name}' not found, creating...")
                    try:
                        response = requests.post(
                            f"{self.server_url}/api/v1/channels.create",
                            headers=self.headers,
                            json={"name": channel_name}
                        )
                        if response.status_code == 200 and response.json().get("success"):
                            self.channel_ids[channel_name] = response.json().get("channel", {}).get("_id")
                            print(f"RocketChatLogHandler: Created channel '{channel_name}'")
                        else:
                            print(f"RocketChatLogHandler: Failed to create channel '{channel_name}': {response.text}")
                    except Exception as e:
                        print(f"RocketChatLogHandler: Error creating channel '{channel_name}': {str(e)}")
            
            # Process any buffered logs
            if self.buffer:
                print(f"RocketChatLogHandler: Processing {len(self.buffer)} buffered logs")
                for record in self.buffer:
                    self.emit(record)
                self.buffer = []
                
            self.initialized = True
            return True
            
        except Exception as e:
            print(f"RocketChatLogHandler: Initialization error: {str(e)}")
            return False
            
    def emit(self, record):
        """Send the log record to all configured RocketChat channels."""
        if not self.initialized:
            # Buffer the log until we're initialized
            self.buffer.append(record)
            if not self.initialize():
                return
                
        try:
            log_message = self.format(record)
            
            # Send to each channel
            for channel_name, channel_id in self.channel_ids.items():
                try:
                    response = requests.post(
                        f"{self.server_url}/api/v1/chat.postMessage",
                        headers=self.headers,
                        json={
                            "channel": f"#{channel_name}",
                            "text": log_message
                        }
                    )
                    
                    if response.status_code != 200 or not response.json().get("success"):
                        # If sending fails, try to re-initialize and send again
                        if "You must be logged in" in response.text:
                            self.initialized = False
                            if self.initialize():
                                self.emit(record)
                        else:
                            print(f"RocketChatLogHandler: Failed to send log to channel '{channel_name}': {response.text}")
                            
                except Exception as e:
                    print(f"RocketChatLogHandler: Error sending log to channel '{channel_name}': {str(e)}")
                    
        except Exception as e:
            print(f"RocketChatLogHandler: Error in emit: {str(e)}")


# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
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
        self.headers = None
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
            
            if response.status_code != 200 or response.json().get("status") != "success":
                logger.error(f"Błąd logowania do RocketChat: {response.text}")
                return False
                
            data = response.json().get("data", {})
            self.auth_token = data.get("authToken")
            self.user_id = data.get("userId")
            self.headers = {
                "X-Auth-Token": self.auth_token,
                "X-User-Id": self.user_id,
                "Content-Type": "application/json"
            }
            
            logger.info(f"Zalogowano do RocketChat jako {self.username} (ID: {self.user_id})")
            
            # Ustaw status jako online
            if not self.set_status_online():
                logger.warning("Nie udało się ustawić statusu jako online")
                
            return True
            
        except Exception as e:
            logger.error(f"Wyjątek podczas logowania do RocketChat: {str(e)}")
            return False
            
    def set_status_online(self):
        """
        Ustawia status użytkownika jako online.
        
        Returns:
            bool: True jeśli ustawienie statusu się powiodło, False w przeciwnym przypadku
        """
        try:
            # Ustaw status jako online bez dodatkowego komunikatu
            status_response = requests.post(
                f"{self.server_url}/api/v1/users.setStatus",
                headers=self.headers,
                json={
                    "status": "online",
                    "message": ""
                }
            )
            
            if status_response.status_code != 200 or not status_response.json().get("success"):
                logger.error(f"Błąd ustawiania statusu: {status_response.text}")
                return False
                
            logger.info("Status ustawiony jako online")
            return True
            
        except Exception as e:
            logger.error(f"Wyjątek podczas ustawiania statusu: {str(e)}")
            return False
            
    def set_status_busy(self, message="Jestem zajęty przetwarzaniem zapytania..."):
        """
        Ustawia status użytkownika jako zajęty.
        
        Args:
            message: Wiadomość statusu
            
        Returns:
            bool: True jeśli ustawienie statusu się powiodło, False w przeciwnym przypadku
        """
        try:
            # Ustaw status jako zajęty
            status_response = requests.post(
                f"{self.server_url}/api/v1/users.setStatus",
                headers=self.headers,
                json={
                    "status": "busy",
                    "message": message
                }
            )
            
            if status_response.status_code != 200 or not status_response.json().get("success"):
                logger.error(f"Błąd ustawiania statusu zajęty: {status_response.text}")
                return False
                
            logger.info(f"Status ustawiony jako zajęty: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Wyjątek podczas ustawiania statusu zajęty: {str(e)}")
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
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/chat.postMessage",
                headers=self.headers,
                json={"roomId": room_id, "text": text}
            )
            
            if response.status_code != 200 or not response.json().get("success"):
                logger.error(f"Błąd wysyłania wiadomości: {response.text}")
                return False
                
            logger.info(f"Wysłano wiadomość do pokoju {room_id}")
            return True
            
        except Exception as e:
            logger.error(f"Wyjątek podczas wysyłania wiadomości: {str(e)}")
            return False
            
    def get_new_messages(self):
        """
        Pobiera nowe wiadomości ze wszystkich pokojów.
        
        Returns:
            list: Lista nowych wiadomości
        """
        try:
            # Pobierz wiadomości z DM
            logger.info("Pobieranie wiadomości z DM...")
            dm_response = requests.get(
                f"{self.server_url}/api/v1/im.list",
                headers=self.headers
            )
            
            if dm_response.status_code != 200 or not dm_response.json().get("success"):
                logger.error(f"Błąd pobierania listy DM: {dm_response.text}")
                return []
                
            dm_rooms = dm_response.json().get("ims", [])
            logger.info(f"Znaleziono {len(dm_rooms)} pokojów DM")
            
            # Pobierz wiadomości z kanałów
            logger.info("Pobieranie wiadomości z kanałów...")
            channels_response = requests.get(
                f"{self.server_url}/api/v1/channels.list",
                headers=self.headers
            )
            
            if channels_response.status_code != 200 or not channels_response.json().get("success"):
                logger.error(f"Błąd pobierania listy kanałów: {channels_response.text}")
                return []
                
            channels = channels_response.json().get("channels", [])
            logger.info(f"Znaleziono {len(channels)} kanałów")
            
            # Zbierz wszystkie wiadomości
            all_messages = []
            
            # Pobierz wiadomości z DM
            for room in dm_rooms:
                room_id = room.get("_id")
                messages = self._get_room_messages(room_id, "im.messages")
                all_messages.extend(messages)
                
            # Pobierz wiadomości z kanałów
            for channel in channels:
                channel_id = channel.get("_id")
                messages = self._get_room_messages(channel_id, "channels.messages")
                all_messages.extend(messages)
                
            # Aktualizuj czas ostatniego sprawdzenia
            self.last_message_check = time.time()
            
            return all_messages
            
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania nowych wiadomości: {str(e)}")
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
                logger.info(f"Otrzymano odpowiedź z API dla pokoju {room_id}, status: {response.status_code}")
            except json.JSONDecodeError:
                logger.error(f"Niepoprawna odpowiedź JSON z pokoju {room_id}: {response.text}")
                return []
                
            if response.status_code == 200 and response_json.get("success"):
                messages_data = response_json.get("messages", [])
                logger.info(f"Otrzymano {len(messages_data)} wiadomości z pokoju {room_id}")
                
                # Sprawdź, czy messages_data jest listą
                if not isinstance(messages_data, list):
                    logger.error(f"Niepoprawny format wiadomości z pokoju {room_id}: {messages_data}")
                    return []
                
                # Filtruj wiadomości nowsze niż ostatnie sprawdzenie i nie wysłane przez bota
                filtered_messages = []
                logger.info(f"Filtrowanie wiadomości nowszych niż {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_message_check))}")
                logger.info(f"ID bota: {self.user_id}")
                for msg in messages_data:
                    try:
                        # Sprawdź, czy msg jest słownikiem
                        if not isinstance(msg, dict):
                            continue
                            
                        # Pobierz timestamp
                        ts = msg.get("ts")
                        timestamp = 0
                        
                        # Dodaj debug info o typie i zawartości ts
                        logger.info(f"Timestamp type: {type(ts)}, value: {ts}")
                        
                        # Obsługa różnych formatów timestampów
                        if isinstance(ts, dict) and "$date" in ts:
                            timestamp = ts["$date"] / 1000
                        elif isinstance(ts, str):
                            # Spróbuj przetworzyć string jako ISO format
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                                timestamp = dt.timestamp()
                            except Exception as e:
                                logger.error(f"Nie można przetworzyć timestampu jako string: {e}")
                        
                        # Ustaw timestamp na aktualny czas, jeśli nie udało się go przetworzyć
                        if timestamp == 0:
                            timestamp = time.time()
                            
                        # Pobierz dane użytkownika
                        user = msg.get("u", {})
                        user_id = ""
                        username = ""
                        if isinstance(user, dict):
                            user_id = user.get("_id", "")
                            username = user.get("username", "")
                        
                        # Sprawdź, czy wiadomość nie została wysłana przez bota
                        msg_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                        logger.info(f"Sprawdzanie wiadomości: ID={msg.get('_id', '')}, czas={msg_time}, użytkownik={username}")
                        
                        # Odpowiadaj na wszystkie wiadomości, niezależnie od czasu
                        if user_id != self.user_id:
                            logger.info(f"Znaleziono wiadomość od {username}: {msg.get('msg', '')}")
                            filtered_messages.append({
                                "id": msg.get("_id", ""),
                                "room_id": msg.get("rid", ""),
                                "text": msg.get("msg", ""),
                                "sender_id": user_id,
                                "sender_username": username,
                                "timestamp": timestamp,
                                "is_direct": msg.get("t", "") == "d"
                            })
                        else:
                            logger.info(f"Pominięto wiadomość - wysłana przez bota")
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
        
    def check_connection(self):
        """
        Sprawdza połączenie z API Ollama.
        
        Returns:
            bool: True jeśli połączenie jest dostępne, False w przeciwnym przypadku
        """
        try:
            # Sprawdź dostępność API
            response = requests.get(f"{self.base_url}/api/tags")
            
            if response.status_code != 200:
                logger.error(f"Błąd połączenia z API Ollama: {response.status_code}")
                return False
                
            # Sprawdź, czy model jest dostępny
            models = response.json().get("models", [])
            model_available = False
            
            for model_info in models:
                if model_info.get("name") == self.model:
                    model_available = True
                    break
                    
            if not model_available:
                logger.warning(f"Model {self.model} nie jest dostępny w Ollama")
                logger.info("Dostępne modele:")
                for model_info in models:
                    logger.info(f"- {model_info.get('name')}")
                    
                # Spróbuj pobrać model, jeśli nie jest dostępny
                logger.info(f"Próba pobrania modelu {self.model}...")
                pull_response = requests.post(
                    f"{self.base_url}/api/pull",
                    json={"name": self.model}
                )
                
                if pull_response.status_code != 200:
                    logger.error(f"Błąd pobierania modelu {self.model}: {pull_response.text}")
                    return False
                    
                logger.info(f"Model {self.model} został pobrany")
                
            return True
            
        except Exception as e:
            logger.error(f"Wyjątek podczas sprawdzania połączenia z Ollama: {str(e)}")
            return False
            
    def generate(self, prompt):
        """
        Generuje tekst za pomocą Ollama.
        
        Args:
            prompt: Prompt dla modelu
            
        Returns:
            str: Wygenerowany tekst
        """
        try:
            logger.info(f"Generowanie odpowiedzi dla promptu: {prompt[:50]}...")
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_predict": 256
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Błąd generowania tekstu: {response.text}")
                return "Przepraszam, wystąpił błąd podczas generowania odpowiedzi."
                
            response_data = response.json()
            generated_text = response_data.get("response", "")
            
            # Usuń niepotrzebne znaki nowej linii na początku i końcu
            generated_text = generated_text.strip()
            
            # Usuń powtarzające się znaki nowej linii
            generated_text = re.sub(r'\n{3,}', '\n\n', generated_text)
            
            logger.info(f"Wygenerowano odpowiedź o długości {len(generated_text)} znaków")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Wyjątek podczas generowania tekstu: {str(e)}")
            return "Przepraszam, wystąpił błąd podczas generowania odpowiedzi."


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
        self.answered_messages = set()  # Zbiór ID wiadomości, na które już odpowiedziano
        self.processing = False  # Flaga wskazująca, czy bot przetwarza obecnie wiadomość
        self.last_message_id = None  # ID ostatniej przetworzonej wiadomości
        
    def start(self, poll_interval=2.0):
        """
        Uruchamia bota.
        
        Args:
            poll_interval: Interwał sprawdzania nowych wiadomości w sekundach
        """
        # Logowanie do RocketChat
        if not self.rocketchat.login():
            logger.error("Nie udało się zalogować do RocketChat")
            return
            
        # Sprawdzenie połączenia z Ollama
        if not self.ollama.check_connection():
            logger.error("Nie udało się połączyć z Ollama")
            return
            
        logger.info("Bot uruchomiony")
        self.running = True
        
        # Licznik do odświeżania statusu
        status_refresh_counter = 0
        
        # Główna pętla bota
        while self.running:
            # Odśwież status co 30 cykli (około 1 minuty przy poll_interval=2.0)
            status_refresh_counter += 1
            if status_refresh_counter >= 30:
                logger.info("Odświeżanie statusu bota...")
                self.rocketchat.set_status_online()
                status_refresh_counter = 0
                
            # Przetwarzaj wiadomości
            self._process_messages()
            time.sleep(poll_interval)
            
    def stop(self):
        """Zatrzymuje bota."""
        self.running = False
        logger.info("Bot zatrzymany")
        
    def _process_messages(self):
        """Przetwarza nowe wiadomości i wysyła odpowiedzi."""
        try:
            logger.info("Rozpoczynam przetwarzanie wiadomości...")
            messages = self.rocketchat.get_new_messages()
            logger.info(f"Znaleziono {len(messages)} nowych wiadomości")
            
            if len(messages) > 0:
                logger.info(f"Szczegóły pierwszej wiadomości: {messages[0]}")
                
                # Wymuś odświeżenie statusu przy nowych wiadomościach
                logger.info("Odświeżanie statusu bota po znalezieniu nowych wiadomości...")
                self.rocketchat.set_status_online()
            
            # Sortuj wiadomości według czasu, aby przetwarzać je chronologicznie
            messages.sort(key=lambda x: x.get("timestamp", 0))
            
            for i, message in enumerate(messages):
                message_id = message.get("id", "")
                logger.info(f"Przetwarzanie wiadomości {i+1} z {len(messages)}, ID: {message_id}")
                
                # Sprawdź, czy już odpowiedzieliśmy na tę wiadomość
                if message_id in self.answered_messages:
                    logger.info(f"Pomijam wiadomość {message_id} - już na nią odpowiedziano")
                    continue
                
                text = message.get("text", "").strip()
                logger.info(f"Treść wiadomości: '{text}'")
                
                # Sprawdź, czy wiadomość jest skierowana do bota
                is_direct_message = message.get("is_direct", False)
                is_direct_mention = text.lower().startswith(f"@{self.rocketchat.username.lower()}")
                
                # Odpowiadaj na wszystkie wiadomości, niezależnie od typu
                logger.info(f"Przetwarzanie wiadomości: {text[:50]}...")
                logger.info(f"Wiadomość bezpośrednia: {is_direct_message}, Bezpośrednie wspomnienie: {is_direct_mention}")
                logger.info(f"Dane wiadomości: room_id={message.get('room_id')}, sender={message.get('sender_username')}")
                
                # Sprawdź, czy room_id jest poprawny
                if not message.get('room_id'):
                    logger.error(f"Brak room_id w wiadomości: {message}")
                    continue
                
                # Sprawdź, czy to jest ostatnia wiadomość
                is_last_message = (i == len(messages) - 1)
                
                # Obsługa komend
                if text.lower() == "pomoc" or text.lower() == "help":
                    logger.info("Obsługa komendy pomocy")
                    self._handle_help(message)
                elif text.lower() == "status":
                    logger.info("Obsługa komendy status")
                    self.rocketchat.send_message(message["room_id"], "Bot jest aktywny i działa poprawnie!")
                    self.rocketchat.set_status_online()
                elif text.lower() == "ping":
                    logger.info("Obsługa komendy ping")
                    self.rocketchat.send_message(message["room_id"], "Pong! Bot działa poprawnie.")
                else:
                    logger.info("Obsługa wiadomości czatu")
                    self._handle_chat(message, text, is_last_message)
                
                # Dodaj wiadomość do zbioru odpowiedzianych
                self.answered_messages.add(message_id)
                self.last_message_id = message_id
                    
        except Exception as e:
            logger.error(f"Błąd podczas przetwarzania wiadomości: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
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
        
    def _handle_chat(self, message, text, is_last_message=True):
        """
        Obsługuje wiadomość czatu.
        
        Args:
            message: Wiadomość z RocketChat
            text: Treść wiadomości
            is_last_message: Czy to jest ostatnia wiadomość w kolejce
        """
        try:
            logger.info(f"Rozpoczynam generowanie odpowiedzi na wiadomość: '{text}'")
            logger.info(f"Dane wiadomości: room_id={message.get('room_id')}, sender={message.get('sender_username')}")
            logger.info(f"Czy to ostatnia wiadomość: {is_last_message}")
            
            # Oszacuj czas odpowiedzi na podstawie długości tekstu i aktualnego obciążenia
            text_length = len(text)
            estimated_time = self._estimate_response_time(text_length)
            
            # Pobierz pierwsze 50 znaków tekstu (lub mniej, jeśli tekst jest krótszy)
            task_preview = text[:50] + "..." if len(text) > 50 else text
            
            # Ustaw status na zajęty z informacją o zadaniu
            self.rocketchat.set_status_busy(f"Jeszcze [{estimated_time}]s zajmie mi: {task_preview}")
            
            # Przygotuj wiadomość z informacją o czasie odpowiedzi
            quoted_text = text.replace('\n', '\n> ')
            processing_message = f"**Przetwarzam pytanie:** \
> {quoted_text}\n\nSzacowany czas odpowiedzi: około {estimated_time} sekund."
            
            # Wyślij wiadomość o rozpoczęciu przetwarzania
            logger.info(f"Wysyłam informację o rozpoczęciu przetwarzania, szacowany czas: {estimated_time} sekund")
            self.rocketchat.send_message(message["room_id"], processing_message)
            
            # Zapisz czas rozpoczęcia i szacowany czas zakończenia
            start_time = time.time()
            end_time = start_time + estimated_time
            
            # Uruchom wątek aktualizacji statusu
            import threading
            status_thread = threading.Thread(
                target=self._update_status_thread,
                args=(task_preview, end_time),
                daemon=True
            )
            status_thread.start()
            
            # Generowanie odpowiedzi za pomocą Ollama
            prompt = f"""
            Użytkownik {message['sender_username']} napisał:
            {text}
            
            Odpowiedz krótko i pomocnie. Jeśli użytkownik pyta o funkcje bota,
            zasugeruj użycie komendy 'pomoc' w celu uzyskania listy dostępnych komend.
            """
            
            logger.info(f"Wysyłam prompt do Ollama: {prompt[:100]}...")
            logger.info(f"URL Ollama: {self.ollama.base_url}, Model: {self.ollama.model}")
            
            # Ustaw flagę, że przetwarzanie jest w toku
            self.processing = True
            
            response = self.ollama.generate(prompt)
            
            # Ustaw flagę, że przetwarzanie zostało zakończone
            self.processing = False
            
            # Oblicz rzeczywisty czas przetwarzania
            processing_time = time.time() - start_time
            logger.info(f"Rzeczywisty czas przetwarzania: {processing_time:.2f} sekund")
            
            logger.info(f"Otrzymano odpowiedź od Ollama o długości {len(response)} znaków")
            logger.info(f"Początek odpowiedzi: {response[:100]}...")
            
            # Jeśli to nie jest odpowiedź na ostatnią wiadomość, dodaj cytat
            final_response = response
            if not is_last_message:
                # Dodaj cytat z oryginalnej wiadomości
                quoted_text = text.replace('\n', '\n> ')
                final_response = f"**W odpowiedzi na:** _{message['sender_username']}:_ \
> {quoted_text}\n\n{response}"
                logger.info("Dodano cytat do odpowiedzi, ponieważ to nie jest ostatnia wiadomość")
            
            logger.info(f"Wysyłam odpowiedź do pokoju {message['room_id']}")
            result = self.rocketchat.send_message(message["room_id"], final_response)
            logger.info(f"Wynik wysyłania wiadomości: {result}")
            
            # Przywróć status na online
            self.rocketchat.set_status_online()
            
        except Exception as e:
            logger.error(f"Błąd podczas generowania odpowiedzi: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            try:
                self.rocketchat.send_message(
                    message["room_id"],
                    "Przepraszam, wystąpił błąd podczas przetwarzania Twojej wiadomości."
                )
                # Przywróć status na online w przypadku błędu
                self.processing = False
                self.rocketchat.set_status_online()
            except Exception as e2:
                logger.error(f"Błąd podczas wysyłania wiadomości o błędzie: {str(e2)}")
                logger.error(traceback.format_exc())
                
    def _estimate_response_time(self, text_length):
        """
        Szacuje czas odpowiedzi na podstawie długości tekstu i aktualnego obciążenia.
        
        Args:
            text_length: Długość tekstu zapytania
            
        Returns:
            int: Szacowany czas odpowiedzi w sekundach
        """
        # Podstawowy czas przetwarzania
        base_time = 5
        
        # Dodatkowy czas w zależności od długości tekstu
        # Załóżmy, że każde 100 znaków dodaje 2 sekundy
        length_factor = text_length // 100 * 2
        
        # Sprawdź obciążenie systemu
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            
            # Dodatkowy czas w zależności od obciążenia CPU i pamięci
            # Jeśli CPU lub pamięć są mocno obciążone, dodaj więcej czasu
            system_factor = (cpu_usage + memory_usage) // 20  # Dzielimy przez 20, aby uzyskać sensowną wartość
        except ImportError:
            # Jeśli nie można zaimportować psutil, użyj domyślnej wartości
            system_factor = 2
            
        # Oblicz całkowity szacowany czas
        estimated_time = base_time + length_factor + system_factor
        
        # Dodaj losowy czynnik, aby uniknąć zbyt precyzyjnych szacunków
        import random
        random_factor = random.randint(-2, 2)
        estimated_time += random_factor
        
        # Upewnij się, że szacowany czas jest co najmniej 3 sekundy
        return max(3, estimated_time)


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
        
        # Konfiguracja loggera do wysyłania logów do RocketChat
        rocketchat_log_handler = RocketChatLogHandler(
            server_url=rocketchat_url,
            username=rocketchat_username,
            password=rocketchat_password,
            channel_names=["heyken-logs", "logs"]
        )
        
        # Ustaw format wiadomości dla handlera RocketChat
        rocketchat_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        rocketchat_log_handler.setLevel(logging.INFO)
        
        # Dodaj handler do loggera
        logger.addHandler(rocketchat_log_handler)
        
        # Inicjalizacja handlera RocketChat
        if rocketchat_log_handler.initialize():
            logger.info("RocketChat log handler zainicjalizowany pomyślnie")
        else:
            logger.warning("Nie udało się zainicjalizować RocketChat log handler, logi nie będą wysyłane do kanału")
        
        logger.info(f"RocketChat URL: {rocketchat_url}")
        logger.info(f"RocketChat Bot: {rocketchat_username}")
        logger.info(f"Ollama URL: {ollama_url}")
        logger.info(f"Ollama Model: {ollama_model}")
        logger.info("Logi są wysyłane do kanałów #heyken-logs i #logs w RocketChat")
        
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
