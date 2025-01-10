from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from dotenv import load_dotenv
import os
import datetime


def sign_as_jwt(payload, algorithm="HS256"):
    load_dotenv()

    jwt_secret_key = os.getenv("JWT_SECRET_KEY")
    token = encode(payload, jwt_secret_key, algorithm)

    return token


def verify_jwt_token(token: str, email: str, algorithm="HS256"):
    load_dotenv()

    jwt_secret_key = os.getenv("JWT_SECRET_KEY")

    payload = decode(token, jwt_secret_key, algorithms=[algorithm])

    if email != payload.get("email"):
        raise InvalidTokenError

    if "exp" in payload:
        exp_timestamp = payload["exp"]
        if datetime.datetime.now(datetime.timezone.utc).timestamp() > exp_timestamp:
            raise ExpiredSignatureError

    return payload
