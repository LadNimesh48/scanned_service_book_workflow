

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")


class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    # subcadre_id: int
    role_id: int


class EmployeeResponse(BaseModel):
    employee_id: int
    name: str
    email: EmailStr
    subcadre_id: int
    role_id: int
    status: int

    model_config = ConfigDict(from_attributes=True)

class APIResponse(BaseModel, Generic[T]):
    status: bool
    items: T


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)

    model_config = ConfigDict(extra="forbid")
