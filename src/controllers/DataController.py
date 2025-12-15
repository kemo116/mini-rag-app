from .BaseController import BaseController
from fastapi import UploadFile
from models import ResponseSignalEnum



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