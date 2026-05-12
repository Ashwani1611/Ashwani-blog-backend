from fastapi import APIRouter, Depends, UploadFile, File
from app.core.uploads import save_image
from app.core.security import get_current_admin

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    _=Depends(get_current_admin),
):
    """
    Upload an image to Cloudinary.
    Returns the image URL — use it as cover_image when creating a post.
    Only admin can upload.
    """
    url = await save_image(file)
    return {
        "url": url,
        "message": "Image uploaded successfully"
    }