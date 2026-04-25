from fastapi import FastAPI, APIRouter, Depends, UploadFile
import os
from fastapi import Request
from helpers.config import  get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from fastapi.responses import JSONResponse
from fastapi import status
import aiofiles
from models import ResponseSignalEnum
import logging 
from .schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.db_schemes import DataChunk
from models.ChunkModel import ChunkModel

logger = logging.getLogger('uvicorn.error')

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"], 
)

@data_router.post("/upload/{project_id}")
async def upload_data(request: Request, project_id: str, file: UploadFile, app_settings: Settings = Depends(get_settings)):
    # VALIDATE file properties
    
    project_model =  await ProjectModel.create_instance(
        db_client = request.app.db_client
    )
    project = await project_model.get_project_or_create_one(
        project_id = project_id
    )





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
            "file_id": file_id,
            "project_id": str(project._id)
        } 
    )
@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: str, process_request: ProcessRequest):
    data_controller = DataController()
    
    file_id = process_request.file_id
    process_controller = ProcessController(project_id = project_id)
    file_content = process_controller.get_file_content(file_id = file_id)
    overlap_size = process_request.overlap_size
    do_reset = process_request.do_reset



    project_model = await ProjectModel.create_instance(
        db_client = request.app.db_client
    )
    project = await project_model.get_project_or_create_one(
        project_id = project_id
    )

    chunks = process_controller.process_file_content(
        file_content = file_content,
        file_id = file_id,
        chunk_size = process_request.chunk_size,
        overlap_size = process_request.overlap_size,
    )
    

    if chunks is None or len(chunks) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignalEnum.processing_failed.value
            }
            
        )
        
    chunks_records = [
        DataChunk(
            chunk_text = chunk.page_content,
            chunk_order = i+1,
            chunk_metadata = chunk.metadata,
            chunk_project_id = project.id,
        )
        for i, chunk in enumerate(chunks)
    ]

    chunk_model = await ChunkModel.create_instance(
        db_client = request.app.db_client
    )
    if do_reset==1:
        await chunk_model.delete_chunks_by_project_id(project_id = project.id)

    no_records = await chunk_model.insert_many_chunks(chunks = chunks_records)
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.processing_success.value,
            "no_of_chunks": no_records
        }
    )
