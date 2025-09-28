from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator

class SurveySubmission(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=13, le=120)
    consent: bool = Field(..., description="Must be true to accept")
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)

    # REQUIRED BY SPEC (optional in requests)
    user_agent: Optional[str] = None
    submission_id: Optional[str] = None

    @validator("comments")
    def _strip_comments(cls, v):
        return v.strip() if isinstance(v, str) else v

    @validator("consent")
    def _must_consent(cls, v):
        if v is not True:
            raise ValueError("consent must be true")
        return v

class StoredSurveyRecord(BaseModel):
    # DO NOT inherit SurveySubmission; store only hashed PII
    submission_id: str
    user_agent: Optional[str] = None
    email_hash: Optional[str] = None
    age_hash: Optional[str] = None

    received_at: datetime
    ip: str

    # non-PII carried through
    name: str
    rating: int
    comments: Optional[str] = None
    consent: bool
