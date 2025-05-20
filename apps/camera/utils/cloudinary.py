import os
import base64
import cloudinary
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_base64_image(base64_data, user_id, filename=None, folder="receipts"):
    """
    Upload a base64 image to Cloudinary and return the public URL

    Args:
        base64_data (str): Base64 encoded image data. Can include data URL prefix.
        user_id (int): The ID of the user uploading the image
        filename (str, optional): Name to give the file on Cloudinary. If None, Cloudinary will auto-generate one.
        folder (str, optional): Base folder in Cloudinary to store the image. Defaults to "receipts".

    Returns:
        dict: Dictionary containing:
            - 'success': Boolean indicating if upload was successful
            - 'public_url': The public HTTP URL of the uploaded image
            - 'secure_url': The secure HTTPS URL of the image
            - 'public_id': The public ID of the image in Cloudinary
            - 'user_id': The ID of the user who uploaded the image
            - 'metadata': Additional metadata returned by Cloudinary
            - 'error': Error message if upload failed

    Raises:
        Exception: If upload fails
    """
    try:
        logger.info(f"Uploading image to Cloudinary for user {user_id}: {filename}")

        # Handle data URL format (data:image/jpeg;base64,...)
        if isinstance(base64_data, str) and base64_data.startswith("data:image"):
            base64_data = base64_data.split("base64,")[1]

        # Set upload parameters with user-specific folder
        upload_params = {
            "folder": f"{folder}/{user_id}",
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
            "public_url": result.get("url"),  # HTTP URL
            "secure_url": result.get("secure_url"),  # HTTPS URL
            "public_id": result.get("public_id"),
            "user_id": user_id,
            "metadata": result,
        }

    except Exception as e:
        logger.error(f"Failed to upload image to Cloudinary: {str(e)}")
        return {"success": False, "error": str(e)}
