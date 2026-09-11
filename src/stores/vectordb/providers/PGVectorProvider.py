from typing import List

from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import( DistanceMethodEnums, 
PgVectorIndexTypeEnums, PgVectorDistanceMethodEnums, PgVectorTableSchemeEnums)


from ..VectorDBInterface import VectorDBInterface
import logging
from ..VectorDBEnums import VectorDBEnums, DistanceMethodEnums
from models.db_schemes import RetrievedDocument
from sqlalchemy.sql import text as sql_text
import json

class PgVectorProvider(VectorDBInterface):
    def __init__(self, db_client, default_vector_size : int = 786,
                 distance_method: str =     None):
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        distance_method=distance_method
        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value
        self.logger = logging.getLogger(__name__)


    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text(
                    f"CREATE EXTENSION IF NOT EXISTS pgvector"
                ))
            await session.commit()

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:

        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT * FROM pg_tables WHERE table_name = :collection_name')
                result = await session.execute(list_tbl, {'collection_name': collection_name})
                record = result.scalar_one_or_none()
        return record

    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT * FROM pg_tables WHERE table_name LIKE :prefix')
                result = await session.execute(list_tbl, {'prefix': self.pgvector_table_prefix})
                records = result.scalars().all()
        return records


    async def get_collection_info(self, collection_name: str)-> dict:
        record = None
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text('''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes 
                     FROM pg_tables WHERE table_name = :collection_name''')

                count_sql = sql_text(f"SELECT COUNT(*) FROM :collection_name")
                table_info = await session.execute(table_info_sql, {'collection_name': collection_name})
                record_count = await session.execute(count_sql, {'collection_name': collection_name})
                table_data = table_info.fetchone()
                if not table_data:
                    return None

                return{
                    "table_info": dict(table_data),
                    "record_count": record_count,
                }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection {collection_name}")
                await session.execute(sql_text(f"DROP TABLE IF EXISTS {collection_name}"))
                await session.commit()

        return True

    async def create_collection(self, collection_name: str,
                               embedding_size: int,
                               do_reset: bool = False):

        if do_reset:
            _ = await self.delete_collection(collection_name= collection_name)

        is_collection_existed = await self.is_collection_existed(collection_name= collection_name)
        if not is_collection_existed:
            self.logger.info(f"Creating collection {collection_name}")

        async with self.db_client() as session:
            async with session.begin():
                create_table_sql = sql_text(f'''
                    CREATE TABLE IF NOT EXISTS {collection_name} (
                        {PgVectorTableSchemeEnums.ID.value} SERIAL PRIMARY KEY,
                        {PgVectorTableSchemeEnums.TEXT.value} TEXT,
                        {PgVectorTableSchemeEnums.VECTOR.value} VECTOR({embedding_size}),
                        {PgVectorTableSchemeEnums.CHUNK_ID.value} INTEGER,
                        {PgVectorTableSchemeEnums.METADATA.value} JSONB DEFAULT \'{{}}\'
                        FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks (chunk_id)
                    )
                ''')
                await session.commit()



    
        