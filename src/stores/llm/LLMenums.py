from enum import Enum

class LLMEnums(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GEMINI = "GEMINI"  # <-- Added

class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant" 

class CohereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT" 
    DOCUMENT = "search_document"
    QUERY = "search_query"

class GeminiEnums(Enum): # <-- Added
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    DOCUMENT = "RETRIEVAL_DOCUMENT"
    QUERY = "RETRIEVAL_QUERY"

class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"