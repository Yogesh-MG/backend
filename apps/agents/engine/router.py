"""
LLM Router — Sends requests to local Ollama or cloud API.

This is the "NeMo Claw Router" from the architecture pitch.
For now, it only supports Ollama (local). Cloud escalation
(DeepSeek-V3) will be added in Phase 2.
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Routes LLM requests to the appropriate backend.
    
    Phase 1: Ollama only (local)
    Phase 2: + DeepSeek-V3 cloud escalation for complex reasoning
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434/api/chat",
        model_name: str = "llama3.2:3b",
        timeout: int = 120,
    ):
        self.ollama_url = ollama_url
        self.model_name = model_name
        self.timeout = timeout
    
    def chat(self, messages: list[dict], stream: bool = False) -> str:
        """
        Send a chat request to the LLM and return the response text.
        
        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": "..."}
            stream: Whether to stream the response (not yet supported)
            
        Returns:
            The AI's response text.
        """
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,  # Streaming handled at WebSocket layer later
        }
        
        try:
            logger.info(f"[LLM] Sending {len(messages)} messages to {self.model_name}")
            
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            ai_reply = data["message"]["content"]
            
            # Log performance stats
            total_ms = data.get("total_duration", 0) / 1_000_000
            eval_count = data.get("eval_count", 0)
            logger.info(f"[LLM] {eval_count} tokens in {total_ms:.0f}ms")
            
            return ai_reply
            
        except requests.ConnectionError:
            error = "Cannot connect to Ollama. Is it running? (ollama serve)"
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
