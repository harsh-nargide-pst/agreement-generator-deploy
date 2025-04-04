from helpers.state_manager import state_manager
from services.doc_agent import save_base64_image
from pydantic import BaseModel
from typing import Optional


class Data(BaseModel):
    user: str
    imageUrl: Optional[str] = ""
    signature: Optional[str] = ""
    agreement_type: str
    agreement_id: int


async def image_and_sign_upload(agreement: Data):
    current_state = state_manager.get_agreement_state(agreement.agreement_id)
    if agreement.user == current_state.owner_id:
        current_state.owner_photo = save_base64_image(
            agreement.imageUrl, current_state.owner_name
        )
        current_state.owner_signature = save_base64_image(
            agreement.signature, current_state.owner_name, is_signature=True
        )

    elif agreement.user in current_state.tenants.keys():
        tenant_photo_path = save_base64_image(
            agreement.imageUrl, current_state.tenant_names[agreement.user]
        )
        tenant_signature_path = save_base64_image(
            agreement.signature,
            current_state.tenant_names[agreement.user],
            is_signature=True,
        )
        current_state.update_tenant(
            tenant_signature_path, tenant_photo_path, agreement.user
        )
    elif agreement.user in current_state.witnesses.keys():
        witness_photo_path = save_base64_image(
            agreement.imageUrl, current_state.witness_names[agreement.user]
        )
        witness_signature_path = save_base64_image(
            agreement.signature,
            current_state.witness_names[agreement.user],
            is_signature=True,
        )
        current_state.update_witness(
            witness_signature_path, witness_photo_path, agreement.user
        )


async def image_and_sign_upload_for_template(agreement: Data):
    current_template_state = state_manager.get_template_agreement_state(
        agreement.agreement_id
    )
    if agreement.user == current_template_state.authority_id:
        current_template_state.authority_signature = save_base64_image(
            agreement.signature,
            current_template_state.authority_email,
            is_signature=True,
        )

    elif agreement.user == current_template_state.participant_id:
        current_template_state.participant_signature = save_base64_image(
            agreement.signature,
            current_template_state.participant_email,
            is_signature=True,
        )
