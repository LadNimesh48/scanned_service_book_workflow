from sqlalchemy import Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column


from app.database.session import Base


class Employee(Base):
    __tablename__ = "employees" 
    
    employee_id : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    subcadre_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"),)