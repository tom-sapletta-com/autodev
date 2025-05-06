"""
Klient API dla lokalnego modelu LLM Ollama.
"""

class OllamaClient:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        """Inicjalizacja klienta Ollama"""
        self.ollama_url = ollama_url

    def run_inference(self, prompt: str):
        """Wysyłanie promptu do modelu LLM"""
        pass

    def check_status(self):
        """Sprawdzenie statusu instancji Ollama"""
        pass
