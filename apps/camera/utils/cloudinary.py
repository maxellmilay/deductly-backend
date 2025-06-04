import os
import base64
import cloudinary
import cloudinary.uploader
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)


def upload_base64_image(image_data, filename=None, folder="receipts"):
    """Upload base64 image to Cloudinary."""
    try:
        logger.info(f"Uploading image to Cloudinary: {filename} in folder {folder}")

        # Validate input
        if not image_data:
            raise ValueError("No image data provided")

        # Handle data URL format (data:image/jpeg;base64,...)
        base64_data = image_data
        image_format = "jpeg"  # default format

        if isinstance(base64_data, str) and base64_data.startswith("data:image"):
            # Extract format from data URL
            format_part = base64_data.split(";")[0].split("/")[1]
            if format_part in ["jpeg", "jpg", "png", "webp", "gif"]:
                image_format = format_part
            base64_data = base64_data.split("base64,")[1]

        # Validate base64 data
        if not base64_data:
            raise ValueError("Invalid base64 data")

        # Set upload parameters
        upload_params = {
            "folder": folder,
            "resource_type": "image",
            "format": image_format,  # Let Cloudinary handle format conversion if needed
        }

        if filename:
            upload_params["public_id"] = filename

        # For profile pictures, add overwrite flag to replace existing image
        if folder.startswith("user-profiles"):
            upload_params["overwrite"] = True

        # Upload to cloudinary with detected format
        result = cloudinary.uploader.upload(
            f"data:image/{image_format};base64,{base64_data}", **upload_params
        )

        logger.info(f"Successfully uploaded image with format: {image_format}")

        return {
            "success": True,
            "public_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }
    except ValueError as e:
        logger.error(f"Validation error uploading image: {str(e)}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error uploading image to Cloudinary: {str(e)}")
        return {"success": False, "error": str(e)}


def upload_base64_pdf(pdf_data, vendor_name=None):
    """Upload base64 PDF to Cloudinary."""
    try:
        # Create filename if vendor name is provided
        public_id = None
        if vendor_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_vendor_name = "".join(
                c for c in vendor_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            public_id = f"{clean_vendor_name}_{timestamp}"

        # Upload to Cloudinary with proper PDF settings
        result = cloudinary.uploader.upload(
            f"data:application/pdf;base64,{pdf_data}",
            resource_type="raw",
            folder="documents",
            public_id=public_id,
        )
        return {
            "success": True,
            "public_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
        }
    except Exception as e:
        logger.error(f"Error uploading PDF to Cloudinary: {str(e)}")
        return {"success": False, "error": str(e)}
