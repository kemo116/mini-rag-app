from fastapi import FastAPI, APIRouter, Depends, UploadFile
import os
from helpers.config import  get_settings, Settings
from controllers import DataController, ProjectController
from fastapi.responses import JSONResponse
from fastapi import status
import aiofiles
from models import ResponseSignalEnum
import logging 

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"], 
)

@data_router.post("/upload/{project_id}")
async def upload_data(project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
    # VALIDATE file properties
    
    data_controller = DataController()

    is_valid, result_signal = data_controller.validate_uploaded_file(file = file)
    if not is_valid:
        return JSONResponse(
            content={
                "signal": result_signal
            },
            status_code=status.HTTP_400_BAD_REQUEST
            )
    project_dir_path = ProjectController().get_project_path(project_id = project_id)
    file_path, file_id = data_controller.generate_unique_filepath(
        orig_filename = file.filename,
         project_id = project_id)
    # SAVE file to project directory
    try:

        async with aiofiles.open(file_path, 'wb') as out_file:
            while content := await file.read(app_settings.CHUNK_SIZE):
                await out_file.write(content)
    except Exception as e:
        logger.error(f"Error while saving file: {e}")
        return JSONResponse(
            content={
                "signal": ResponseSignalEnum.FILE_UPLAOD_FAILED.value
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.FILE_UPLAOD_SUCCESS.value,
            "file_id": file_id
        } 
    )
