
from typing import Literal
from pydantic import BaseModel, Field, model_validator, field_validator
from datetime import datetime


class ServiceBookNotificationResponse(BaseModel):
    status: bool = True
    notification_popup: bool
    remark: str | None = None


class ServiceBookDetailsResponse(BaseModel):
    status: bool = True
    s3_key: str
    category_id: int
    entity_id: int
    upload_status: int
    remark: str | None = None



class ServiceBookDecisionResponse(BaseModel):
    status: bool = True
    message: str
    upload_status: int
    workflow_request_created: bool
    request_id: int | None = None
    request_year_month: int | None = None



class ServiceBookEmployeeResponse(BaseModel):
    decision : Literal["CONFIRM", "NOT_CONFIRM"]
    remark : str | None = Field(default=None, max_length=2000)
    
    @model_validator(mode="after")
    def validate_remark(self):
        if self.decision == "NOT_CONFIRM" and not (self.remark and self.remark.strip()):
            raise ValueError("Remark is required when the Service Book is not confirmed")
        
        if self.decision == "CONFIRM" and self.remark and self.remark.strip():
            raise ValueError("Remark is not required when confirming")
        
        return self

class NodalNoChangesRequest(BaseModel):
    action: Literal["NO_NEED_CHANGES"] = "NO_NEED_CHANGES"
    remark: str = Field(min_length=1, max_length=2000)
    
    @field_validator("remark")
    @classmethod
    def validate_remark(cls, value: str) -> str:
        value = value.strip()
        
        if not value:
            raise ValueError("Nodal Officer remark is required")
        
        return value

class NodalDecisionResponse(BaseModel):
    status: bool = True
    message: str
    upload_status: int
    current_assignee_role_id: int


class NodalPendingRequestItem(BaseModel):
    request_id: int
    request_year_month: int
    employee_id: int
    employee_code: str | None = None
    employee_name: str | None = None
    employee_remark: str | None = None
    submitted_at: datetime | None = None


class NodalPendingRequestsResponse(BaseModel):
    status: bool
    total: int
    requests: list[NodalPendingRequestItem]