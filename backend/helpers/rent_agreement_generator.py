import tempfile
from constants import Model, CHAT_OPENAI_BASE_URL
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from helpers.state_manager import State, state_manager
import os
from PIL import Image
from templates import format_agreement_details
from prompts import AGREEMENT_SYSTEM_PROMPT
from typing import List, Dict
from helpers.agreement_generator_helper import create_pdf_file

os.environ["OPENAI_API_KEY"] = "XXX"

memory = ConversationBufferMemory(memory_key="chat_history")
llm = ChatOpenAI(
    model=Model.GPT_MODEL.value,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key="",
    base_url=CHAT_OPENAI_BASE_URL,
)


def generate_table(
    owner_name: str,
    owner_address: str,
    tenants: List[Dict[str, str]],
    witnesses: List[Dict[str, str]],
) -> str:
    table = "\n IN ACKNOWLEDGMENT OF THE TERMS AND CONDITIONS STATED HEREIN, BOTH OWNER AND THE TENANT(S) HAVE SET THEIR RESPECTIVE HANDS AND SIGNATURES ON THIS AGREEMENT ON THE DAY, MONTH, AND YEAR FIRST ABOVE WRITTEN.\n\n"
    table += "| Name & Address                                    | Photo           | Signature           |  \n"
    table += "|--------------------------------------------------|-----------------|---------------------|  \n"

    # Owner details
    table += (
        f"|**Owner:**<br/>**Name:** {owner_name}<br/>**Address:** {owner_address} "
        "| [OWNER PHOTO]   | [OWNER SIGNATURE]   |  \n"
    )

    # Tenant details
    for idx, tenant in enumerate(tenants, start=1):
        table += (
            f"|**Tenant {idx}:**<br/>**Name:**{tenant['name']}<br/>**Address:**{tenant['address']} "
            f"| [TENANT {idx} PHOTO] | [TENANT {idx} SIGNATURE] |  \n"
        )

    for idx, witness in enumerate(witnesses, start=1):
        table += (
            f"|**Witness {idx}:**<br/>**Name:**{witness['name']}<br/>**Address:**{witness['address']} "
            f"| [WITNESS {idx} PHOTO] | [WITNESS {idx} SIGNATURE] |  \n"
        )

    return table


def generate_furniture_table(furniture: List[Dict[str, str]]) -> str:
    if not furniture:
        return "\n THE OWNER HEREBY LETS OUT THE DEMISED PREMISES TO THE TENANT ON AN UNFURNISHED BASIS, WITH NO FURNITURE OR APPLIANCES PROVIDED AS PART OF THIS AGREEMENT."

    table = "\n THE OWNER HEREBY LETS OUT THE DEMISED PREMISES TO TENANT WITH FOLLOWING FURNITURE AND APPLIANCES, FORMING AN INTEGRAL PART OF THIS AGREEMENT: \n\n"
    table += "| Sr. No. | Name              | Units |\n"
    table += "|---------|-------------------|-------|\n"
    for item in furniture:
        table += (
            f"| {item['sr_no']}       | {item['name']}       | {item['units']}     |\n"
        )

    return table


def generate_agreement(state: State):
    """Generates the complete rental agreement by combining all sections."""
    agreement_id = state["agreement_id"]
    current_state = state_manager.get_agreement_state(agreement_id)
    if not current_state:
        raise ValueError("No active agreement state found")

    # Reset memory for fresh conversation
    memory.clear()
    if current_state.is_pdf_generated:
        return {"messages": current_state.agreement_text, "agreement_id": agreement_id}
    # Extract details from the current state
    owner = current_state.owner_name
    owner_address = current_state.owner_address
    tenant_details = current_state.tenant_details
    property_address = current_state.property_address
    city = current_state.city
    bhk_type = current_state.bhk_type
    area = current_state.area
    furnishing_type = current_state.furnishing_type
    rent_amount = current_state.rent_amount
    agreement_period = current_state.agreement_period
    security_deposit = current_state.security_deposit
    registration_date = current_state.registration_date
    amenities = current_state.amenities
    furniture_and_appliances = current_state.furniture_and_appliances
    witness_details = current_state.witness_details

    agreement_details = format_agreement_details(
        owner_name=owner,
        tenant_details=tenant_details,
        property_address=property_address,
        city=city,
        rent_amount=rent_amount,
        agreement_period=[date.isoformat() for date in agreement_period],
        owner_address=owner_address,
        furnishing_type=furnishing_type,
        security_deposit=security_deposit,
        bhk_type=bhk_type,
        area=area,
        registration_date=registration_date,
        amenities=amenities,
    )

    messages = [
        {"role": "system", "content": state["messages"][-1].content},
        {"role": "system", "content": AGREEMENT_SYSTEM_PROMPT},
        {"role": "user", "content": agreement_details},
    ]
    response = llm.invoke(messages)
    content_response = response.content

    # Combine all sections into the final agreement
    final_agreement = "\n\n".join(
        [
            content_response,
            generate_furniture_table(furniture_and_appliances),
            generate_table(owner, owner_address, tenant_details, witness_details),
        ]
    )

    current_state.agreement_text = final_agreement

    return {"messages": final_agreement, "agreement_id": agreement_id}


def resize_image(image_path, max_width, max_height):
    try:
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        with Image.open(image_path) as img:
            if image_path.lower().endswith(".jfif"):
                img = img.convert("RGB")

            img.thumbnail((max_width, max_height), Image.LANCZOS)

            original_format = "jpeg" if img.format == "JPEG" else "png"
            file_extension = ".jpg" if original_format == "jpeg" else ".png"

            temp_image = tempfile.NamedTemporaryFile(
                delete=False, suffix=file_extension
            )
            temp_image_path = temp_image.name
            img.save(temp_image_path, format=img.format)
            temp_image.close()

            return temp_image_path, original_format
    except Exception as e:
        print(f"Error resizing image: {e}")
        return None, None


def create_pdf(state: State):
    if isinstance(state, dict):
        content = state["messages"][-1].content
        agreement_id = state["agreement_id"]
        state = state_manager.get_agreement_state(agreement_id)
        state.agreement_text = content
    else:
        content = state.agreement_text

    if not state:
        raise ValueError("No active agreement state found")

    isDraft = True
    if state.is_fully_approved():
        # Replace owner signature with image
        if os.path.isfile(state.owner_signature):
            owner_signature_data, _ = resize_image(state.owner_signature, 60, 30)
            content = content.replace(
                "[OWNER SIGNATURE]", f" ![Owner Signature]({owner_signature_data})"
            )
        else:
            content = content.replace("[OWNER SIGNATURE]", state.owner_signature)

        # Replace owner photos with image
        if os.path.isfile(state.owner_photo):
            owner_photo_data, _ = resize_image(state.owner_photo, 60, 60)
            content = content.replace(
                "[OWNER PHOTO]", f" ![Owner PHOTO]({owner_photo_data})"
            )
        else:
            content = content.replace("[OWNER PHOTO]", state.owner_photo)

        # Replace tenant signatures with numbered placeholders and images
        for i, (tenant_id, signature) in enumerate(state.tenant_signatures.items(), 1):
            placeholder = f"[TENANT {i} SIGNATURE]"
            tenant_name = state.tenant_names.get(tenant_id, f"Tenant {i}")

            if os.path.isfile(signature):
                tenant_signature_data, _ = resize_image(signature, 60, 30)
                content = content.replace(
                    placeholder, f" ![Tenant {i} Signature]({tenant_signature_data})"
                )
            else:
                content = content.replace(placeholder, signature)

        # Replace tenant photos with numbered placeholders and images
        for i, (tenant_id, photo) in enumerate(state.tenant_photos.items(), 1):
            placeholder = f"[TENANT {i} PHOTO]"
            tenant_name = state.tenant_names.get(tenant_id, f"Tenant {i}")
            if os.path.isfile(photo):
                tenant_photos_data, _ = resize_image(photo, 60, 60)
                content = content.replace(
                    placeholder, f" ![Tenant PHOTO]({tenant_photos_data})"
                )
            else:
                content = content.replace(placeholder, photo)

        # Replace witness signatures and photos
        for i, (witness_id, signature) in enumerate(
            state.witness_signatures.items(), 1
        ):
            placeholder = f"[WITNESS {i} SIGNATURE]"
            if signature and os.path.isfile(signature):
                witness_signature_data, _ = resize_image(signature, 60, 30)
                content = content.replace(
                    placeholder, f" ![Witness {i} Signature]({witness_signature_data})"
                )
            else:
                content = content.replace(placeholder, "Signature not available")

        for i, (witness_id, photo) in enumerate(state.witness_photos.items(), 1):
            placeholder = f"[WITNESS {i} PHOTO]"
            if photo and os.path.isfile(photo):
                witness_photos_data, _ = resize_image(photo, 60, 60)
                content = content.replace(
                    placeholder, f" ![Witness PHOTO]({witness_photos_data})"
                )
            else:
                content = content.replace(placeholder, "Photo not available")
        isDraft = False

    # Ensure no Rupee symbols make it through to the PDF
    content = content.replace("₹", "Rs.")

    # Remove any potential Unicode characters that might cause LaTeX issues
    content = content.encode("ascii", "ignore").decode()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Create a temporary file
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir=base_dir)
    temp_pdf_path = temp_pdf.name

    create_pdf_file(content=content, output_pdf_path=temp_pdf_path, isDraft=isDraft)
    state.pdf_file_path = temp_pdf_path
    return {"messages": content}


# Build graph
graph_builder = StateGraph(State)
graph_builder.add_node("generate", generate_agreement)
graph_builder.add_node("create_pdf", create_pdf)
graph_builder.add_edge(START, "generate")
graph_builder.add_edge("generate", "create_pdf")
graph_builder.add_edge("create_pdf", END)
graph = graph_builder.compile()
