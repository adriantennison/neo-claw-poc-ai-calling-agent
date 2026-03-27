import os
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator
from utils.logger import get_logger

logger = get_logger(__name__)


def validate_twilio_request(request: Request, form_data: dict) -> None:
    """Validate that the incoming request is genuinely from Twilio."""
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    validator = RequestValidator(auth_token)
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")
    if not validator.validate(url, form_data, signature):
        logger.warning(f"Invalid Twilio signature for URL={url}")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    logger.debug(f"Twilio signature valid for URL={url}")
