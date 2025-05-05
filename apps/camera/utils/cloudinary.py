import os
import base64
import cloudinary
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "dzoy1bipn"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "511386762631941"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "evl1E4X-IAzRNmBV4bcX8FctD_M"),
    secure=True,
)


def upload_base64_image(base64_data, filename=None, folder="receipts"):
    """
    Upload a base64 image to Cloudinary and return the public URL

    Args:
        base64_data (str): Base64 encoded image data. Can include data URL prefix.
        filename (str, optional): Name to give the file on Cloudinary. If None, Cloudinary will auto-generate one.
        folder (str, optional): Folder in Cloudinary to store the image. Defaults to "receipts".

    Returns:
        dict: Dictionary containing:
            - 'url': The public URL of the uploaded image
            - 'public_id': The public ID of the image in Cloudinary
            - 'secure_url': HTTPS URL of the image
            - Additional metadata returned by Cloudinary

    Raises:
        Exception: If upload fails
    """
    try:
        logger.info(f"Uploading image to Cloudinary: {filename}")

        # Handle data URL format (data:image/jpeg;base64,...)
        if isinstance(base64_data, str) and base64_data.startswith("data:image"):
            base64_data = base64_data.split("base64,")[1]

        # Set upload parameters
        upload_params = {
            "folder": folder,
        }

        if filename:
            upload_params["public_id"] = filename

        # Upload to cloudinary
        result = cloudinary.uploader.upload(
            f"data:image/jpeg;base64,{base64_data}", **upload_params
        )

        logger.info(
            f"Successfully uploaded image to Cloudinary: {result.get('public_id')}"
        )

        return {
            "success": True,
            "url": result.get("url"),
            "secure_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "metadata": result,
        }

    except Exception as e:
        logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
        return {"success": False, "error": str(e)}
