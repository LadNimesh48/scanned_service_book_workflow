from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.session import get_db
from app.models.employee import Employee
from app.schemas.employee import (APIResponse,EmployeeCreate,EmployeeResponse,EmployeeUpdate)

from app.core.security import hash_password, verify_hash_password

from app.core.cache import get_cached_response, set_cached_response, invalidate_employee_cache
from app.core.token import get_current_user
from app.core.roles import role_config

router = APIRouter(prefix="/api/v1/employees",tags=["Scanned Service Book Employee"],)


@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/",response_model=APIResponse[EmployeeResponse], status_code=status.HTTP_201_CREATED,)
def create_employee(payload: EmployeeCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):
    
    # Only Nodal Officers can create employees
    if current_user["role_id"] != role_config.NODAL_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Nodal Officers can create employees",)
    
    existing_employee = (db.query(Employee).filter(Employee.email == payload.email).first())

    if existing_employee:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered",)

    new_employee_data = payload.model_dump(exclude={"password"})
    
    new_employee_data["subcadre_id"] = current_user["subcadre_id"]
    new_employee_data["password_hash"] = hash_password(payload.password)

    new_employee = Employee(**new_employee_data)

    try:
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)

        response = APIResponse[EmployeeResponse](
            status=True,
            items=EmployeeResponse.model_validate(new_employee),
        )

        invalidate_employee_cache()

        return response

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee data conflicts with an existing record",)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create employee",)


@router.get("/{employee_id}", response_model=APIResponse[EmployeeResponse],)
def get_emp_by_id(employee_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):
    
    cache_key = f"employees:detail:{employee_id}"

    # 1. Try Redis first
    employee = get_cached_response(cache_key, EmployeeResponse)

    # 2. Query PostgreSQL only on cache miss
    if employee is None:
        db_employee = (db.query(Employee).filter(Employee.employee_id == employee_id).first())

        if db_employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Employee not found for ID: {employee_id}",)

        employee = EmployeeResponse.model_validate(db_employee)
        set_cached_response(cache_key, employee)

    # 3. Authorize using the target employee's cached data
    if current_user["role_id"] == role_config.EMPLOYEE_ROLE_ID:
        if current_user["employee_id"] != employee.employee_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own employee record",)

    elif current_user["role_id"] == role_config.NODAL_ROLE_ID:
        if current_user["subcadre_id"] != employee.subcadre_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this sub-cadre",)

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized to view employee records",)

    # 4. Build the API response
    return APIResponse[EmployeeResponse](
        status=True,
        items=employee,
    )

@router.get("/", response_model=APIResponse[list[EmployeeResponse]])
def get_all_emp(skip: int = 0, limit: int = 10, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):

    if current_user["role_id"] != role_config.NODAL_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Nodal Officers can view the employee list",)

    cache_key = f"employees:list:skip:{skip}:limit:{limit}"

    cached = get_cached_response(cache_key, APIResponse[list[EmployeeResponse]],)

    if cached is not None:
        return cached

    employees = (db.query(Employee).filter(Employee.subcadre_id == current_user["subcadre_id"]).offset(skip).limit(limit).all())

    employee_items = [
        EmployeeResponse.model_validate(employee) for employee in employees
    ]

    response = APIResponse[list[EmployeeResponse]](
        status=True,
        items=employee_items,
    )

    set_cached_response(cache_key, response)

    return response


@router.put("/{employee_id}", response_model=APIResponse[EmployeeResponse],)
def update_employee(employee_id: int, payload: EmployeeUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):
    
    # Only Nodal Officers can update employees.
    if current_user["role_id"] != role_config.NODAL_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Nodal Officers can update employees",)

    # Find the target employee.
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found",)

    # Restrict updates to the Nodal Officer's sub-cadre.
    if employee.subcadre_id != current_user["subcadre_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for this sub-cadre",)

    # Only update fields explicitly supplied by the client.
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide at least one field to update",)

    # Prevent duplicate email addresses.
    if "email" in update_data:
        existing_employee = (db.query(Employee).filter(Employee.email == update_data["email"], Employee.employee_id != employee_id,).first())

        if existing_employee:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered",)

    # Hash the password before saving it.
    if "password" in update_data:
        update_data["password_hash"] = hash_password(update_data.pop("password"))

    try:
        for field, value in update_data.items():
            setattr(employee, field, value)

        db.commit()
        db.refresh(employee)

        # Clear cached employee details and employee lists.
        invalidate_employee_cache()

        return APIResponse[EmployeeResponse](
            status=True,
            items=EmployeeResponse.model_validate(employee),
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee data conflicts with an existing record",)

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to update employee",)
