from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import role_config
from app.models.employee import Employee
from app.models.scanned_service_book import (CDREhrmsUpload,EhrmsWorkflowRequest,)
from app.schemas.scanned_service_book import NodalNoChangesRequest



def get_latest_scanned_service_book_upload(db: Session, employee_id: int, upload_status: int | None = None,) -> CDREhrmsUpload | None:
    """Return the latest scanned service book upload for an employee."""
    query = db.query(CDREhrmsUpload).filter(
        CDREhrmsUpload.category_id == 1,
        CDREhrmsUpload.entity_id == employee_id,
    )

    if upload_status is not None:
        query = query.filter(CDREhrmsUpload.status == upload_status)

    return query.order_by(CDREhrmsUpload.id.desc()).first()


def process_nodal_decision(request_year_month: int, request_id: int,nodal_subcadre_id: int | None,payload: NodalNoChangesRequest, db: Session, ):
    """Process a Nodal Officer decision and return upload status and assignee role."""

    request = (
        db.query(EhrmsWorkflowRequest)
        .filter(
            EhrmsWorkflowRequest.id == request_id,
            EhrmsWorkflowRequest.request_year_month == request_year_month,
            EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID,
        )
        .with_for_update()
        .first()
    )

    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Workflow request not found",)

    if (request.current_status != 2 or request.current_assignee_role_id != role_config.NODAL_ROLE_ID):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This request is not awaiting Nodal Officer action",)

    employee_id = request.employee_id

    employee = (db.query(Employee).filter(Employee.employee_id == employee_id).first())

    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Employee not found",)

    if employee.subcadre_id != nodal_subcadre_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="You cannot process requests outside your sub-cadre",)

    request_data = dict(request.request_data or {})
    upload_id = request_data.get("upload_id")

    if upload_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="The workflow request has no associated upload",)

    upload = (
        db.query(CDREhrmsUpload)
        .filter(
            CDREhrmsUpload.id == upload_id,
            CDREhrmsUpload.category_id == 1,
            CDREhrmsUpload.entity_id == employee_id,
        )
        .with_for_update()
        .first()
    )

    if upload is None or upload.status != 6:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="The associated upload is not awaiting review",)

    request_data["nodal_action"] = payload.action
    request_data["nodal_remark"] = payload.remark
    request.request_data = request_data

    request.current_assignee_role_id = role_config.EMPLOYEE_ROLE_ID
    request.current_assignee_id = employee_id
    upload.status = 4

    # return upload.status, request.current_assignee_role_id
    return (
        employee_id,
        upload.status,
        request.current_assignee_role_id,
    )
