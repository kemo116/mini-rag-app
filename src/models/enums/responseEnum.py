from enum import Enum

class ResponseSignalEnum(str, Enum):
    FILE_VALIDATED_SUCCESS = "File_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLAOD_SUCCESS = "success"
    FILE_UPLOAD_FAILURE = "failure"
    processing_failed = "processing failed"
    processing_success = "processing success"
    NO_FILES_ERROR = "not_found_files"
    FILE_ID_ERROR = "NO_FILE_FOUND_WITH_THIS_ID"
    PROJECT_NOT_FOUND_ERROR = "PROJECT_NOT_FOUND"
    INSERT_INTO_VECTORDB_ERROR = "insert_into_vectordb_error"
    INSERT_INTO_VECTORDB_SUCCESS = "insert_into_vectordb_success"