"""
API Gateway Lambda handler for user authentication, backed by Amazon Cognito.

Routes (dispatch via event["rawPath"] / event["path"]):
    POST /auth/signup   {"email", "password"}                -> Cognito SignUp
    POST /auth/confirm  {"email", "code"}                     -> Cognito ConfirmSignUp
    POST /auth/login    {"email", "password"}                 -> Cognito InitiateAuth (USER_PASSWORD_AUTH)

Cognito is used instead of a hand-rolled auth system so password storage,
MFA, and token issuance/rotation are handled by AWS rather than
application code.
"""
import json
import logging

import boto3
from botocore.exceptions import ClientError

from backend.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Content-Type": "application/json",
}

cognito_client = boto3.client("cognito-idp", region_name=config.AWS_REGION)


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": json.dumps(body)}


def _route(event) -> str:
    return (event.get("rawPath") or event.get("path") or "").rstrip("/").split("/")[-1]


def _signup(payload: dict) -> dict:
    email, password = payload.get("email"), payload.get("password")
    if not email or not password:
        return _response(400, {"error": "email and password are required"})

    try:
        cognito_client.sign_up(
            ClientId=config.COGNITO_APP_CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        return _response(201, {"message": "Signup successful. Check your email for a confirmation code."})
    except ClientError as exc:
        logger.warning("Signup failed for %s: %s", email, exc)
        return _response(400, {"error": exc.response["Error"]["Message"]})


def _confirm(payload: dict) -> dict:
    email, code = payload.get("email"), payload.get("code")
    if not email or not code:
        return _response(400, {"error": "email and code are required"})

    try:
        cognito_client.confirm_sign_up(
            ClientId=config.COGNITO_APP_CLIENT_ID,
            Username=email,
            ConfirmationCode=code,
        )
        return _response(200, {"message": "Account confirmed. You can now log in."})
    except ClientError as exc:
        logger.warning("Confirmation failed for %s: %s", email, exc)
        return _response(400, {"error": exc.response["Error"]["Message"]})


def _login(payload: dict) -> dict:
    email, password = payload.get("email"), payload.get("password")
    if not email or not password:
        return _response(400, {"error": "email and password are required"})

    try:
        auth_result = cognito_client.initiate_auth(
            ClientId=config.COGNITO_APP_CLIENT_ID,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )["AuthenticationResult"]
        return _response(
            200,
            {
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "refresh_token": auth_result["RefreshToken"],
                "expires_in": auth_result["ExpiresIn"],
            },
        )
    except ClientError as exc:
        logger.warning("Login failed for %s: %s", email, exc)
        return _response(401, {"error": exc.response["Error"]["Message"]})


ROUTES = {"signup": _signup, "confirm": _confirm, "login": _login}


def handler(event, context):
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _response(200, {})

    route = _route(event)
    handler_fn = ROUTES.get(route)
    if handler_fn is None:
        return _response(404, {"error": f"Unknown auth route '{route}'"})

    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON."})

    return handler_fn(payload)
