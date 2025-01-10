from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
import os


def verify_google_id_token(google_id_token: str):
    load_dotenv()

    try:
        request = requests.Request()
        payload = id_token.verify_oauth2_token(
            google_id_token, request, os.getenv("OAUTH_IOS_CLIENT_ID")
        )
        return payload
    except ValueError as e:
        print("Invalid ID Token: ", e)
        return None
