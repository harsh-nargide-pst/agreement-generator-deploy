from fastapi import APIRouter, HTTPException, Request
import base64
import os
import random
from auth.clerk_auth import requires_auth
from helpers.state_manager import state_manager
from helpers.image_validation import are_faces_different, validate_uploaded_image

router = APIRouter()


@router.post("/validate-image")
@requires_auth
async def validate_image(request: Request):
    data = await request.json()
    image_url = data.get("image_url")
    agreement_id = int(data.get("agreement_id"))
    user_id = random.randint(1, 10000)
    if not image_url:
        raise HTTPException(status_code=400, detail="Missing image_url")

    if image_url.startswith("data:image/jpeg;base64,"):
        file_ext = "jpg"
        image_url = image_url.replace("data:image/jpeg;base64,", "")
    elif image_url.startswith("data:image/png;base64,"):
        file_ext = "png"
        image_url = image_url.replace("data:image/png;base64,", "")
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Only JPEG and PNG are supported.",
        )

    save_dir = "./utils"
    os.makedirs(save_dir, exist_ok=True)

    try:
        photo_bytes = base64.b64decode(image_url)
        photo_path = os.path.join(save_dir, f"{user_id}_photo.{file_ext}")

        with open(photo_path, "wb") as photo_file:
            photo_file.write(photo_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

    image_paths = []
    current_state = state_manager.get_agreement_state(agreement_id)
    if current_state.owner_photo:
        image_paths.append(current_state.owner_photo)
    if current_state.tenant_photos:
        image_paths.extend(
            photo for photo in current_state.tenant_photos.values() if photo
        )

    image_paths.append(photo_path)
    try:
        is_valid, message = are_faces_different(image_paths)
        if not is_valid:
            return {"message": {message}, "status": 400}

        is_valid, message = validate_uploaded_image(photo_path)
        if not is_valid:
            return {"message": {message}, "status": 400}

        return {"message": "Image successfully validated", "status": 200}

    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)
