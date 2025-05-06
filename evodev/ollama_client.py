"""
Moduł klienta Ollama do komunikacji z lokalnym serwerem Ollama LLM.
"""
import requests


class OllamaClient:
    """Klient do komunikacji z serwerem Ollama LLM"""
    
    def __init__(self, ollama_url="http://localhost:11434"):
        """Inicjalizacja klienta Ollama
        
        Args:
            ollama_url (str): URL serwera Ollama, domyślnie http://localhost:11434
        """
        self.ollama_url = ollama_url
        
    def run_inference(self, prompt, model="llama2"):
        """Wykonuje wnioskowanie na modelu LLM
        
        Args:
            prompt (str): Zapytanie do modelu
            model (str): Nazwa modelu do użycia, domyślnie llama2
            
        Returns:
            dict: Odpowiedź z serwera Ollama lub informacja o błędzie
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"prompt": prompt, "model": model},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": f"HTTP Error: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.ConnectionError as e:
            return {"status": "error", "error": f"ConnectionError: {str(e)}"}
        except requests.exceptions.Timeout as e:
            return {"status": "error", "error": f"Timeout: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Error: {str(e)}"}
            
    def check_status(self):
        """Sprawdza status serwera Ollama
        
        Returns:
            dict: Status serwera Ollama
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/health", timeout=5)
            
            if response.status_code == 200:
                return {"status": "available", "details": response.json()}
            else:
                return {
                    "status": "error",
                    "reason": f"HTTP Error: {response.status_code}",
                    "details": response.text
                }
                
        except requests.exceptions.ConnectionError as e:
            return {"status": "unavailable", "reason": f"ConnectionError: {str(e)}"}
        except requests.exceptions.Timeout as e:
            return {"status": "unavailable", "reason": f"Timeout: {str(e)}"}
        except Exception as e:
            return {"status": "error", "reason": f"Error: {str(e)}"}
