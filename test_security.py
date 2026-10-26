from app.core.security import hash_password, verify_hash_password

password = "TestPassword123!"
hashed_password = hash_password(password)

print("Hash created:", hashed_password != password)
print("Correct password:", verify_hash_password(password, hashed_password))
print("Wrong password:", verify_hash_password("WrongPassword!", hashed_password))