import logging
import shutil
import os
from helpers.thread_executer import execute_in_new_thread
from helpers.db_operations import create_user_agreement_status, update_agreement_status, store_final_pdf
from helpers.email_helper import send_email_with_attachment
from helpers.websocket_helper import (
    listen_for_approval,
    ConnectionClosedError,
    ApprovalResult,
)
from langchain.agents import initialize_agent, Tool, AgentType
from helpers.rent_agreement_generator import create_pdf
from helpers.rent_agreement_generator import llm, memory, graph
from templates import format_agreement_details
from helpers.state_manager import state_manager
from fastapi import HTTPException
from pydantic import BaseModel
import os
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from constants import MAX_RETRIES, RETRY_DELAY
from datetime import datetime
import base64
from prisma.enums import AgreementStatus
from typing import List, Dict
from prompts import PREFIX, FORMAT_INSTRUCTIONS, SUFFIX
import uuid
from models.rental_agreement import AgreementRequest

logging.basicConfig(level=logging.INFO)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

def run_agreement_tool(user_input: str, agreement_id: int) -> str:
    state = {
        "messages": [("user", user_input)],
        "agreement_id": agreement_id
    }
    for event in graph.stream(state):
        if "create_pdf" in event:
            output = event["create_pdf"].get("messages", "No messages found")
            return output
    return "Failed to generate agreement"


# Define Tool
def create_tool_with_agreement_id(agreement_id):
    return [
        Tool(
            name="generate_agreement",
            func=lambda user_input: run_agreement_tool(user_input, agreement_id),
            description="Generate a rental agreement PDF from the provided details. Output only the agreement text.",
        )
    ]


def delete_temp_file(current_state):
    """Deletes the temporary agreement file if it exists."""
    try:
        if current_state.pdf_file_path and os.path.exists(
            current_state.pdf_file_path
        ):
            os.remove(current_state.pdf_file_path)
            logging.info(f"Temporary file deleted: {current_state.pdf_file_path}")
        else:
            logging.info(f"Temp file not found: {current_state.pdf_file_path}")
    except Exception as e:
        logging.info(f"Error deleting temp file: {str(e)}")

def delete_temp_images(current_state):
    """Removes only the image files associated with the current agreement."""
    
    files_to_delete = [
        current_state.owner_photo,
        current_state.owner_signature
    ]
    
    # Add tenant photos and signatures
    files_to_delete.extend(current_state.tenant_photos.values())
    files_to_delete.extend(current_state.tenant_signatures.values())

    for file_path in files_to_delete:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")


def save_base64_image(photo_data: str, user_id: str, is_signature: bool = False) -> str:
    if photo_data.startswith("data:image/jpeg;base64,"):
        file_ext = "jpg"
        photo_data = photo_data.replace("data:image/jpeg;base64,", "")
    elif photo_data.startswith("data:image/png;base64,"):
        file_ext = "png"
        photo_data = photo_data.replace("data:image/png;base64,", "")
    else:
        return ""

    photo_bytes = base64.b64decode(photo_data)
    save_dir = "./utils"
    os.makedirs(save_dir, exist_ok=True)

    unique_id = uuid.uuid4().hex
    
    if is_signature:
        photo_path = f"{save_dir}/{user_id}_signature_{unique_id}.{file_ext}"
    else:
        photo_path = f"{save_dir}/{user_id}_photo_{unique_id}.{file_ext}"

    with open(photo_path, "wb") as photo_file:
        photo_file.write(photo_bytes)

    return photo_path

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            " You are a helpful assistant to Generate a rental agreement from the provided details. Output only the agreement text",
        ),
        ("user", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

def log_before_retry(retry_state):
    attempt = retry_state.attempt_number
    logging.info(f"Retry attempt {attempt}: Retrying agreement generation...")

    if retry_state.args:
        agreement_id = retry_state.args[2]
        current_state = state_manager.get_agreement_state(agreement_id)
        delete_temp_file(current_state)



def log_after_failure(retry_state):
    exception = retry_state.outcome.exception()
    logging.info(
        f"Agreement generation failed after {retry_state.attempt_number} attempts : {str(exception)}"
    )


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_fixed(RETRY_DELAY),
    retry=retry_if_exception_type(Exception),
    before_sleep=log_before_retry,
    after=log_after_failure,
)

def generate_agreement_with_retry(agent, agreement_details, agreement_id):
    try:
        response = agent.invoke(agreement_details)
        if not response:
            raise ValueError("Empty response from LLM")
        return response
    except Exception as e:
        logging.info(f"Error while invoking agent for agreement_id {agreement_id}: {str(e)}")
        return None

async def create_agreement_details(
    request: AgreementRequest, agreement_id: int, db: object
):
    try:
        state_manager.set_current_agreement_id(agreement_id)
        current_state = state_manager.get_agreement_state(agreement_id)
        current_state.set_owner(request.owner_name, request.owner_email)
        current_state.set_agreement_details(request)
        tools = create_tool_with_agreement_id(agreement_id)

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=memory,
            max_iterations=1,
            early_stopping_method="generate",
            agent_kwargs={
                "prefix": PREFIX,
                "format_instructions": FORMAT_INSTRUCTIONS,
                "suffix": SUFFIX,
                "prompt": prompt,
            },
        )


        # Store tenant details
        tenants = []
        for tenant in request.tenant_details:
            tenant_id = current_state.add_tenant(
                tenant["email"],
                tenant["name"],
            )
            tenants.append((tenant_id, tenant["email"]))

        # Store witness details
        witnesses = []
        for witness in request.witness_details:
            witness_id = current_state.add_witness(
                witness["email"],
                witness["name"],
            )
            witnesses.append((witness_id, witness["email"]))

        # Format agreement details
        agreement_details = format_agreement_details(
            owner_name=request.owner_name,
            tenant_details=request.tenant_details,
            property_address=request.property_address,
            city=request.city,
            rent_amount=request.rent_amount,
            agreement_period=[date.isoformat() for date in request.agreement_period],
            owner_address=request.owner_address,
            furnishing_type=request.furnishing_type,
            security_deposit=request.security_deposit,
            bhk_type=request.bhk_type,
            area=request.area,
            registration_date=request.registration_date,
            amenities=request.amenities,
        )

        try:
            response = await execute_in_new_thread(
                generate_agreement_with_retry, agent, agreement_details, agreement_id
            )
        except Exception as e:
            await update_agreement_status(db, agreement_id, AgreementStatus.FAILED)
            raise HTTPException(
                status_code=500,
                detail=f"Error generating agreement after {MAX_RETRIES} attempts: {str(e)}",
            )

        owner_success, _ = send_email_with_attachment(
            request.owner_email, current_state.pdf_file_path, "owner", agreement_id, False
        )
        tenant_successes = []
        for tenant_id, tenant_email in tenants:
            success, _ = send_email_with_attachment(
                tenant_email, current_state.pdf_file_path, "tenant", agreement_id, False, tenant_id
            )
            tenant_successes.append(success)

        witness_successes = []
        for witness_id, witness_email in witnesses:
            success, _ = send_email_with_attachment(
                witness_email, current_state.pdf_file_path, "witness", agreement_id, False, witness_id
            )
            witness_successes.append(success)

        current_state.is_pdf_generated = True

        if owner_success and all(tenant_successes) and all(witness_successes):
            delete_temp_file(current_state)
            try:
                # Wait for approvals
                approval_result = await listen_for_approval(
                    timeout_seconds=500, is_template=False, agreement_id=agreement_id
                )

                if approval_result == ApprovalResult.APPROVED:
                    # Mark as approved and generate final PDF with signatures
                    current_state.owner_approved = True
                    for tenant_id in current_state.tenants:
                        current_state.tenants[tenant_id] = True
                    for witness_id in current_state.witnesses:
                        current_state.witnesses[witness_id] = True
                    # Generate final PDF with signatures and get the path
                    create_pdf(current_state)
                    final_pdf_path = current_state.pdf_file_path

                    # Send final agreement with replaced signatures/photos
                    owner_success, _ = send_email_with_attachment(
                        request.owner_email, final_pdf_path, "owner", agreement_id, False
                    )
                    for tenant_id, tenant_email in tenants:
                        send_email_with_attachment(
                            tenant_email, final_pdf_path, "tenant", agreement_id, False, tenant_id
                        )
                    for witness_id, witness_email in witnesses:
                        send_email_with_attachment(
                            witness_email, final_pdf_path, "witness", agreement_id, False, witness_id
                        )
                    # Stores final agreement pdf in db
                    await store_final_pdf(db, agreement_id, current_state.pdf_file_path)
                    delete_temp_file(current_state)
                    delete_temp_images(current_state)
                    state_manager.cleanup_agreement_state(agreement_id)
                    return {
                        "message": "Final signed agreement with signatures sent to all parties!"
                    }
                elif approval_result == ApprovalResult.REJECTED:
                    # If explicitly rejected
                    await update_agreement_status(db, agreement_id, AgreementStatus.REJECTED)
                    await create_user_agreement_status(db, current_state.owner_id, agreement_id, AgreementStatus.REJECTED)
                    for tenant_id, _ in tenants:
                        await create_user_agreement_status(db, tenant_id, agreement_id, AgreementStatus.REJECTED)
                    for witness_id, _ in witnesses:
                        await create_user_agreement_status(db, witness_id, agreement_id, AgreementStatus.REJECTED)

                    delete_temp_file(current_state)
                    delete_temp_images(current_state)
                    state_manager.cleanup_agreement_state(agreement_id)
                    return {"message": "Agreement was rejected by one or more parties."}

                elif approval_result == ApprovalResult.EXPIRED:
                    # ApprovalResult.EXPIRED
                    await update_agreement_status(db, agreement_id, AgreementStatus.EXPIRED)
                    await create_user_agreement_status(db, current_state.owner_id, agreement_id, AgreementStatus.EXPIRED)
                    for tenant_id, _ in tenants:
                        await create_user_agreement_status(db, tenant_id, agreement_id, AgreementStatus.EXPIRED)
                    for witness_id, _ in witnesses:
                        await create_user_agreement_status(db, witness_id, agreement_id, AgreementStatus.EXPIRED)

                    delete_temp_file(current_state)
                    delete_temp_images(current_state)
                    state_manager.cleanup_agreement_state(agreement_id)
                    return {
                        "message": "Agreement was expired due to no action taken by one or more parties within 5 minutes."
                    }

                else:
                    # ApprovalResult.CONNECTION_CLOSED
                    await update_agreement_status(db, agreement_id, AgreementStatus.FAILED)
                    await create_user_agreement_status(db, current_state.owner_id, agreement_id, AgreementStatus.FAILED)
                    for tenant_id, _ in tenants:
                        await create_user_agreement_status(db, tenant_id, agreement_id, AgreementStatus.FAILED)
                    for witness_id, _ in witnesses:
                        await create_user_agreement_status(db, witness_id, agreement_id, AgreementStatus.FAILED)

                    delete_temp_file(current_state)
                    delete_temp_images(current_state)
                    state_manager.cleanup_agreement_state(agreement_id)
                    return {
                        "message": "Agreement process failed due to connection issues."
                    }

            except ConnectionClosedError as e:
                # Update status to FAILED on connection closed
                await update_agreement_status(db, agreement_id, AgreementStatus.FAILED)
                await create_user_agreement_status(db, current_state.owner_id, agreement_id, AgreementStatus.FAILED)
                for tenant_id, _ in tenants:
                    await create_user_agreement_status(db, tenant_id, agreement_id, AgreementStatus.FAILED)
                for witness_id, _ in witnesses:
                    await create_user_agreement_status(db, witness_id, agreement_id, AgreementStatus.FAILED)

                delete_temp_file(current_state)
                delete_temp_images(current_state)
                state_manager.cleanup_agreement_state(agreement_id)
                return {
                    "message": "Agreement process failed: Connection closed unexpectedly"
                }
        else:
            await update_agreement_status(db, agreement_id, AgreementStatus.FAILED)
            return {"message": "Error sending initial agreement emails."}

    except Exception as e:
        await update_agreement_status(db, agreement_id, AgreementStatus.FAILED)
        await create_user_agreement_status(db, current_state.owner_id, agreement_id, AgreementStatus.FAILED)
        for tenant_id, _ in tenants:
            await create_user_agreement_status(db, tenant_id, agreement_id, AgreementStatus.FAILED)
        for witness_id, _ in witnesses:
            await create_user_agreement_status(db, witness_id, agreement_id, AgreementStatus.FAILED)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
    finally:
        delete_temp_images(current_state)
        state_manager.cleanup_agreement_state(agreement_id)
