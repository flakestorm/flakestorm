"""
HuggingFace Integration

Auto-download attacker models from HuggingFace Hub.
Supports GGUF quantized models for use with Ollama.
"""

from __future__ import annotations

import logging
from pathlib import Path

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

    def __init__(self, models_dir: Path | None = None):
        """
        Initialize the provider.

        Args:
            models_dir: Directory to store downloaded models
                       (default: ~/.flakestorm/models)
        """
        if models_dir is None:
            self.models_dir = Path.home() / ".flakestorm" / "models"
        else:
            self.models_dir = Path(models_dir)

        self.models_dir.mkdir(parents=True, exist_ok=True)

    def download_model(
        self,
        model_id: str,
        filename: str | None = None,
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
                "Install with: pip install flakestorm[huggingface]"
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
        List recommended models for flakestorm.

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

    def import_to_ollama(
        self,
        model_path: Path | str,
        model_name: str | None = None,
        ollama_host: str = "http://localhost:11434",
    ) -> str:
        """
        Import a GGUF model into Ollama.

        This creates an Ollama model from a downloaded GGUF file,
        making it available for use with `ollama run <model_name>`.

        Args:
            model_path: Path to the GGUF model file
            model_name: Name for the model in Ollama (default: derived from filename)
            ollama_host: Ollama server URL

        Returns:
            The model name as registered in Ollama

        Example:
            >>> provider = HuggingFaceModelProvider()
            >>> path = provider.download_model("TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
            >>> model_name = provider.import_to_ollama(path, "mistral-attacker")
            >>> # Now use with: ollama run mistral-attacker
        """
        import subprocess  # nosec B404
        import tempfile

        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        # Derive model name from filename if not provided
        if model_name is None:
            # e.g., "mistral-7b-instruct-v0.2.Q4_K_M.gguf" -> "mistral-7b-instruct"
            name = model_path.stem.lower()
            # Remove quantization suffix
            for quant in ["q4_k_m", "q5_k_m", "q8_0", "q4_0", "q5_0", "q6_k", "q3_k_m"]:
                name = name.replace(f".{quant}", "").replace(f"-{quant}", "")
            model_name = name.replace(".", "-").replace("_", "-")

        logger.info(f"Importing {model_path.name} to Ollama as '{model_name}'...")

        # Create a Modelfile for Ollama
        modelfile_content = f"""# Modelfile for {model_name}
# Imported from: {model_path.name}

FROM {model_path.absolute()}

# Default parameters for mutation generation
PARAMETER temperature 0.8
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

# System prompt for mutation tasks
SYSTEM You are a helpful assistant that generates text variations.
"""

        # Write Modelfile to temp directory
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".Modelfile", delete=False
        ) as f:
            f.write(modelfile_content)
            modelfile_path = f.name

        try:
            # Run ollama create command
            result = subprocess.run(  # nosec B603, B607
                ["ollama", "create", model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for large models
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to import model to Ollama: {result.stderr}")

            logger.info(f"Successfully imported model as '{model_name}'")
            logger.info(f"Use with: ollama run {model_name}")

            return model_name

        finally:
            # Clean up temp file
            Path(modelfile_path).unlink(missing_ok=True)

    def download_and_import(
        self,
        model_id: str,
        model_name: str | None = None,
        quantization: str = "Q4_K_M",
    ) -> str:
        """
        Download a model from HuggingFace and import it to Ollama in one step.

        Args:
            model_id: HuggingFace model ID
            model_name: Name for the model in Ollama
            quantization: Preferred quantization level

        Returns:
            The model name as registered in Ollama

        Example:
            >>> provider = HuggingFaceModelProvider()
            >>> name = provider.download_and_import(
            ...     "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            ...     model_name="flakestorm-attacker"
            ... )
            >>> # Now use in flakestorm.yaml:
            >>> # llm:
            >>> #   model: "flakestorm-attacker"
        """
        # Download the model
        model_path = self.download_model(
            model_id=model_id,
            quantization=quantization,
        )

        # Import to Ollama
        return self.import_to_ollama(
            model_path=model_path,
            model_name=model_name,
        )

    @staticmethod
    def verify_ollama_connection(host: str = "http://localhost:11434") -> bool:
        """
        Verify that Ollama is running and accessible.

        Args:
            host: Ollama server URL

        Returns:
            True if Ollama is accessible, False otherwise
        """
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(f"{host}/api/version")
            with urllib.request.urlopen(req, timeout=5) as response:  # nosec B310
                return response.status == 200
        except (urllib.error.URLError, TimeoutError):
            return False

    @staticmethod
    def list_ollama_models(host: str = "http://localhost:11434") -> list[str]:
        """
        List models available in Ollama.

        Args:
            host: Ollama server URL

        Returns:
            List of model names

        Example:
            >>> models = HuggingFaceModelProvider.list_ollama_models()
            >>> print(models)
            ['qwen2.5-coder:7b', 'mistral:7b', 'llama2:7b']
        """
        import json
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(f"{host}/api/tags")
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                data = json.loads(response.read().decode())
                return [model["name"] for model in data.get("models", [])]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return []
