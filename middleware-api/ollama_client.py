# ollama_client.py

"""
Klient API dla lokalnego modelu LLM Ollama.

Copyright 2023 [Your Organization]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import requests
import logging
from typing import Dict, Any

# Konfiguracja logowania
logger = logging.getLogger(__name__)

class OllamaClient:
    """Klient API dla lokalnego modelu LLM Ollama."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """
        Inicjalizacja klienta Ollama.

        Args:
            ollama_url: URL serwera Ollama, domyślnie "http://localhost:11434"
        """
        self.ollama_url = ollama_url
        logger.info(f"Initialized Ollama client with URL: {ollama_url}")

    def run_inference(self, prompt: str, model: str = "llama2") -> Dict[str, Any]:
        """
        Wysyłanie promptu do modelu LLM i uzyskanie odpowiedzi.

        Args:
            prompt: Tekst do przetworzenia przez model
            model: Nazwa modelu do użycia, domyślnie "llama2"

        Returns:
            Dict: Odpowiedź z modelu LLM lub informacja o błędzie
        """
        logger.debug(f"Running inference with model {model}, prompt: {prompt[:50]}...")

        try:
            headers = {"Content-Type": "application/json"}
            payload = {"prompt": prompt, "model": model}

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                headers=headers,
                timeout=30  # 30-sekundowy timeout dla zapytań
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"HTTP Error: {response.status_code}"
                logger.error(f"{error_msg}, details: {response.text}")
                return {
                    "status": "error",
                    "error": error_msg,
                    "details": response.text
                }

        except requests.exceptions.ConnectionError as e:
            error_msg = f"ConnectionError: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(error_msg)
            return {
                "status": "error",
                "error": error_msg
            }

    def check_status(self) -> Dict[str, Any]:
        """
        Sprawdzenie statusu instancji Ollama.

        Returns:
            Dict: Status instancji Ollama
                - status: "available" jeśli serwer Ollama działa
                - status: "unavailable" jeśli serwer nie odpowiada
                - status: "error" jeśli wystąpił błąd HTTP
                - dodatkowo pola z szczegółami
        """
        logger.debug(f"Checking Ollama status at {self.ollama_url}...")

        try:
            response = requests.get(f"{self.ollama_url}/api/health", timeout=5)

            if response.status_code == 200:
                logger.info("Ollama server is available")
                return {
                    "status": "available",
                    "details": response.json()
                }
            else:
                error_msg = f"HTTP Error: {response.status_code}"
                logger.error(f"{error_msg}, details: {response.text}")
                return {
                    "status": "error",
                    "reason": error_msg,
                    "details": response.text
                }

        except requests.exceptions.ConnectionError as e:
            error_msg = f"ConnectionError: {str(e)}"
            logger.error(f"Ollama server is unavailable: {error_msg}")
            return {
                "status": "unavailable",
                "reason": error_msg
            }
        except requests.exceptions.Timeout as e:
            error_msg = f"Timeout: {str(e)}"
            logger.error(f"Ollama server timed out: {error_msg}")
            return {
                "status": "unavailable",
                "reason": error_msg
            }
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"Error checking Ollama status: {error_msg}")
            return {
                "status": "error",
                "reason": error_msg
            }