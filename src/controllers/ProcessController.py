from .BaseController import BaseController 
from .ProjectController import ProjectController
import os
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import ProcessingEnum

class ProcessController(BaseController):
    def __init__(self, project_id: str):
        super().__init__()
        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id = project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1]

    def get_file_loader(self, file_id: str):
        file_extension = self.get_file_extension(file_id = file_id)
        file_path= os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return none

        if file_extension == ProcessingEnum.TXT.value:
            return TextLoader(file_path, encoding = "utf-8")
        if file_extension == ProcessingEnum.PDF.value:
            return PyPDFLoader(file_path, encoding = "utf-8")
        else:
            raise ValueError(f"File extension {file_extension} not supported")

    def get_file_content(self, file_id: str):
        loader = self.get_file_loader(file_id = file_id)
        if loader:

            return loader.load()
        else:
            return None

    def process_file_content(self, file_content: list, file_id:str, chunk_size: int = 1000, overlap_size: int = 100):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = overlap_size,
            length_function = len,
            is_separator_regex = False,
        )
        file_content_text = [
            rec.page_content
            for rec in file_content
        ]
        file_content_metadata = [
            {
                "source": file_id,
                "page": getattr(rec, 'metadata', {}).get('page', 0),
                "type": "text"
            }
            for rec in file_content


        ]
        chunks = text_splitter.create_documents(
            file_content_text,
            metadatas = file_content_metadata
        )
        return chunks