from pydantic import BaseModel
from typing import Optional

class TranslationResponse(BaseModel):
    filename: str
    status: str
    download_url: Optional[str] = None
    message: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    service: str
