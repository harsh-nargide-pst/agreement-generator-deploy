import base64
import requests
from constants import SMTP2GO_EMAIL_SEND_URL
from config import SMTP2GO_API_KEY, SENDER_EMAIL
from helpers.state_manager import state_manager
from templates import generate_email_template


def send_rejection_email(
    agreement_id: str,
    rejected_by_name: str,
    rejected_by_role: str = None,
    is_template: bool = False,
):
    """Send rejection notification emails to all parties involved in the agreement."""
    # Get all email addresses
    emails_to_notify = []

    if is_template:
        current_state = state_manager.get_template_agreement_state(agreement_id)
        if hasattr(current_state, "authority_email") and current_state.authority_email:
            emails_to_notify.append(
                (
                    current_state.authority_email,
                    "Authority",
                    current_state.authority_id,
                )
            )
        if (
            hasattr(current_state, "participant_email")
            and current_state.participant_email
        ):
            emails_to_notify.append(
                (
                    current_state.participant_email,
                    "Participant",
                    current_state.participant_id,
                )
            )

    else:
        current_state = state_manager.get_agreement_state(agreement_id)
        if hasattr(current_state, "owner_email") and current_state.owner_email:
            emails_to_notify.append(
                (current_state.owner_email, "owner", current_state.owner_id)
            )
        # Add all tenants' emails
        for tenant_id in current_state.tenants.keys():
            tenant_email = getattr(current_state, "tenant_emails", {}).get(tenant_id)
            if tenant_email:
                emails_to_notify.append((tenant_email, "tenant", tenant_id))
        # Add all witnesses' emails
        for witness_id in current_state.witnesses.keys():
            witness_email = getattr(current_state, "witness_emails", {}).get(witness_id)
            if witness_email:
                emails_to_notify.append((witness_email, "witness", witness_id))

    success_list = []
    failed_list = {}
    agreement_id = (
        current_state.agreement_id if is_template else current_state.agreement_id
    )

    for email, role, user_id in emails_to_notify:
        email_body = generate_email_template(
            role=role,
            user_id=user_id,
            agreement_id=agreement_id,
            is_rejection=True,
            rejected_by=(
                f"{rejected_by_name} ({rejected_by_role})"
                if rejected_by_name and rejected_by_role
                else rejected_by_name
            ),
        )

        payload = {
            "sender": SENDER_EMAIL,
            "to": [email],
            "subject": "Rental Agreement Rejected",
            "html_body": email_body,
        }

        headers = {
            "X-Smtp2go-Api-Key": SMTP2GO_API_KEY,
            "Content-Type": "application/json",
        }

        response = requests.post(SMTP2GO_EMAIL_SEND_URL, headers=headers, json=payload)

        if response.status_code == 200:
            print(f"Email sent successfully to {email}")
            success_list.append(email)
        else:
            print(f"Failed to send email to {email}: {response.text}")
            failed_list[email] = response.text

    return {"success": success_list, "failed": failed_list}


def send_email_with_attachment(
    recipient_email: str,
    pdf_path: str,
    role: str,
    agreement_id: str,
    is_template: bool = False,
    user_id=None,
):

    with open(pdf_path, "rb") as attachment_file:
        file_content = attachment_file.read()
        encoded_file = base64.b64encode(file_content).decode("utf-8")

    if is_template:
        current_state = state_manager.get_template_agreement_state(agreement_id)
        user_id = (
            current_state.participant_id
            if role == "Participant"
            else current_state.authority_id
        )
    else:
        current_state = state_manager.get_agreement_state(agreement_id)
        if role == "owner" or user_id is None:
            user_id = current_state.owner_id
    agreement_id = (
        current_state.agreement_id if is_template else current_state.agreement_id
    )
    email_body = generate_email_template(role, user_id, agreement_id, is_template)

    payload = {
        "sender": SENDER_EMAIL,
        "to": [recipient_email],
        "subject": (
            f"Agreement for {role.capitalize()}"
            if is_template
            else f"Rental Agreement for {role.capitalize()}"
        ),
        "html_body": email_body,
        "attachments": [
            {
                "fileblob": encoded_file,
                "filename": "agreement.pdf" if is_template else "rental-agreement.pdf",
                "content_type": "application/pdf",
            }
        ],
    }
    headers = {
        "X-Smtp2go-Api-Key": SMTP2GO_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(SMTP2GO_EMAIL_SEND_URL, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Successfully sent email to {recipient_email}")
    else:
        print(f"Failed to send email to {recipient_email}: {response.text}")
    return response.status_code == 200, response.text
