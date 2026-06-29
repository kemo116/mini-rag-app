from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignalEnum
from .ProjectController import ProjectController 
import re
import os

class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576 

    def validate_uploaded_file(self, file:UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_EXTENSIONS:
            return False, ResponseSignalEnum.FILE_TYPE_NOT_SUPPORTED.value


        if file.size > self.app_settings.FILE_MAX_SIZE:
            return False, ResponseSignalEnum.FILE_SIZE_EXCEEDED

        return True,  ResponseSignalEnum.FILE_VALIDATED_SUCCESS
    def generate_unique_filepath(self, orig_filename: str, project_id : str):

        random_key =  self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id = project_id)
        cleaned_file_name = self.get_clean_file_name(orig_file_name = orig_filename)
        new_file_path = os.path.join(
            project_path,
            random_key + "_" + cleaned_file_name
            
        )
        while os.path.exists(new_file_path):
            random_key =  self.generate_random_string()
            new_file_path = os.path.join(
                project_path,
                random_key + "_" + cleaned_file_name
                
            )
        return new_file_path, random_key + "_" + cleaned_file_name

    def get_clean_file_name(self, orig_file_name: str):
        cleaned_file_name = re.sub(r'[^a-zA-Z0-9_.-]', '', orig_file_name.strip())
        cleaned_file_name = cleaned_file_name.replace(" ", "_")
        return cleaned_file_name    