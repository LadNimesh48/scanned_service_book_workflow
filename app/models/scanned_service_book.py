
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CDREhrmsUpload(Base):
    __tablename__ = "cdr_ehrms_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_parts: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_driver: Mapped[str] = mapped_column(String(16), nullable=False, default="s3")
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(Text, nullable=False)
    s3_upload_id: Mapped[str] = mapped_column(String(255), nullable=False)

    service_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.now(),onupdate=func.now(),)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class EhrmsWorkflowRequest(Base):
    __tablename__ = "ehrms_workflow_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    request_year_month: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    request_code: Mapped[str] = mapped_column(String(50), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    module_id: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_template_id: Mapped[int] = mapped_column(Integer, nullable=False)
    requester_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    requester_role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_status: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_assignee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assignee_role_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime,nullable=False,server_default=func.now(),onupdate=func.now(),)
    employee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    workflow_registry_no: Mapped[int | None] = mapped_column(BigInteger, nullable=True)




class EhrmsWorkflowRequestArchive(Base):
    __tablename__ = "ehrms_workflow_requests_archive"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(Integer, nullable=False)
    request_code: Mapped[str] = mapped_column(String(50), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    module_id: Mapped[int] = mapped_column(Integer, nullable=False)
    workflow_template_id: Mapped[int] = mapped_column(Integer, nullable=False)
    requester_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    requester_role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    current_status: Mapped[int] = mapped_column(Integer, nullable=False)
    current_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_assignee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_assignee_role_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    sla_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    request_year_month: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    workflow_registry_no: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())