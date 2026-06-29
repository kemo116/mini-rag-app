from ..LLMinterface import LLMInterface
from ..LLMenums import GeminiEnums, DocumentTypeEnum
import logging
from google import genai
from google.genai import types

class GeminiProvider(LLMInterface):

    def __init__(self, api_key: str, 
                 default_input_max_characters: int = 1000,
                 default_generation_max_output_tokens: int=1000,
                 default_temperature: float=0.1):
        
        self.api_key = api_key
        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_temperature = default_temperature
        
        self.generation_model_id = None
        self.embedding_model_id = None
        self.embedding_size = None
        
        # New Google GenAI SDK uses a Client object
        self.client = genai.Client(api_key=self.api_key)
        
        self.enums = GeminiEnums
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

    def generate_text(self, prompt: str, chat_history: list=None, max_output_tokens: int=None, temperature: float=None):
        if chat_history is None:
            chat_history = []
            
        if not self.generation_model_id:
            self.logger.error("Generation model is not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_temperature
        
        chat_history.append(
            self.construct_prompt(prompt=prompt, role=self.enums.USER.value)
        )

        system_instruction = None
        gemini_history = []

        # Parse internal generic roles into Gemini-specific roles
        for msg in chat_history:
            if msg["role"] == self.enums.SYSTEM.value:
                system_instruction = msg["content"]
            else:
                role = "model" if msg["role"] == self.enums.ASSISTANT.value else "user"
                gemini_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )

        try:
            # Generate content using the new Client API
            response = self.client.models.generate_content(
                model=self.generation_model_id,
                contents=gemini_history,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                )
            )

            if not response or not response.text:
                self.logger.error("Generation response is not valid")
                return None
                
            return response.text
            
        except Exception as e:
            self.logger.error(f"Gemini generation error: {e}")
            return None
            
    def embed_text(self, text: str, document_type: str = None):
        if not self.embedding_model_id:
            self.logger.error("Embedding model is not set")
            return None

        try:
            task_type = self.enums.DOCUMENT.value
            if document_type == DocumentTypeEnum.QUERY.value:
                task_type = self.enums.QUERY.value
            
            # Embed content using the new Client API
            response = self.client.models.embed_content(
                model=self.embedding_model_id,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type)
            )

            if not response or not response.embeddings or len(response.embeddings) == 0:
                self.logger.error("Embedding response is not valid")
                return None
                
            # The new SDK returns a list of embeddings, we want the float values of the first one
            return response.embeddings[0].values
            
        except Exception as e:
            self.logger.error(f"Gemini embedding error: {e}")
            return None