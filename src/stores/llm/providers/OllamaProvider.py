from ..LLMinterface import LLMInterface
from ..LLMenums import OpenAIEnums
import logging
from openai import OpenAI

class OllamaProvider(LLMInterface):

    def __init__(self, api_url: str,
                 default_input_max_characters: int = 1000,
                 default_generation_max_output_tokens: int = 1000,
                 default_temperature: float = 0.1):
        self.api_url = api_url
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_temperature = default_temperature
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't require a real key
            base_url=f"{api_url.rstrip('/')}/v1"
        )
        self.enums = OpenAIEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt)
        }

    def generate_text(self, prompt: str, chat_history: list = None, max_output_tokens: int = None, temperature: float = None):
        if chat_history is None:
            chat_history = []

        if not self.generation_model_id:
            self.logger.error("Generation model is not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_temperature

        chat_history.append(
            self.construct_prompt(prompt=prompt, role=OpenAIEnums.USER.value)
        )

        try:
            response = self.client.chat.completions.create(
                model=self.generation_model_id,
                messages=chat_history,
                max_tokens=max_output_tokens,
                temperature=temperature
            )

            if not response or not response.choices or len(response.choices) == 0:
                self.logger.error("Generation response is not valid")
                return None

            return response.choices[0].message.content

        except Exception as e:
            self.logger.error(f"Ollama generation error: {e}")
            return None

    def embed_text(self, text: str, document_type: str = None):
        if not self.embedding_model_id:
            self.logger.error("Embedding model is not set")
            return None

        try:
            response = self.client.embeddings.create(
                model=self.embedding_model_id,
                input=text
            )

            if not response or not response.data or len(response.data) == 0:
                self.logger.error("Embedding response is not valid")
                return None

            return response.data[0].embedding

        except Exception as e:
            self.logger.error(f"Ollama embedding error: {e}")
            return None
