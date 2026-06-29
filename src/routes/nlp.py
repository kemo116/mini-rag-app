import logging 
from fastapi.responses import JSONResponse
from fastapi import FastAPI, APIRouter, status, Depends, UploadFile, Request
from routes.schemas.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import ResponseSignalEnum
import json
logger = logging.getLogger('uvicorn.error')


nlp_router = APIRouter(

    prefix = "/api/v1/nlp",
    tags = ["api_v1", "nlp"],

)


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request, project_id: str, push_request: PushRequest):
    


    project_model = await ProjectModel.create_instance(
            request.app.db_client
        
        )
    
    chunk_model = await ChunkModel.create_instance(
        db_client = request.app.db_client
    )
    project = await project_model.get_project_or_create_one(
            project_id= project_id
        
        )
    
    if not project:
        return JSONResponse(
            status_code= status.HTTP_404_BAD_REQUEST,
            content= {
                "signal": ResponseSignalEnum.PROJECT_NOT_FOUND_ERROR.value,
            }
        )
    
    nlp_controller = NLPController(
           vectordb_client = request.app.vector_db_client,
           generation_client = request.app.generation_client,
           embedding_client = request.app.embedding_client,
           template_parser = request.app.template_parser,
        )
    
    has_records = True
    page_no = 1
    inserted_items_count = 0
    idx = 0
    while has_records:
        page_chunks = await chunk_model.get_project_chunks(
            project_id = project.id, page_no=page_no
        )
        if len(page_chunks):
            page_no+=1

        if not page_chunks or len(page_chunks) == 0:
            has_records = False
            break

        chunk_ids = list(range(idx, idx+len(page_chunks)))
        idx += len(page_chunks)

        is_inserted = nlp_controller.index_into_vector_db(
            project = project,
            chunks = page_chunks,
            chunks_ids = chunk_ids,
            do_reset = push_request.do_request,
        )

        if not is_inserted:
            return JSONResponse(
                status_code= status.HTTP_400_INTERNAL_SERVER_ERROR,
                content= {
                    "signal": ResponseSignalEnum.INSERT_INTO_VECTORDB_ERROR.value,
                }
            )
        
        inserted_items_count += len(page_chunks)
        
    return JSONResponse(
        status_code= status.HTTP_200_OK,
        content= {
            "signal": ResponseSignalEnum.INSERT_INTO_VECTORDB_SUCCESS.value,
            "inserted_items_count": inserted_items_count,
        }
    )
        
    # chunks = await chunk_model.get_project_chunks(
    #     project_id = project.project_id,
    # )
   
    

    

@nlp_router.get("/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str):
    project_model = await ProjectModel.create_instance(
        request.app.db_client
    
    )

    project = await project_model.get_project_or_create_one(
            project_id= project_id
        
    )

    nlp_controller = NLPController(
           vectordb_client = request.app.vector_db_client,
           generation_client = request.app.generation_client,
           embedding_client = request.app.embedding_client,
           template_parser = request.app.template_parser,
    )

    collection_info = nlp_controller.get_vector_db_collection_info(
        project = project,
    )

    return JSONResponse(
        status_code= status.HTTP_200_OK,
        content= {
            "signal": ResponseSignalEnum.VECTORDB_COLLECTION_RETRIEVED.value,
            "collection_info": collection_info,
        }
    ) 



@nlp_router.post("/index/search/{project_id}")
async def search_index(request: Request, project_id: str, search_request: SearchRequest):

    project_model = await ProjectModel.create_instance(
        db_client=request.app.db_client
    
    )

    project = await project_model.get_project_or_create_one(
            project_id= project_id
        
    )

    nlp_controller = NLPController(
           vectordb_client = request.app.vector_db_client,
           generation_client = request.app.generation_client,
           embedding_client = request.app.embedding_client,
           template_parser= request.app.template_parser,
    )

    search_results = nlp_controller.search_vector_db_collection(
        project = project,
        text = search_request.text,
        limit = search_request.limit,
    )

    if not search_results:
        return JSONResponse(
            status_code= status.HTTP_400_INTERNAL_SERVER_ERROR,
            content= {
                "signal": ResponseSignalEnum.SEARCH_VECTORDB_ERROR.value,
            }
        )
    
    return JSONResponse(
            content= {
                "signal": ResponseSignalEnum.SEARCH_VECTORDB_SUCCESS.value,
                "search_results": [result.dict() for result in search_results],
            }
        )


@nlp_router.post("/index/answer/{project_id}")
async def answer_rag(request: Request, project_id: str, search_request: SearchRequest):

    project_model = await ProjectModel.create_instance(
        db_client= request.app.db_client
    
    )

    project = await project_model.get_project_or_create_one(
            project_id= project_id
        
    )

    nlp_controller = NLPController(
           vectordb_client = request.app.vector_db_client,
           generation_client = request.app.generation_client,
           embedding_client = request.app.embedding_client,
           template_parser= request.app.template_parser,
    )

    answer, full_prompt, chat_history = nlp_controller.answer_rag_question(
        project = project,
        query = search_request.text,
        limit = search_request.limit,
        language = search_request.language,
    )

    if not answer:
        return JSONResponse(
            status_code= status.HTTP_500_INTERNAL_SERVER_ERROR,
            content= {
                "signal": ResponseSignalEnum.ANSWER_RAG_ERROR.value,
            }
        )
    
    return JSONResponse(
        content={
            "signal": ResponseSignalEnum.ANSWER_RAG_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        }

    )
    