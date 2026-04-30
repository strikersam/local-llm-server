class ModelRegistry:
    """
    A centralized registry for available LLM models and their metadata.
    This class provides methods to access and manage model information.
    """
    _models = [
        {
            "name": "gpt-4o",
            "provider": "openai",
            "version": "4.0",
            "description": "A powerful multimodal model from OpenAI.",
            "is_default": True
        },
        {
            "name": "claude-3-opus",
            "provider": "anthropic",
            "version": "3.0",
            "description": "Anthropic's most advanced model.",
            "is_default": False
        },
        {
            "name": "llama-3-70b",
            "provider": "meta",
            "version": "L3-70B",
            "description": "A high-performance open-source model.",
            "is_default": False
        },
        # Add more models here as they become available
    ]

    @classmethod
    def get_all_models(cls) -> list[dict]:
        """
        Returns a list of all registered models metadata.
        """
        return cls._models

    @classmethod
    def get_model_by_name(cls, model_name: str) -> dict or None:
        """
        Retrieves a specific model's metadata by its name (case-insensitive).
        Returns None if the model is not found.
        """
        for model in cls._models:
            if model["name"].lower() == model_name.lower():
                return model
        return None
