# test_ollama_client.py

import unittest
from unittest.mock import MagicMock, patch

import requests

from evodev.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    """Unit tests for the OllamaClient class"""

    def setUp(self):
        """Set up test fixtures"""
        self.default_url = "http://localhost:11434"
        self.custom_url = "http://ollama:11434"
        self.client = OllamaClient()
        self.custom_client = OllamaClient(ollama_url=self.custom_url)

    def test_init_default_url(self):
        """Test initialization with default URL"""
        self.assertEqual(self.client.ollama_url, self.default_url)

    def test_init_custom_url(self):
        """Test initialization with custom URL"""
        self.assertEqual(self.custom_client.ollama_url, self.custom_url)

    @patch("evodev.ollama_client.requests.post")
    def test_run_inference_success(self, mock_post):
        """Test successful LLM inference"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "llama2",
            "response": "This is a test response",
            "done": True,
        }
        mock_post.return_value = mock_response

        # Test data
        prompt = "Hello, how are you?"

        # Call the method
        response = self.client.run_inference(prompt)

        # Verify the request was made correctly
        mock_post.assert_called_once_with(
            f"{self.default_url}/api/generate",
            json={"prompt": prompt, "model": "llama2"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Verify the response
        expected_response = {
            "model": "llama2",
            "response": "This is a test response",
            "done": True,
        }
        self.assertEqual(response, expected_response)

    @patch("evodev.ollama_client.requests.post")
    def test_run_inference_with_custom_model(self, mock_post):
        """Test LLM inference with custom model"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "mistral",
            "response": "This is a test response from Mistral",
            "done": True,
        }
        mock_post.return_value = mock_response

        # Test data
        prompt = "Hello, how are you?"
        model = "mistral"

        # Call the method
        response = self.client.run_inference(prompt, model)

        # Verify the request was made correctly
        mock_post.assert_called_once_with(
            f"{self.default_url}/api/generate",
            json={"prompt": prompt, "model": model},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        # Verify the response
        expected_response = {
            "model": "mistral",
            "response": "This is a test response from Mistral",
            "done": True,
        }
        self.assertEqual(response, expected_response)

    @patch("evodev.ollama_client.requests.post")
    def test_run_inference_http_error(self, mock_post):
        """Test LLM inference with HTTP error"""
        # Configure mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        mock_post.return_value = mock_response

        # Test data
        prompt = "Hello, how are you?"

        # Call the method
        response = self.client.run_inference(prompt)

        # Verify the response
        expected_response = {
            "status": "error",
            "error": "HTTP Error: 404",
            "details": "Model not found",
        }
        self.assertEqual(response, expected_response)

    @patch("evodev.ollama_client.requests.post")
    def test_run_inference_connection_error(self, mock_post):
        """Test LLM inference with connection error"""
        # Configure mock to raise ConnectionError
        mock_post.side_effect = requests.exceptions.ConnectionError(
            "Connection refused"
        )

        # Test data
        prompt = "Hello, how are you?"

        # Call the method and verify it handles the error
        response = self.client.run_inference(prompt)

        # Verify the response
        expected_response = {
            "status": "error",
            "error": "ConnectionError: Connection refused",
        }
        self.assertEqual(response, expected_response)

    @patch("evodev.ollama_client.requests.post")
    def test_run_inference_timeout(self, mock_post):
        """Test LLM inference with timeout"""
        # Configure mock to raise Timeout
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # Test data
        prompt = "Hello, how are you?"

        # Call the method and verify it handles the error
        response = self.client.run_inference(prompt)

        # Verify the response
        expected_response = {"status": "error", "error": "Timeout: Request timed out"}
        self.assertEqual(response, expected_response)

    @patch("evodev.ollama_client.requests.get")
    def test_check_status_available(self, mock_get):
        """Test status check when Ollama is available"""
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        # Call the method
        status = self.client.check_status()

        # Verify the request was made correctly
        mock_get.assert_called_once_with(f"{self.default_url}/api/health", timeout=5)

        # Verify the response
        expected_status = {"status": "available", "details": {"status": "ok"}}
        self.assertEqual(status, expected_status)

    @patch("evodev.ollama_client.requests.get")
    def test_check_status_http_error(self, mock_get):
        """Test status check with HTTP error"""
        # Configure mock response with error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_get.return_value = mock_response

        # Call the method
        status = self.client.check_status()

        # Verify the response
        expected_status = {
            "status": "error",
            "reason": "HTTP Error: 500",
            "details": "Internal server error",
        }
        self.assertEqual(status, expected_status)

    @patch("evodev.ollama_client.requests.get")
    def test_check_status_connection_error(self, mock_get):
        """Test status check when Ollama is unavailable due to connection error"""
        # Configure mock to raise ConnectionError
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        # Call the method
        status = self.client.check_status()

        # Verify the response
        expected_status = {
            "status": "unavailable",
            "reason": "ConnectionError: Connection refused",
        }
        self.assertEqual(status, expected_status)

    @patch("evodev.ollama_client.requests.get")
    def test_check_status_timeout(self, mock_get):
        """Test status check when Ollama times out"""
        # Configure mock to raise Timeout
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        # Call the method
        status = self.client.check_status()

        # Verify the response
        expected_status = {
            "status": "unavailable",
            "reason": "Timeout: Request timed out",
        }
        self.assertEqual(status, expected_status)


if __name__ == "__main__":
    unittest.main()
