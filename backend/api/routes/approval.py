import os
import shutil
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from api.routes.websocket import notify_clients
from helpers.email_helper import send_rejection_email
from helpers.state_manager import AgreementState, TemplateAgreementState, state_manager
from services.doc_agent import delete_temp_file, delete_temp_images
from services.template_doc_agent import (
    delete_template_file,
    delete_template_temp_images,
)
from services.image_sign_upload import (
    Data,
    image_and_sign_upload,
    image_and_sign_upload_for_template,
)
from database.connection import get_db
from prisma import Prisma
from auth.clerk_auth import requires_auth
from prisma.enums import AgreementStatus

router = APIRouter()
approved_users = set()
rejected_users = set()


@router.post("/approve")
@requires_auth
async def approve_user(data: Data, request: Request, db: Prisma = Depends(get_db)):
    agreement_type = data.agreement_type
    if agreement_type == "template":
        await image_and_sign_upload_for_template(data)
        await db.useragreementstatus.create(
            data={
                "status": AgreementStatus.APPROVED,
                "agreementId": data.agreement_id,
                "userId": data.user,
            }
        )
    else:
        await image_and_sign_upload(data)
        await db.userrentagreementstatus.create(
            data={
                "status": AgreementStatus.APPROVED,
                "agreementId": data.agreement_id,
                "userId": data.user,
            }
        )

    approved_users.add(data.user)
    response = {
        "status": AgreementStatus.APPROVED,
        "user_id": data.user,
        "approved": True,
        "agreement_type": agreement_type,
    }
    await notify_clients(response)
    return JSONResponse(content=response)


@router.post("/reject")
@requires_auth
async def reject_user(data: Data, request: Request, db: Prisma = Depends(get_db)):
    rejected_users.add(data.user)
    agreement_type = data.agreement_type
    if agreement_type == "rent":
        await db.userrentagreementstatus.create(
            data={
                "status": AgreementStatus.REJECTED,
                "agreementId": data.agreement_id,
                "userId": data.user,
            }
        )
    else:
        await db.useragreementstatus.create(
            data={
                "status": AgreementStatus.REJECTED,
                "agreementId": data.agreement_id,
                "userId": data.user,
            }
        )

    # Determine the role and name of the person who rejected
    rejected_by_name = None
    rejected_by_role = None

    current_state = (
        state_manager.get_agreement_state(data.agreement_id)
        if data.agreement_type == "rent"
        else state_manager.get_template_agreement_state(data.agreement_id)
    )

    if isinstance(current_state, AgreementState):
        if data.user == current_state.owner_id:
            rejected_by_name = current_state.owner_name
            rejected_by_role = "owner"
        elif data.user in current_state.tenants:
            rejected_by_name = current_state.tenant_names[data.user]
            rejected_by_role = "tenant"
        elif data.user in current_state.witnesses:
            rejected_by_name = current_state.witness_names[data.user]
            rejected_by_role = "witness"
    elif isinstance(current_state, TemplateAgreementState):
        if data.user == current_state.authority_id:
            rejected_by_name = "Authority"
        elif data.user == current_state.participant_id:
            rejected_by_name = "Participant"

    # Send rejection notifications to all parties
    if rejected_by_name and rejected_by_role:
        send_rejection_email(
            agreement_id=data.agreement_id,
            rejected_by_name=rejected_by_name,
            rejected_by_role=rejected_by_role,
            is_template=False,
        )
        delete_temp_file(current_state)
        delete_temp_images(current_state)
    elif rejected_by_name:
        send_rejection_email(
            agreement_id=data.agreement_id,
            rejected_by_name=rejected_by_name,
            is_template=True,
        )
        delete_temp_file(current_state)
        delete_template_file(current_state)
        delete_template_temp_images(current_state)

    response = {
        "status": AgreementStatus.REJECTED,
        "user_id": data.user,
        "approved": False,
        "agreement_type": agreement_type,
    }
    await notify_clients(response)
    return JSONResponse(content=response)
