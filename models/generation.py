from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class GenerationRequest(BaseModel):
    brief: str = Field(..., min_length=1)
    referenceAssetId: str = Field(..., min_length=1)
    aspectRatio: str = Field("1:1", pattern="^(1:1|16:9|9:16)$")

class GenerationResponse(BaseModel):
    generationId: str
    status: str
    brief: str
    createdAt: datetime
    outputUrl: Optional[str] = None
    optimizedPrompt: Optional[str] = None
    error: Optional[str] = None
