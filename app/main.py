from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_db

# Load All Routes
from app.routes.employees import router as employees_router
from app.routes.auth import router as aith_router
from app.routes.scanned_service_book import router as scanned_service_book_router

import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Scanned Service Book API", version="1.0.0")


@app.get("/")
def root():
    return {"msg": "FastAPI application is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "PostgreSQL",
        }
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )


# Inclide All Route

app.include_router(employees_router)
app.include_router(aith_router)
app.include_router(scanned_service_book_router)