"""
Klient RocketChat do komunikacji z serwerem.
"""
from typing import Dict, List, Optional, Any
import requests
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Reprezentacja wiadomości w RocketChat."""
    id: str
    room_id: str
    text: str
    sender_id: str
    sender_username: str
    timestamp: float
    is_direct: bool = False
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "Message":
        """Tworzy obiekt Message z odpowiedzi API RocketChat."""
        return cls(
            id=data.get("_id", ""),
            room_id=data.get("rid", ""),
            text=data.get("msg", ""),
            sender_id=data.get("u", {}).get("_id", ""),
            sender_username=data.get("u", {}).get("username", ""),
            timestamp=data.get("ts", {}).get("$date", time.time() * 1000) / 1000,
            is_direct=data.get("t", "") == "d"
        )


class RocketChatClient:
    """
    Klient do komunikacji z API RocketChat.
    
    Umożliwia logowanie, wysyłanie i odbieranie wiadomości oraz zarządzanie pokojami.
    """
    
    def __init__(self, server_url: str, username: str, password: str):
        """
        Inicjalizuje klienta RocketChat.
        
        Args:
            server_url: URL serwera RocketChat (np. http://localhost:3100)
            username: Nazwa użytkownika bota
            password: Hasło użytkownika bota
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.auth_token = None
        self.user_id = None
        self.headers = {}
        self.last_message_check = time.time()
        
    def login(self) -> bool:
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
            
    def send_message(self, room_id: str, text: str) -> bool:
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
            
    def get_new_messages(self, room_id: Optional[str] = None) -> List[Message]:
        """
        Pobiera nowe wiadomości z pokoju lub ze wszystkich pokojów.
        
        Args:
            room_id: Opcjonalne ID pokoju. Jeśli nie podano, pobiera wiadomości ze wszystkich pokojów.
            
        Returns:
            List[Message]: Lista nowych wiadomości
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
                    if room_id and room["_id"] != room_id:
                        continue
                        
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
                    if room_id and channel["_id"] != room_id:
                        continue
                        
                    room_messages = self._get_room_messages(channel["_id"], "channels.messages")
                    messages.extend(room_messages)
                    
            # Aktualizuj czas ostatniego sprawdzenia
            self.last_message_check = time.time()
            
            return messages
            
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania wiadomości: {str(e)}")
            return []
            
    def _get_room_messages(self, room_id: str, endpoint: str) -> List[Message]:
        """
        Pobiera wiadomości z pokoju.
        
        Args:
            room_id: ID pokoju
            endpoint: Endpoint API do pobrania wiadomości
            
        Returns:
            List[Message]: Lista wiadomości z pokoju
        """
        try:
            response = requests.get(
                f"{self.server_url}/api/v1/{endpoint}",
                headers=self.headers,
                params={"roomId": room_id, "count": 50}
            )
            
            if response.status_code == 200 and response.json().get("success"):
                messages_data = response.json().get("messages", [])
                
                # Filtruj wiadomości nowsze niż ostatnie sprawdzenie i nie wysłane przez bota
                filtered_messages = [
                    Message.from_api_response(msg) for msg in messages_data
                    if msg.get("ts", {}).get("$date", 0) / 1000 > self.last_message_check
                    and msg.get("u", {}).get("_id") != self.user_id
                ]
                
                return filtered_messages
            else:
                logger.error(f"Błąd pobierania wiadomości z pokoju {room_id}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania wiadomości z pokoju {room_id}: {str(e)}")
            return []
            
    def get_rooms(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Pobiera listę pokojów, w których jest bot.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Słownik z listami pokojów
        """
        if not self.auth_token or not self.user_id:
            logger.error("Nie zalogowano do RocketChat")
            return {"direct": [], "channels": []}
            
        rooms = {"direct": [], "channels": []}
        
        try:
            # Pobierz wiadomości bezpośrednie
            dm_response = requests.get(
                f"{self.server_url}/api/v1/im.list",
                headers=self.headers
            )
            
            if dm_response.status_code == 200 and dm_response.json().get("success"):
                rooms["direct"] = dm_response.json().get("ims", [])
            
            # Pobierz kanały
            channels_response = requests.get(
                f"{self.server_url}/api/v1/channels.list.joined",
                headers=self.headers
            )
            
            if channels_response.status_code == 200 and channels_response.json().get("success"):
                rooms["channels"] = channels_response.json().get("channels", [])
                
            return rooms
            
        except Exception as e:
            logger.error(f"Wyjątek podczas pobierania pokojów: {str(e)}")
            return {"direct": [], "channels": []}
