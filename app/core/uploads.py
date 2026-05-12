import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import get_settings

settings = get_settings()

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)

# Allowed image types
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Max file size — 5MB
MAX_SIZE = 5 * 1024 * 1024


async def save_image(file: UploadFile, folder: str = "blog") -> str:
    """
    Validates and uploads image to Cloudinary.
    Returns the secure URL of the uploaded image.
    """
    # Check file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WEBP, GIF"
        )

    # Read file
    contents = await file.read()

    # Check file size
    if len(contents) > MAX_SIZE:
        raise HTTPException(400, "File too large. Maximum size is 5MB")

    # Upload to Cloudinary
    try:
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type="image",
            transformation=[
                {"width": 1200, "crop": "limit"},  # max width 1200px
                {"quality": "auto"},                # auto optimize quality
                {"fetch_format": "auto"},           # auto best format (webp etc)
            ]
        )
        return result["secure_url"]
    except Exception as e:
        raise HTTPException(500, f"Image upload failed: {str(e)}")


async def delete_image(public_id: str):
    """Delete image from Cloudinary by public_id."""
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception:
        pass  # Don't break the app if delete fails