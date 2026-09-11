from enum import Enum

class VectorDBEnums(Enum):
    QDRANTDB = "QDRANT"
    PGVECTOR = "PGVECTOR"


class DistanceMethodEnums(Enum):
    COSINE = "cosine"
    EUCLIDEAN = "EUCLIDEAN"
    DOT = "dot"



class PgVectorTableSchemeEnums(Enum):
    ID = "id"
    TEXT = "text"
    VECTOR = "vector"
    CHUNK_ID = "chunk_id"
    METADATA = "metadata"
    _PREFIX = "pgvector"


class PgVectorDistanceMethodEnums(Enum):
    COSINE = "vector_cosine_ops"
    DOT = "vector_12_ops"

class PgVectorIndexTypeEnums(Enum):
    HNSW = "hnsw"
    IVFLAT = "ivflat"






