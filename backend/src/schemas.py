from datetime import datetime
from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    email: str
    password: str

class ServiceEventIn(BaseModel):
    tenant_id: int
    category: str
    severity: str = Field(pattern="^(routine|urgent|emergency)$")
    summary: str
    status: str = Field(default="resolved", pattern="^(open|resolved)$")
    satisfaction_score: float = Field(default=4.0, ge=1, le=5)
    opened_at: datetime | None = None

class SurveyIn(BaseModel):
    tenant_id: int
    lease_period: str = Field(min_length=4, max_length=40)
    cleanliness_score: float = Field(ge=1, le=5)
    service_score: float = Field(ge=1, le=5)
    value_score: float = Field(ge=1, le=5)
    community_score: float = Field(ge=1, le=5)
    renewal_intent: float = Field(ge=1, le=10)
    comments: str = ""

class ReviewIn(BaseModel):
    note: str = Field(min_length=3, max_length=300)
