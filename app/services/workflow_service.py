
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import role_config
from app.models.scanned_service_book import (
    EhrmsWorkflowRequest,
    EhrmsWorkflowRequestArchive,
)


def find_active_employee_workflow(employee_id: int,upload_id: int, db: Session,) -> EhrmsWorkflowRequest | None:
    """Find an active workflow assigned to the employee for this upload."""
    return (
        db.query(EhrmsWorkflowRequest)
        .filter(
            EhrmsWorkflowRequest.employee_id == employee_id,
            EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID,
            EhrmsWorkflowRequest.current_status == 2,
            EhrmsWorkflowRequest.current_assignee_role_id
            == role_config.EMPLOYEE_ROLE_ID,
            EhrmsWorkflowRequest.request_data["upload_id"].as_integer()
            == upload_id,
        )
        .order_by(
            EhrmsWorkflowRequest.updated_at.desc(),
            EhrmsWorkflowRequest.id.desc(),
        )
        .with_for_update()
        .first()
    )


def archive_workflow_request(workflow_request: EhrmsWorkflowRequest, db: Session,) -> None:
    """Move an active workflow request into the archive table."""
    
    archive_fields = {
        column.name: getattr(workflow_request, column.name)
        for column in EhrmsWorkflowRequestArchive.__table__.columns
        if column.name != "archived_at"
        and hasattr(workflow_request, column.name)
    }

    db.add(EhrmsWorkflowRequestArchive(**archive_fields))
    db.delete(workflow_request)


def create_scanned_sb_workflow(employee_id: int,subcadre_id: int | None,upload_id: int,category_id: int,entity_id: int,employee_remark: str, db: Session,) -> EhrmsWorkflowRequest:
    """Create a workflow request for Nodal Officer review."""
    
    now = datetime.now()

    workflow_request = EhrmsWorkflowRequest(
        request_year_month=now.year * 100 + now.month,
        tenant_id=settings.SCANNED_SB_TENANT_ID,
        module_id=settings.SCANNED_SB_MODULE_ID,
        workflow_template_id=settings.SCANNED_SB_WORKFLOW_TEMPLATE_ID,
        request_code=str(uuid4()),
        request_type="SCANNED_SERVICE_BOOK_REVIEW",
        requester_id=employee_id,
        requester_role_id=role_config.EMPLOYEE_ROLE_ID,
        current_status=2,
        current_step=1,
        current_assignee_id=subcadre_id,
        current_assignee_role_id=settings.SCANNED_SB_ASSIGNEE_ROLE_ID,
        request_data={
            "upload_id": upload_id,
            "category_id": category_id,
            "entity_id": entity_id,
            "employee_remark": employee_remark,
            "nodal_remark": None,
            "decision": "NOT_CONFIRM",
        },
        priority="medium",
        submitted_at=now,
        employee_id=employee_id,
    )

    db.add(workflow_request)
    db.flush()
    return workflow_request



def reuse_returned_workflow(employee_id: int, upload_id: int, employee_remark: str, subcadre_id: int | None, db: Session, ) -> EhrmsWorkflowRequest | None:
    """Reuse a returned workflow request for the same scanned upload."""

    workflow_request = (
        db.query(EhrmsWorkflowRequest)
        .filter(
            EhrmsWorkflowRequest.employee_id == employee_id,
            EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID,
            EhrmsWorkflowRequest.current_status == 2,
            EhrmsWorkflowRequest.current_assignee_role_id
            == role_config.EMPLOYEE_ROLE_ID,
            EhrmsWorkflowRequest.request_data["upload_id"].as_integer()
            == upload_id,
        )
        .order_by(
            EhrmsWorkflowRequest.updated_at.desc(),
            EhrmsWorkflowRequest.id.desc(),
        )
        .with_for_update()
        .first()
    )

    if not workflow_request:
        return None

    request_data = dict(workflow_request.request_data or {})
    request_data["employee_remark"] = employee_remark
    request_data["decision"] = "NOT_CONFIRM"
    request_data["nodal_remark"] = None

    workflow_request.request_data = request_data
    workflow_request.current_assignee_role_id = (settings.SCANNED_SB_ASSIGNEE_ROLE_ID)
    workflow_request.current_assignee_id = subcadre_id
    workflow_request.current_step = 1
    workflow_request.submitted_at = datetime.now()

    return workflow_request
