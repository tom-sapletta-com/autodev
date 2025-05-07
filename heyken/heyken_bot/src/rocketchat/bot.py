"""
Bot RocketChat do automatycznej obsługi wiadomości.
"""
import time
import logging
import re
from typing import Callable, Dict, List, Optional, Any, Union
from .client import RocketChatClient, Message

logger = logging.getLogger(__name__)

class RocketChatBot:
    """
    Bot RocketChat do automatycznej obsługi wiadomości.
    
    Umożliwia rejestrowanie funkcji obsługujących różne typy wiadomości
    i automatyczne odpowiadanie na wiadomości.
    """
    
    def __init__(
        self, 
        server_url: str, 
        username: str, 
        password: str,
        poll_interval: float = 2.0
    ):
        """
        Inicjalizuje bota RocketChat.
        
        Args:
            server_url: URL serwera RocketChat (np. http://localhost:3100)
            username: Nazwa użytkownika bota
            password: Hasło użytkownika bota
            poll_interval: Interwał sprawdzania nowych wiadomości w sekundach
        """
        self.client = RocketChatClient(server_url, username, password)
        self.username = username
        self.poll_interval = poll_interval
        self.handlers: Dict[str, Callable[[Message], Optional[str]]] = {}
        self.default_handler: Optional[Callable[[Message], Optional[str]]] = None
        self.running = False
        
    def start(self) -> None:
        """
        Uruchamia bota i rozpoczyna nasłuchiwanie wiadomości.
        """
        if not self.client.login():
            logger.error("Nie można uruchomić bota - błąd logowania")
            return
            
        logger.info(f"Bot {self.username} uruchomiony")
        self.running = True
        
        try:
            while self.running:
                self._process_messages()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Bot zatrzymany przez użytkownika")
        except Exception as e:
            logger.error(f"Błąd podczas działania bota: {str(e)}")
        finally:
            self.running = False
            
    def stop(self) -> None:
        """
        Zatrzymuje bota.
        """
        self.running = False
        logger.info(f"Bot {self.username} zatrzymany")
        
    def _process_messages(self) -> None:
        """
        Przetwarza nowe wiadomości i wywołuje odpowiednie handlery.
        """
        messages = self.client.get_new_messages()
        
        for message in messages:
            # Ignoruj wiadomości od bota
            if message.sender_username == self.username:
                continue
                
            logger.info(f"Nowa wiadomość od {message.sender_username}: {message.text}")
            
            # Sprawdź, czy wiadomość jest skierowana do bota
            is_direct_mention = f"@{self.username}" in message.text
            is_direct_message = message.is_direct
            
            if not is_direct_mention and not is_direct_message:
                continue
                
            # Usuń wzmiankę o bocie z treści wiadomości
            clean_text = message.text.replace(f"@{self.username}", "").strip()
            
            # Znajdź pasujący handler
            handler = self._find_handler(clean_text)
            
            if handler:
                try:
                    response = handler(message)
                    if response:
                        self.client.send_message(message.room_id, response)
                except Exception as e:
                    logger.error(f"Błąd w handlerze: {str(e)}")
                    self.client.send_message(
                        message.room_id,
                        f"Przepraszam, wystąpił błąd podczas przetwarzania Twojej wiadomości: {str(e)}"
                    )
            elif self.default_handler:
                try:
                    response = self.default_handler(message)
                    if response:
                        self.client.send_message(message.room_id, response)
                except Exception as e:
                    logger.error(f"Błąd w domyślnym handlerze: {str(e)}")
                    self.client.send_message(
                        message.room_id,
                        f"Przepraszam, wystąpił błąd podczas przetwarzania Twojej wiadomości: {str(e)}"
                    )
                    
    def _find_handler(self, text: str) -> Optional[Callable[[Message], Optional[str]]]:
        """
        Znajduje handler pasujący do treści wiadomości.
        
        Args:
            text: Treść wiadomości
            
        Returns:
            Optional[Callable[[Message], Optional[str]]]: Funkcja obsługująca wiadomość lub None
        """
        for pattern, handler in self.handlers.items():
            if re.search(pattern, text, re.IGNORECASE):
                return handler
                
        return None
        
    def register_handler(self, pattern: str, handler: Callable[[Message], Optional[str]]) -> None:
        """
        Rejestruje handler dla wiadomości pasujących do wzorca.
        
        Args:
            pattern: Wyrażenie regularne do dopasowania wiadomości
            handler: Funkcja obsługująca wiadomość
        """
        self.handlers[pattern] = handler
        logger.debug(f"Zarejestrowano handler dla wzorca: {pattern}")
        
    def set_default_handler(self, handler: Callable[[Message], Optional[str]]) -> None:
        """
        Ustawia domyślny handler dla wiadomości, które nie pasują do żadnego wzorca.
        
        Args:
            handler: Funkcja obsługująca wiadomość
        """
        self.default_handler = handler
        logger.debug("Ustawiono domyślny handler")
        
    def send_message(self, room_id: str, text: str) -> bool:
        """
        Wysyła wiadomość do pokoju.
        
        Args:
            room_id: ID pokoju
            text: Treść wiadomości
            
        Returns:
            bool: True jeśli wysłanie się powiodło, False w przeciwnym przypadku
        """
        return self.client.send_message(room_id, text)
