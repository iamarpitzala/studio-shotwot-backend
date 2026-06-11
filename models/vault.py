from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VaultAssetResponse(BaseModel):
    assetId: str
    category: str
    filename: str
    signedUrl: Optional[str] = None
    uploadedAt: datetime
