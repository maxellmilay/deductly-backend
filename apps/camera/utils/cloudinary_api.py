import os
import cloudinary
import cloudinary.api
import logging

logger = logging.getLogger(__name__)

# Log the configuration being used
cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "dzoy1bipn")
api_key = os.getenv("CLOUDINARY_API_KEY", "511386762631941")
api_secret = os.getenv("CLOUDINARY_API_SECRET", "evl1E4X-IAzRNmBV4bcX8FctD_M")

logger.info(f"Initializing Cloudinary with cloud_name: {cloud_name}")

cloudinary.config(
    cloud_name=cloud_name,
    api_key=api_key,
    api_secret=api_secret,
    secure=True,
)


def fetch_cloudinary_images(user_id=None, folder="receipts", max_results=100):
    """
    Fetch images from Cloudinary folder

    Args:
        user_id (int, optional): The ID of the user to fetch images for. If None, fetches all images.
        folder (str): The base folder to fetch images from. Defaults to "receipts"
        max_results (int): Maximum number of results to return. Defaults to 100

    Returns:
        dict: Dictionary containing:
            - 'success': Boolean indicating if fetch was successful
            - 'resources': List of image resources with name, URL, date, and user_id
            - 'error': Error message if fetch failed
    """
    try:
        # Construct the folder path based on user_id
        folder_path = f"{folder}/{user_id}" if user_id else folder
        logger.info(f"Fetching images from Cloudinary folder: {folder_path}")

        # List all resources first to check if we can access Cloudinary
        try:
            all_resources = cloudinary.api.resources(type="upload", max_results=1)
            logger.info(
                f"Successfully connected to Cloudinary. Found {len(all_resources.get('resources', []))} total resources"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Cloudinary: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to connect to Cloudinary: {str(e)}",
            }

        # Fetch resources from Cloudinary
        result = cloudinary.api.resources(
            type="upload",
            prefix=folder_path,
            max_results=max_results,
            resource_type="image",
        )

        resources = result.get("resources", [])
        logger.info(f"Found {len(resources)} images in folder '{folder_path}'")

        # Transform the resources into a simplified format with name, URL, date, and user_id
        formatted_resources = []
        for resource in resources:
            # Extract user_id from the folder path
            resource_user_id = None
            if "/" in resource.get("folder", ""):
                resource_user_id = int(resource.get("folder").split("/")[-1])

            formatted_resource = {
                "name": resource.get("public_id"),
                "image": resource.get("secure_url"),
                "date": resource.get("created_at"),
                "user_id": resource_user_id,
            }
            formatted_resources.append(formatted_resource)
            logger.debug(f"Processed image: {formatted_resource['name']}")

        logger.info(
            f"Successfully fetched {len(formatted_resources)} images from Cloudinary"
        )

        return {"success": True, "resources": formatted_resources}

    except Exception as e:
        logger.error(f"Failed to fetch images from Cloudinary: {str(e)}")
        return {"success": False, "error": str(e)}
