"""
LLM Router — Sends requests to local Ollama or cloud API.

This is the "NeMo Claw Router" from the architecture pitch.
For now, it only supports Ollama (local). Cloud escalation
(DeepSeek-V3) will be added in Phase 2.
"""

import requests
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Routes LLM requests to the appropriate backend.
    
    Phase 1: Ollama only (local)
    Phase 2: + Cloud escalation (Groq, Gemini, DeepSeek, or other OpenAI-compatible API)
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3.2:3b",
        timeout: int = 120,
    ):
        self.ollama_url = ollama_url
        self.ollama_model = model_name
        self.timeout = timeout
        
        # Load cloud configurations from Django settings
        self.llm_api_key = getattr(settings, "LLM_API_KEY", "")
        self.llm_base_url = getattr(settings, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
        self.llm_model = getattr(settings, "LLM_MODEL", "openai/gpt-oss-20b")
    
    def chat(self, messages: list[dict], stream: bool = False) -> str:
        """
        Send a chat request to the LLM and return the response text.
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            stream: Whether to stream the response (not yet supported)
            
        Returns:
            The AI's response text.
        """
        is_cloud = bool(self.llm_api_key)
        
        if is_cloud:
            # Route to standard OpenAI-compatible API (e.g., Groq)
            url = f"{self.llm_base_url.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.llm_model,
                "messages": messages,
                "stream": False,
            }
        else:
            # Fallback to local Ollama
            url = self.ollama_url
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.ollama_model,
                "messages": messages,
                "stream": False,
            }
        
        try:
            logger.info(
                f"[LLM] Sending {len(messages)} messages to "
                f"{self.llm_model if is_cloud else self.ollama_model} "
                f"({'Cloud' if is_cloud else 'Ollama'})"
            )
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            
            if is_cloud:
                # Standard OpenAI chat completions format
                ai_reply = data["choices"][0]["message"]["content"]
                logger.info("[LLM] Cloud LLM responded successfully.")
            else:
                # Ollama format
                ai_reply = data["message"]["content"]
                
                # Log performance stats
                total_ms = data.get("total_duration", 0) / 1_000_000
                eval_count = data.get("eval_count", 0)
                logger.info(f"[LLM] {eval_count} tokens in {total_ms:.0f}ms")
            
            return ai_reply
            
        except requests.ConnectionError:
            provider = "Cloud LLM" if is_cloud else "Ollama"
            error = f"Cannot connect to {provider} at {url}."
            logger.error(f"[LLM] {error}")
            raise ConnectionError(error)
            
        except requests.Timeout:
            error = f"LLM request timed out after {self.timeout}s"
            logger.error(f"[LLM] {error}")
            raise TimeoutError(error)
            
        except Exception as e:
            logger.error(f"[LLM] Unexpected error: {e}")
            raise



# Singleton instance for the app
_router = None

def get_router() -> LLMRouter:
    """Get or create the global LLM router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
