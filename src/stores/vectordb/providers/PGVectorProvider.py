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
                 distance_method: str =     None, index_threshold: int = 100):
        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.index_threshold = index_threshold
        distance_method=distance_method
        self.pgvector_table_prefix = PgVectorTableSchemeEnums._PREFIX.value
        self.logger = logging.getLogger(__name__)
        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"

    # async def get_pgvector_index_name(self, collection_name: str) -> str:
    #     return f"{collection_name}_vector_idx"


    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text(
                    f"CREATE EXTENSION IF NOT EXISTS vector"
                ))
            await session.commit()

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:

        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT * FROM pg_tables WHERE tablename = :collection_name')
                result = await session.execute(list_tbl, {'collection_name': collection_name})
                record = result.scalar_one_or_none()
        return record

    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text('SELECT * FROM pg_tables WHERE tablename LIKE :prefix')
                result = await session.execute(list_tbl, {'prefix': self.pgvector_table_prefix})
                records = result.scalars().all()
        return records


    async def get_collection_info(self, collection_name: str)-> dict:
        record = None
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text('''
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                     FROM pg_tables WHERE tablename = :collection_name''')

                count_sql = sql_text(f"SELECT COUNT(*) FROM {collection_name}")
                table_info = await session.execute(table_info_sql, {'collection_name': collection_name})
                record_count = await session.execute(count_sql)
                table_data = table_info.fetchone()
                if not table_data:
                    return None

                return{
                    "table_info": dict(table_data._mapping),
                    "record_count": record_count.scalar(),
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
                            {PgVectorTableSchemeEnums.METADATA.value} JSONB DEFAULT \'{{}}\',
                            FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES chunks (chunk_id)
                        )
                    ''')
                    await session.execute(create_table_sql)
                    await session.commit()

            return True
        return False
    

    async def is_index_existed(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_idx = sql_text('SELECT 1 FROM pg_indexes WHERE tablename = :collection_name AND indexname = :index_name')
                result = await session.execute(list_idx, {'collection_name': collection_name, 'index_name': index_name})
                record = result.scalar_one_or_none()
        return record


    
    async def create_vector_index(self, collection_name: str,index_type: str= PgVectorIndexTypeEnums.HNSW.value):
        is_index_existed = await self.is_index_existed(collection_name= collection_name)

        if is_index_existed:
            return False

        async with self.db_client() as session:
            async with session.begin():
                count_sql = sql_text(f'SELECT COUNT(*) FROM {collection_name}')
                result = await session.execute(count_sql)
                records_count = result.scalar_one()
                if records_count< self.index_threshold:
                    return False

                index_name = self.default_index_name(collection_name)
                self.logger.info(f"Creating vector index {index_name} for collection {collection_name}")

                create_idx_sql = sql_text(f'CREATE INDEX {index_name} ON {collection_name} USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method}) ')
                await session.execute(create_idx_sql)
                self.logger.info(f"End of Execution create index SQL for collection: {collection_name}")

    
    async def reset_vector_index(self, collection_name: str,index_type: str= PgVectorIndexTypeEnums.HNSW.value):
            index_name = self.default_index_name(collection_name)
            is_index_existed = await self.is_index_existed(collection_name= collection_name)
            
            if is_index_existed:
                return False
    
            async with self.db_client() as session:
                async with session.begin():
                    drop_sql = sql_text(f'DROP INDEX IF EXISTS {index_name}')
                    await session.execute(drop_sql)

            return await self.create_vector_index(collection_name= collection_name, index_type= index_type)

    
    
    async def insert_one(self, collection_name: str, text: str, vector: list, 
                       metadata: dict = None,
                       record_id: str = None):

        is_collection_existed = await self.is_collection_existed(collection_name= collection_name)
        
        
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist")
            return False
        
        if not record_id:
            self.logger.error(f"Record ID {record_id} is None")
            return False

        async with self.db_client() as session:
            async with session.begin():


                insert_sql = sql_text(f'INSERT INTO {collection_name}'
                                    f'({PgVectorTableSchemeEnums.TEXT.value}',
                                        f'{PgVectorTableSchemeEnums.VECTOR.value}',
                                        f'{PgVectorTableSchemeEnums.CHUNK_ID.value}',
                                        f'{PgVectorTableSchemeEnums.METADATA.value})'
                                        f'VALUES (:text, :vector, :chunk_id, :metadata)')
                await session.execute(insert_sql, 
                                      {'text': text, 
                                       'vector': "[" + ",".join([str(v) for v in vector]) + "]",
                                        'chunk_id': record_id, 
                                        'metadata': metadata})
                await session.commit()
        return True


    async def insert_many(self, collection_name: str, texts: list, vectors: list, 
                       metadata: list = None,
                       record_ids: list = None, batch_size: int = 50):

        is_collection_existed = await self.is_collection_existed(collection_name= collection_name)
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist")
            return False

        if len(vectors) != len(record_ids):
            self.logger.error(f"Vectors length {len(vectors)} does not match record_ids length {len(record_ids)}")
            return False

        if not metadata or len(metadata) ==0:
            metadata = [{} for _ in range(len(texts))]

        insert_sql = sql_text(f'''
            INSERT INTO {collection_name}
            ({PgVectorTableSchemeEnums.TEXT.value}, {PgVectorTableSchemeEnums.VECTOR.value},
             {PgVectorTableSchemeEnums.CHUNK_ID.value}, {PgVectorTableSchemeEnums.METADATA.value})
            VALUES (:text, :vector, :chunk_id, :metadata)
        ''')

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i+batch_size]
                    batch_record_ids = record_ids[i:i+batch_size]
                    batch_metadata = metadata[i:i+batch_size]

                    batch_params = [
                        {
                            'text': _text,
                            'vector': "[" + ",".join([str(v) for v in _vector]) + "]",
                            'chunk_id': _record_id,
                            'metadata': json.dumps(_metadata),
                        }
                        for _text, _vector, _metadata, _record_id in zip(batch_texts, batch_vectors, batch_metadata, batch_record_ids)
                    ]

                    await session.execute(insert_sql, batch_params)
                await session.commit()
        return True


    async def search_by_vector(self, collection_name: str, vector: list, limit: int) -> List[RetrievedDocument]:
        is_collection_existed = await self.is_collection_existed(collection_name= collection_name)
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist")
            return None

        vector = "[" + ",".join([str(v) for v in vector]) + "]"

        async with self.db_client() as session:
            async with session.begin():
                search_sql = sql_text(f'''
                    SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, 
                    1- ({PgVectorTableSchemeEnums.VECTOR.value} <=> :vector) as score
                    FROM {collection_name}
                    ORDER BY score DESC
                    LIMIT :limit
                ''')
                result = await session.execute(search_sql, {'vector': vector, 'limit': limit})
                records = result.fetchall()
                return [
                    RetrievedDocument(
                        text=record.text,
                        score=record.score
                    )
                    for record in records
                ]


    

           


                    



    
        