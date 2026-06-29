from enum import Enum

class VectorDBEnums(Enum):
    QDRANTDB = "QDRANT"


class DistanceMethodEnums(Enum):
    COSINE = "cosine"
    EUCLIDEAN = "EUCLIDEAN"
    DOT = "dot"



