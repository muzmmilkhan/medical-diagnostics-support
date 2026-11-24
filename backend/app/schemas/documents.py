from pydantic import BaseModel


class UploadResponse(BaseModel):
    message: str
    filename: str
    chunks_processed: int
    stored_in_s3: bool
