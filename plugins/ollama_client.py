import json
import requests
from core.logger import logger

import time

class OllamaClient:
    def __init__(self, host="http://localhost:11434"):
        self.host = host

    def generate(self, model: str, prompt: str, schema: dict = None, options: dict = None) -> str:
        """Generate text from Ollama. Optionally enforces a JSON schema (format='json')."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if schema:
            payload["format"] = "json"
        
        if options:
            payload["options"] = options
            
        start_time = time.time()
        try:
            logger.debug(f"Calling Ollama model {model} on {url}")
            response = requests.post(url, json=payload, timeout=420)
            elapsed = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"Ollama HTTP {response.status_code} in {elapsed:.2f}s. Body: {response.text}")
                response.raise_for_status()
                
            result = response.json()
            response_text = result.get("response", "")
            logger.info(f"Ollama generate success in {elapsed:.2f}s for model {model}. Response size: {len(response_text)}")
            return response_text
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Ollama generation failed in {elapsed:.2f}s: {str(e)}")
            raise
