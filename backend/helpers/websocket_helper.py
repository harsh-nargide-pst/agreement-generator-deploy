import asyncio
from datetime import datetime
import websockets
import json
import os
import logging
from helpers.state_manager import state_manager
from config import WEBSOCKET_URL
from enum import Enum


class ApprovalTimeoutError(Exception):
    pass


class ConnectionClosedError(Exception):
    pass


class ApprovalResult(Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONNECTION_CLOSED = "connection_closed"


# Configure logging
logging.basicConfig(level=logging.INFO)


async def listen_for_approval(
    timeout_seconds: int = 300, is_template: bool = False, agreement_id: str = None
) -> ApprovalResult:
    """
    Listen for approval messages with a timeout.
    Args:
        timeout_seconds: Maximum time to wait for approvals (default 5 minutes)
    Returns:
        ApprovalResult: APPROVED if all parties approved, REJECTED if explicitly rejected,
                       CONNECTION_CLOSED if connection issues occurred
    Raises:
        ApprovalTimeoutError: If no response received within timeout period
    """
    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            while True:
                try:
                    # Set timeout for receiving messages
                    response = await asyncio.wait_for(
                        websocket.recv(), timeout=timeout_seconds
                    )
                    data = json.loads(response)
                    logging.info(f"Received approval response: {data}")

                    user_id = data.get("user_id")
                    if is_template:
                        current_template_state = (
                            state_manager.get_template_agreement_state(agreement_id)
                        )
                        if user_id == current_template_state.participant_id:
                            current_template_state.participant_approved = data.get(
                                "approved", False
                            )
                            if current_template_state.participant_approved:
                                participant_signature_path = (
                                    current_template_state.participant_signature
                                )
                                if os.path.isfile(participant_signature_path):
                                    current_template_state.participant_signature = (
                                        participant_signature_path
                                    )
                                else:
                                    current_template_state.participant_signature = (
                                        f"APPROVED BY PARTICIPANT - {datetime.now()}"
                                    )
                                print("Participant has approved!")
                            else:
                                print("Participant has rejected!")
                                return ApprovalResult.REJECTED

                        elif user_id == current_template_state.authority_id:
                            current_template_state.authority_approved = data.get(
                                "approved", False
                            )
                            if current_template_state.authority_approved:
                                authority_signature_path = (
                                    current_template_state.authority_signature
                                )
                                if os.path.isfile(authority_signature_path):
                                    current_template_state.authority_signature = (
                                        authority_signature_path
                                    )
                                else:
                                    current_template_state.authority_signature = (
                                        f"APPROVED BY AUTHORITY - {datetime.now()}"
                                    )
                                print("Authority has approved!")
                            else:
                                print("Authority has rejected!")
                                return ApprovalResult.REJECTED
                    else:
                        current_state = state_manager.get_agreement_state(agreement_id)
                        if user_id in current_state.tenants:
                            current_state.tenants[user_id] = data.get("approved", False)
                            if current_state.tenants[user_id]:
                                tenant_name = current_state.tenant_names[user_id]
                                logging.info(
                                    f"Tenant {tenant_name} ({user_id}) has approved the agreement."
                                )
                                tenant_signature_path = current_state.tenant_signatures[
                                    user_id
                                ]
                                if os.path.isfile(tenant_signature_path):
                                    current_state.tenant_signatures[user_id] = (
                                        tenant_signature_path
                                    )
                                else:
                                    current_state.tenant_signatures[user_id] = (
                                        f"APPROVED BY {tenant_name} - {datetime.now()}"
                                    )

                                tenant_photo_path = current_state.tenant_photos[user_id]
                                if os.path.isfile(tenant_photo_path):
                                    current_state.tenant_photos[user_id] = (
                                        tenant_photo_path
                                    )
                                else:
                                    current_state.tenant_photos[user_id] = (
                                        f"{tenant_name}"
                                    )
                            else:
                                logging.warning(f"Tenant {user_id} has rejected!")
                                return ApprovalResult.REJECTED

                        elif user_id == current_state.owner_id:
                            current_state.owner_approved = data.get("approved", False)
                            if current_state.owner_approved:
                                logging.info(
                                    f"Owner {current_state.owner_name} ({user_id}) has approved the agreement."
                                )
                                owner_signature_path = current_state.owner_signature
                                if os.path.exists(owner_signature_path):
                                    current_state.owner_signature = owner_signature_path
                                else:
                                    current_state.owner_signature = f"APPROVED BY {current_state.owner_name} - {datetime.now()}"

                                owner_photo_path = current_state.owner_photo
                                if os.path.exists(owner_photo_path):
                                    current_state.owner_photo = owner_photo_path
                                else:
                                    current_state.owner_photo = (
                                        f"{current_state.owner_name}"
                                    )
                            else:
                                logging.warning("Owner has rejected!")
                                return ApprovalResult.REJECTED

                        elif user_id in current_state.witnesses:
                            current_state.witnesses[user_id] = data.get("approved", False)
                            if current_state.witnesses[user_id]:
                                witness_name = current_state.witness_names[user_id]
                                logging.info(
                                    f"Witness {witness_name} ({user_id}) has approved the agreement."
                                )
                                witness_signature_path = current_state.witness_signatures[
                                    user_id
                                ]
                                if os.path.isfile(witness_signature_path):
                                    current_state.witness_signatures[user_id] = (
                                        witness_signature_path
                                    )
                                else:
                                    current_state.witness_signatures[user_id] = (
                                        f"APPROVED BY {witness_name} - {datetime.now()}"
                                    )

                                witness_photo_path = current_state.witness_photos[user_id]
                                if os.path.isfile(witness_photo_path):
                                    current_state.witness_photos[user_id] = (
                                        witness_photo_path
                                    )
                                else:
                                    current_state.witness_photos[user_id] = (
                                        f"{witness_name}"
                                    )
                            else:
                                logging.warning(f"Witness {user_id} has rejected!")
                                return ApprovalResult.REJECTED

                    # Check if both parties have responded
                    if is_template:
                        if current_template_state.is_fully_approved():
                            logging.info(
                                "Agreement successfully approved by Authority and Participant."
                            )
                            return ApprovalResult.APPROVED
                    else:
                        if current_state.is_fully_approved():
                            logging.info(
                                "Agreement successfully approved by Owner, Tenants, and Witnesses."
                            )
                            return ApprovalResult.APPROVED

                except asyncio.TimeoutError:
                    logging.error("Approval process timed out")
                    return ApprovalResult.EXPIRED
                except json.JSONDecodeError as e:
                    logging.error(f"Invalid JSON received: {e}")
                    continue
    except websockets.exceptions.ConnectionClosed:
        logging.error("WebSocket connection closed unexpectedly")
        return ApprovalResult.CONNECTION_CLOSED
    except websockets.exceptions.WebSocketException as e:
        logging.error(f"WebSocket error: {str(e)}")
        return ApprovalResult.CONNECTION_CLOSED
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return ApprovalResult.CONNECTION_CLOSED
