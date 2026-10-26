
from pydantic import ValidationError

from app.schemas.employee import EmployeeCreate, EmployeeResponse


# Test 1: Valid employee input
print("\n--- Test 1: Valid EmployeeCreate ---")

employee_data = EmployeeCreate(
    name="Rahul Sharma",
    email="rahul@example.com",
    subcadre_id=10,
    role_id=1,
)

print(employee_data)
print("Valid employee input passed!")


# Test 2: Invalid email
print("\n--- Test 2: Invalid Email ---")

try:
    EmployeeCreate(
        name="Rahul Sharma",
        email="invalid-email",
        subcadre_id=10,
        role_id=1,
    )
except ValidationError as error:
    print("Invalid email rejected successfully!")
    print(error)


# Test 3: Employee response
print("\n--- Test 3: EmployeeResponse ---")

employee_response = EmployeeResponse(
    employee_id=1,
    name="Rahul Sharma",
    email="rahul@example.com",
    subcadre_id=10,
    role_id=1,
    status=1,
)

print(employee_response)
print("Employee response validation passed!")

# Convert response to a dictionary
print("\n--- Response as Dictionary ---")
print(employee_response.model_dump())
