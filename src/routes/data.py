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
from bson.objectid import ObjectId
from .schemas.data import ProcessRequest
from models.AssetModel import AssetModel
from models.ProjectModel import ProjectModel
from models.db_schemes import DataChunk, Asset
from models.ChunkModel import ChunkModel
from models.enums.asset_type_enum import AssetTypeEnum

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
    
    # store the assets into the database
    asset_model = await AssetModel.create_instance(
        db_client = request.app.db_client
    )
    asset_resource = Asset(
        asset_project_id = project.id,
        asset_type = AssetTypeEnum.FILE.value,
        asset_name = file_id,
        asset_size = os.path.getsize(file_path)

    )

    asset_record = await asset_model.create_asset(asset= asset_resource)

    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.FILE_UPLAOD_SUCCESS.value,
            "file_id": str(asset_record.id),
            # "project_id": str(project._id)
        } 
    )
@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: str, process_request: ProcessRequest):
    data_controller = DataController()
    project_file_ids = {}
    do_reset = process_request.do_reset
    overlap_size = process_request.overlap_size
    chunk_size = process_request.chunk_size
    project_model = await ProjectModel.create_instance(
        db_client = request.app.db_client
    )
    project = await project_model.get_project_or_create_one(
            project_id = project_id
        )
    asset_model = await AssetModel.create_instance(
            db_client = request.app.db_client
        )
    if process_request.file_id:
        asset_record = await asset_model.get_asset_record(
            asset_project_id=project.id,
            asset_name=process_request.file_id
        )

        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignalEnum.FILE_ID_ERROR.value,
                }
            )

        project_file_ids = {
            asset_record.id: asset_record.asset_name
        }
    
    else:
        

        project_files = await asset_model.get_all_project_assets(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value,
        )

        project_file_ids = {
            record.id : record.asset_name
            for record in project_files
        }

    if len(project_file_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignal.NO_FILES_ERROR.value,
            }
        )

    process_controller = ProcessController(project_id = project_id)
    no_records = 0
    no_files = 0
    chunk_model = await ChunkModel.create_instance(
            db_client = request.app.db_client
        )
    if do_reset==1:
        await chunk_model.delete_chunks_by_project_id(project_id = project.id)

    for asset_id, file_id in project_file_ids.items():
        file_content = process_controller.get_file_content(file_id = file_id)
        
        if file_content is None:
            logger.error(f"Error while loading file content for file_id: {file_id}")
            continue
        
       
       



       
        

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
                chunk_asset_id = asset_id,
            )
            for i, chunk in enumerate(chunks)
        ]

        
        
        no_records += await chunk_model.insert_many_chunks(chunks = chunks_records)
        no_files += 1
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.processing_success.value,
            "no_of_chunks": no_records,
            "processed_files": no_files
        }
    )
