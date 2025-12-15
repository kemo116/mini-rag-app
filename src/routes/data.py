from fastapi import FastAPI, APIRouter, Depends, UploadFile
import os
from helpers.config import  get_settings, Settings
from controllers import DataController
from fastapi.responses import JSONResponse
from fastapi import status


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"], 
)

@data_router.post("/upload/{project_id}")
async def upload_data(project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
    # VALIDATE file properties
    is_valid, result_signal = DataController().validate_uploaded_file(file = file)
    if not is_valid:
        return JSONResponse(
            content={
                "signal": result_signal
            },
            status_code=status.HTTP_400_BAD_REQUEST
            )


