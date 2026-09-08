from sqlalchemy import func

from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum
from bson import ObjectId
from typing import Optional
from pymongo import InsertOne
from .db_schemes import DataChunk
from sqlalchemy.future import select

class ProjectModel(BaseDataModel):
    def __init__(self, db_client:object):
        super().__init__(db_client)
        self.collection = db_client

    @classmethod
    async def create_instance(cls, db_client: object):
        instance = cls(db_client)
        return instance


    
                
    async def create_project(self, project:Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.commit()
            await session.refresh(project)

        return project



        # result = await self.collection.insert_one(project.dict(by_alias=True, exclude_unset=True))
        # project.project_id = result.inserted_id
        # return project
    
    async def update_project(self, project_id: ObjectId, update_data: dict):
        return await self.collection.update_one(
            {"_id": project_id},
            {"$set": update_data}
        )
    async def get_project_or_create_one(self, project_id:str):
        
        async with self.db_client() as session:
            async with session.begin():
                query = select(Project).where(Project.project_id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if project is None:
                    project_rec = Project(
                        project_id = project_id
                    )
                    project = await self.create_project(project= project_rec)

                    return project
                else:
                    return project


        

    

    
    async def get_all_projects(self, page:int, page_size:int=10):
        async with self.db_client() as session:
            async with session.begin():
                total_documents = await session.execute(
                    select(func.count(Project.project_id))
                ).scalar()

                total_documents = total_documents.scalar_one()

                total_pages = (total_documents) // page_size
                if total_documents % page_size != 0:
                    total_pages += 1

                query = select(Project).offset((page - 1) * page_size).limit(page_size)
                projects = await session.execute(query).scalars().all()

                return {
                    "projects": projects,
                    "total_pages": total_pages,
                    "current_page": page
                }
