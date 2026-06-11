from pydantic import BaseModel, Field

class UserRegisterRequest(BaseModel):
    companyName: str = Field(..., min_length=1)
    industry: str = Field(..., min_length=1)
    companySize: str = Field(..., min_length=1)
