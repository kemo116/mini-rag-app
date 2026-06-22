from .LLMenums import LLMEnums
from .providers import OpenAIProvider, CohereProvider
from .providers.GeminiProvider import GeminiProvider # <-- Added import

class LLMProviderFactory:
    def __init__(self, config): # changed config type hint to handle Settings object
        self.config = config

    def create(self, provider: str):
        if provider == LLMEnums.OPENAI.value:
            return OpenAIProvider(
                api_key = self.config.OPENAI_API_KEY,
                api_url = self.config.OPENAI_API_URL,
                default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                default_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        if provider == LLMEnums.COHERE.value:
            return CohereProvider(
                api_key = self.config.COHERE_API_KEY,
                default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                default_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        if provider == LLMEnums.GEMINI.value: # <-- Added block
            return GeminiProvider(
                api_key = self.config.GEMINI_API_KEY,
                default_input_max_characters=self.config.INPUT_DEFAULT_MAX_CHARACTERS,
                default_generation_max_output_tokens=self.config.GENERATION_DEFAULT_MAX_TOKENS,
                default_temperature=self.config.GENERATION_DEFAULT_TEMPERATURE
            )
        
        return None