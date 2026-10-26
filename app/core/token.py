from fastapi import Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError
from app.core.config import settings

from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.employee import Employee

bearer_scheme = HTTPBearer()


def create_access_token(data: dict) -> str:
    
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode,settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM,)

    return encoded_jwt



def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db),) -> dict:
    try:
        # Step 1: Decode and validate JWT
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],)

        employee_id = payload.get("employee_id")
        role_id = payload.get("role_id")
        subcadre_id = payload.get("subcadre_id")

        # Step 2: Validate claim types
        if (type(employee_id) is not int or type(role_id) is not int or type(subcadre_id) is not int):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims", headers={"WWW-Authenticate": "Bearer"},)

        # Step 3: Fetch employee from PostgreSQL
        employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()

        # Step 4: Check employee exists and is active
        if employee is None or employee.status != 1:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found or account deactivated", headers={"WWW-Authenticate": "Bearer"},)

        # Step 5: Verify token claims against current database values
        if (employee.role_id != role_id or employee.subcadre_id != subcadre_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token claims no longer match employee records", headers={"WWW-Authenticate": "Bearer"},)

        # Step 6: Return authenticated employee details
        return {
            "employee_id": employee.employee_id,
            "role_id": employee.role_id,
            "subcadre_id": employee.subcadre_id,
        }

    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"},)