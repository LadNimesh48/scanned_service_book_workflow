from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.auth import (LoginRequest, TokenResponse)
from app.core.security import verify_hash_password
from app.core.token import create_access_token

from app.models.employee import Employee

router = APIRouter(prefix="/api/v1/auth",tags=["Scanned Service Book Auth"],)



@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db),):
    
    employee = (db.query(Employee).filter(Employee.email == payload.email).first())

    if employee is None or employee.password_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password",)

    if employee.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is deactivated",)

    if not verify_hash_password(payload.password, employee.password_hash,):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password",)

    token_data = {
        "employee_id": employee.employee_id,
        "role_id": employee.role_id,
        "subcadre_id": employee.subcadre_id,
    }

    token = create_access_token(token_data)

    return {
        "status": True,
        "access_token": token,
        "token_type": "bearer",
    }