"""
HuggingFace Integration

Auto-download attacker models from HuggingFace Hub.
Supports GGUF quantized models for use with Ollama.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Recommended models for mutation generation
RECOMMENDED_MODELS = [
    {
        "id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "description": "Qwen 2.5 Coder - Fast and effective for code-aware mutations",
    },
    {
        "id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        "file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "description": "Mistral 7B Instruct - Great general-purpose attacker model",
    },
    {
        "id": "TheBloke/Llama-2-7B-Chat-GGUF",
        "file": "llama-2-7b-chat.Q4_K_M.gguf",
        "description": "Llama 2 Chat - Solid baseline model",
    },
]


class HuggingFaceModelProvider:
    """
    Provider for downloading models from HuggingFace Hub.
    
    Downloads quantized GGUF models that can be used with Ollama
    for local mutation generation.
    
    Example:
        >>> provider = HuggingFaceModelProvider()
        >>> provider.download_model("TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
    """
    
    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize the provider.
        
        Args:
            models_dir: Directory to store downloaded models
                       (default: ~/.entropix/models)
        """
        if models_dir is None:
            self.models_dir = Path.home() / ".entropix" / "models"
        else:
            self.models_dir = Path(models_dir)
        
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def download_model(
        self,
        model_id: str,
        filename: Optional[str] = None,
        quantization: str = "Q4_K_M",
    ) -> Path:
        """
        Download a model from HuggingFace Hub.
        
        Args:
            model_id: HuggingFace model ID (e.g., "TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
            filename: Specific file to download (auto-detected if not provided)
            quantization: Preferred quantization level
            
        Returns:
            Path to the downloaded model file
        """
        try:
            from huggingface_hub import hf_hub_download, list_repo_files
        except ImportError:
            raise ImportError(
                "huggingface-hub is required for model downloading. "
                "Install with: pip install entropix[huggingface]"
            )
        
        # If no filename specified, find appropriate GGUF file
        if filename is None:
            files = list_repo_files(model_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]
            
            # Prefer the specified quantization
            matching = [f for f in gguf_files if quantization.lower() in f.lower()]
            if matching:
                filename = matching[0]
            elif gguf_files:
                filename = gguf_files[0]
            else:
                raise ValueError(f"No GGUF files found in {model_id}")
        
        logger.info(f"Downloading {model_id}/{filename}...")
        
        # Download to cache, then copy to our models dir
        cached_path = hf_hub_download(
            repo_id=model_id,
            filename=filename,
        )
        
        # Return the cached path (HuggingFace handles caching)
        return Path(cached_path)
    
    def list_available(self) -> list[dict]:
        """
        List recommended models for Entropix.
        
        Returns:
            List of model info dictionaries
        """
        return RECOMMENDED_MODELS.copy()
    
    def list_downloaded(self) -> list[Path]:
        """
        List models already downloaded.
        
        Returns:
            List of paths to downloaded model files
        """
        return list(self.models_dir.glob("*.gguf"))

