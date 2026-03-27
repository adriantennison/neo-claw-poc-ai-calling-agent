import os
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from services.openai_service import get_ai_response, clear_conversation
from services.twilio_service import validate_twilio_request
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

VOICE = os.getenv("TWILIO_VOICE", "Polly.Joanna")
LANGUAGE = os.getenv("TWILIO_LANGUAGE", "en-US")


@router.post("/call/incoming", response_class=PlainTextResponse)
async def call_incoming(request: Request):
    """Twilio webhook for inbound calls. Greets caller and starts speech collection."""
    form_data = dict(await request.form())
    validate_twilio_request(request, form_data)

    call_sid = form_data.get("CallSid", "unknown")
    logger.info(f"Call received: CallSid={call_sid}")

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/call/respond",
        method="POST",
        speech_timeout="auto",
        language=LANGUAGE,
    )
    gather.say("Hello, you've reached the AI assistant. How can I help you today?", voice=VOICE)
    response.append(gather)
    response.say("I didn't catch that. Please call back and try again.", voice=VOICE)
    return str(response)


@router.post("/call/respond", response_class=PlainTextResponse)
async def call_respond(request: Request):
    """Process transcribed speech via GPT-4o and return TwiML voice response."""
    form_data = dict(await request.form())
    validate_twilio_request(request, form_data)

    speech_result = form_data.get("SpeechResult", "")
    call_sid = form_data.get("CallSid", "unknown")
    logger.info(f"Speech transcribed: CallSid={call_sid}, text='{speech_result[:80]}'")

    response = VoiceResponse()

    if not speech_result.strip():
        logger.info(f"Empty speech: CallSid={call_sid}, prompting again")
        gather = Gather(
            input="speech",
            action="/call/respond",
            method="POST",
            speech_timeout="auto",
            language=LANGUAGE,
        )
        gather.say("I didn't catch that. Could you repeat yourself?", voice=VOICE)
        response.append(gather)
        response.say("I'm unable to hear you. Goodbye!", voice=VOICE)
        response.hangup()
        return str(response)

    try:
        ai_reply = get_ai_response(call_sid, speech_result)
        logger.info(f"Response sent: CallSid={call_sid}")
    except Exception as e:
        logger.error(f"OpenAI error: CallSid={call_sid}: {e}")
        clear_conversation(call_sid)
        response.say(
            "I'm sorry, I'm experiencing technical difficulties. Please call back shortly.",
            voice=VOICE,
        )
        response.hangup()
        return str(response)

    gather = Gather(
        input="speech",
        action="/call/respond",
        method="POST",
        speech_timeout="auto",
        language=LANGUAGE,
    )
    gather.say(ai_reply, voice=VOICE)
    gather.say("Is there anything else I can help you with?", voice=VOICE)
    response.append(gather)
    response.say("Thank you for calling. Goodbye!", voice=VOICE)
    response.hangup()
    return str(response)
