from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.database.session import get_db
from app.models.scanned_service_book import (CDREhrmsUpload, EhrmsWorkflowRequest,)
from app.models.employee import Employee
from app.core.token import get_current_user
from app.schemas.scanned_service_book import (
    ServiceBookNotificationResponse,
    ServiceBookDetailsResponse,
    ServiceBookDecisionResponse,
    ServiceBookEmployeeResponse,
    NodalNoChangesRequest,
    NodalDecisionResponse,
    NodalPendingRequestsResponse,
    NodalPendingRequestItem,
)
from app.core.config import settings
from app.core.roles import role_config

from app.services.workflow_service import (find_active_employee_workflow,archive_workflow_request,create_scanned_sb_workflow,reuse_returned_workflow,)
from app.services.scanned_service_book_service import (get_latest_scanned_service_book_upload, process_nodal_decision,)

from app.core.cache import get_cached_response, set_cached_response, invalidate_employee_cache, invalidate_service_book_notification_cache

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scanned-service-book",tags=["Scanned Service Book"],)


@router.get("/notification", response_model=ServiceBookNotificationResponse)
def get_service_book_notification( current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):

    employee_id = current_user["employee_id"]

    cache_key = f"scanned_sb:notification:{employee_id}"

    # 1. Try Redis first.
    cached_response = get_cached_response(cache_key,ServiceBookNotificationResponse,)

    if cached_response is not None:
        return cached_response

    # 2. Query PostgreSQL on cache miss.
    upload = get_latest_scanned_service_book_upload(db=db,employee_id=employee_id,)

    # 3. Find the active workflow request returned to this employee.
    workflow_request = None

    if upload is not None:
        workflow_request = (
            db.query(EhrmsWorkflowRequest)
            .filter(
                EhrmsWorkflowRequest.employee_id == employee_id,
                EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID,
                EhrmsWorkflowRequest.current_status == 2,
                EhrmsWorkflowRequest.current_assignee_role_id == role_config.EMPLOYEE_ROLE_ID,
                EhrmsWorkflowRequest.request_data["upload_id"].as_integer() == upload.id,
            )
            .order_by(
                EhrmsWorkflowRequest.updated_at.desc(),
                EhrmsWorkflowRequest.id.desc(),
            )
            .first()
        )

    # 4. Get the Nodal Officer's remark, if available.
    remark = None

    if workflow_request is not None:
        request_data = workflow_request.request_data or {}
        remark = request_data.get("nodal_remark")

    # 3. Show popup only when status is 4.
    response = ServiceBookNotificationResponse(
        status=True,
        notification_popup = upload is not None and upload.status == 4,
        remark=remark,
    )

    # 4. Cache the response using your existing TTL.
    set_cached_response(cache_key, response)
    return response


@router.get("/details", response_model=ServiceBookDetailsResponse,)
def get_service_book_details(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):

    # 1 Employee identity comes from the verified JWT.
    employee_id = current_user["employee_id"]

    # This endpoint is intended for the employee's own page.
    if current_user["role_id"] != role_config.EMPLOYEE_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employees can access their Service Book details",)

    # 2 Get the latest scanned Service Book upload for this employee.
    upload = get_latest_scanned_service_book_upload(db=db,employee_id=employee_id,upload_status=4,)

    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanned Service Book not found",)

    # 3. Find the active workflow request returned to this employee.
    workflow_request = (
        db.query(EhrmsWorkflowRequest)
        .filter(
            EhrmsWorkflowRequest.employee_id == employee_id,
            EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID,
            EhrmsWorkflowRequest.current_status == 2,
            EhrmsWorkflowRequest.current_assignee_role_id == role_config.EMPLOYEE_ROLE_ID,
            EhrmsWorkflowRequest.request_data["upload_id"].as_integer() == upload.id,
        )
        .order_by(EhrmsWorkflowRequest.updated_at.desc(), EhrmsWorkflowRequest.id.desc(),)
        .first()
    )

    # 4. Get the Nodal Officer's remark, if available.
    remark = None

    if workflow_request is not None:
        request_data = workflow_request.request_data or {}
        remark = request_data.get("nodal_remark")

    # 5. Return upload details and the Nodal Officer's remark.
    return ServiceBookDetailsResponse(
        status=True,
        s3_key=upload.s3_key,
        category_id=upload.category_id,
        entity_id=upload.entity_id,
        upload_status=upload.status,
        remark=remark,
    )


@router.post("/decision",response_model=ServiceBookDecisionResponse,)
def submit_service_book_decision( payload: ServiceBookEmployeeResponse, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):

    employee_id = current_user["employee_id"]
    subcadre_id = current_user["subcadre_id"]

    # Only employees can submit this decision.
    if current_user["role_id"] != role_config.EMPLOYEE_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only employees can submit a Service Book decision",)

    # Find the latest scanned Service Book upload.
    upload = get_latest_scanned_service_book_upload(db=db,employee_id=employee_id,)

    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanned Service Book not found",)

    # The employee can respond only to an upload awaiting confirmation.
    if upload.status != 4:
        if upload.status == 6:
            message = "This Service Book has already been submitted for review"
        elif upload.status == 5:
            message = "This Service Book has already been confirmed"
        else:
            message = "This Service Book is not awaiting confirmation"

        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=message,)

    workflow_request_created = False

    try:
        if payload.decision == "CONFIRM":

            # Find the active request returned to this employee
            workflow_request = find_active_employee_workflow(employee_id=employee_id,upload_id=upload.id,db=db,)

            # Archive only if a request was returned to the employee
            if workflow_request:
                archive_workflow_request(workflow_request,db,)

            upload.status = 5
            request_id = None
            request_year_month = None
        else:
            remark = (payload.remark or "").strip()

            if not remark:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Remark is required when the Service Book is not confirmed",)

            # Prevent another active submitted request for this employee.
            existing_request = (db.query(EhrmsWorkflowRequest)
                .filter(EhrmsWorkflowRequest.employee_id == employee_id,
                        EhrmsWorkflowRequest.module_id == settings.SCANNED_SB_MODULE_ID, 
                        EhrmsWorkflowRequest.current_status == 2,
                        EhrmsWorkflowRequest.current_assignee_role_id == role_config.NODAL_ROLE_ID,
                        )
                .first()
            )

            if existing_request is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active Service Book request already exists",)

            # Try to reuse a request returned to the employee.
            workflow_request = reuse_returned_workflow(
                employee_id=employee_id,
                upload_id=upload.id,
                employee_remark=remark,
                subcadre_id=subcadre_id,
                db=db,
            )

            if workflow_request is None:
                workflow_request = create_scanned_sb_workflow(
                    employee_id=employee_id,
                    subcadre_id=subcadre_id,
                    upload_id=upload.id,
                    category_id=upload.category_id,
                    entity_id=upload.entity_id,
                    employee_remark=remark,
                    db=db,
                )
            if workflow_request is None:
                raise RuntimeError("Workflow creation/reuse returned None")

            request_id = workflow_request.id
            request_year_month = workflow_request.request_year_month
            upload.status = 6
            workflow_request_created = True

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    # except Exception:
    #     db.rollback()
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to save the Service Book decision",)
    
    except Exception:
        db.rollback()

        logger.exception(
            "Failed to save Service Book decision. employee_id=%s, decision=%s",
            employee_id,
            payload.decision,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the Service Book decision",
        )

    # Clear cached notification only after the transaction succeeds.
    invalidate_service_book_notification_cache(employee_id)

    return ServiceBookDecisionResponse(
        status=True,
        message=("Service Book confirmed successfully" if payload.decision == "CONFIRM" else "Service Book issue submitted successfully" ),
        upload_status=upload.status,
        workflow_request_created=workflow_request_created,
        request_id=request_id,
        request_year_month=request_year_month,
    )


@router.post("/requests/{request_year_month}/{request_id}/nodal-decision", response_model=NodalDecisionResponse,)
def nodal_no_changes(request_year_month: int,request_id: int,payload: NodalNoChangesRequest,current_user: dict = Depends(get_current_user),db: Session = Depends(get_db),):

    if current_user["role_id"] != role_config.NODAL_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only Nodal Officers can process this request",)

    try:
        employee_id, upload_status, assignee_role_id = process_nodal_decision(
            request_year_month=request_year_month,
            request_id=request_id,
            nodal_subcadre_id=current_user["subcadre_id"],
            payload=payload,
            db=db,
        )
        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Unable to save the Nodal Officer decision",)

    # The service updates the request's employee assignment.
    if employee_id is not None:
        invalidate_service_book_notification_cache(employee_id)

    return NodalDecisionResponse(
        status=True,
        message="Request returned to employee successfully",
        upload_status=upload_status,
        current_assignee_role_id=assignee_role_id,
    )



@router.get("/nodal/pending-requests", response_model=NodalPendingRequestsResponse,)
def get_nodal_pending_requests(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db),):
    
    # Only Nodal Officers can view pending requests.
    if current_user["role_id"] != role_config.NODAL_ROLE_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Nodal Officers can view pending requests",)

    # Sub-cadre must come from the authenticated user's JWT.
    subcadre_id = current_user.get("subcadre_id")

    if subcadre_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sub-cadre information is missing for the logged-in user",)

    # Fetch only active requests assigned to this sub-cadre's
    # Nodal Officer workflow.
    results = (
        db.query(EhrmsWorkflowRequest, Employee)
        .join(
            Employee,
            Employee.employee_id == EhrmsWorkflowRequest.employee_id,
        )
        .filter(
            EhrmsWorkflowRequest.module_id
            == settings.SCANNED_SB_MODULE_ID,
            EhrmsWorkflowRequest.current_status == 2,
            EhrmsWorkflowRequest.current_assignee_role_id
            == role_config.NODAL_ROLE_ID,
            EhrmsWorkflowRequest.current_assignee_id == subcadre_id,
            Employee.subcadre_id == subcadre_id,
        )
        .order_by(EhrmsWorkflowRequest.submitted_at.asc())
        .all()
    )

    requests = []

    for workflow_request, employee in results:
        request_data = workflow_request.request_data or {}

        requests.append(
            NodalPendingRequestItem(
                request_id=workflow_request.id,
                request_year_month=workflow_request.request_year_month,
                employee_id=workflow_request.employee_id,
                employee_code=getattr(employee, "employee_code", None),
                employee_name=getattr(employee, "full_name", None),
                employee_remark=request_data.get("employee_remark"),
                submitted_at=workflow_request.submitted_at,
            )
        )

    return NodalPendingRequestsResponse(
        status=True,
        total=len(requests),
        requests=requests,
    )
