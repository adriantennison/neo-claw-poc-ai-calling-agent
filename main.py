"""
AI Calling Agent — FastAPI server for AI-powered voice calls.
Uses Twilio for telephony, OpenAI for conversation, ElevenLabs for TTS.
"""

import os
import time
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai

from database import init_db, SessionLocal, CallLog, CallTranscript
from workflows import WORKFLOWS, get_system_prompt

load_dotenv()

# --- Configuration ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Init ---
app = FastAPI(title="AI Calling Agent", version="1.0.0")
twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# In-memory conversation state (keyed by Twilio CallSid)
conversations: dict[str, list[dict]] = {}


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("AI Calling Agent started")


# --- Models ---
class OutboundCallRequest(BaseModel):
    to: str
    workflow: str = "lead_qualification"
    context: Optional[dict] = None


class CallResponse(BaseModel):
    call_id: str
    status: str
    workflow: str
    duration: Optional[int] = None
    transcript: Optional[list] = None


# --- Inbound Call Handler ---
@app.post("/voice/inbound")
async def handle_inbound(request: Request):
    """Handle incoming Twilio voice webhook — greet and start conversation."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    from_number = form.get("From", "unknown")
    
    logger.info(f"Inbound call from {from_number} (CallSid: {call_sid})")
    
    # Initialize conversation with default workflow
    workflow = "customer_support"
    system_prompt = get_system_prompt(workflow)
    conversations[call_sid] = [{"role": "system", "content": system_prompt}]
    
    # Log the call
    db = SessionLocal()
    try:
        call_log = CallLog(
            call_sid=call_sid,
            direction="inbound",
            from_number=from_number,
            to_number=TWILIO_PHONE_NUMBER,
            workflow=workflow,
            status="in-progress",
            started_at=datetime.utcnow(),
        )
        db.add(call_log)
        db.commit()
    finally:
        db.close()
    
    # Generate greeting
    greeting = _get_ai_response(call_sid, None, is_greeting=True)
    
    # Build TwiML response with Gather for speech input
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"{BASE_URL}/voice/respond",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(greeting, voice="Polly.Joanna")
    response.append(gather)
    response.say("I didn't catch that. Goodbye!", voice="Polly.Joanna")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/voice/respond")
async def handle_response(request: Request):
    """Process speech input and generate AI response."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    speech_result = form.get("SpeechResult", "")
    confidence = form.get("Confidence", "0")
    
    logger.info(f"Speech from {call_sid}: '{speech_result}' (confidence: {confidence})")
    
    if not speech_result:
        response = VoiceResponse()
        gather = Gather(
            input="speech",
            action=f"{BASE_URL}/voice/respond",
            method="POST",
            speech_timeout="auto",
            language="en-US",
        )
        gather.say("I'm sorry, I didn't catch that. Could you repeat?", voice="Polly.Joanna")
        response.append(gather)
        return Response(content=str(response), media_type="application/xml")
    
    # Log transcript
    _log_transcript(call_sid, "user", speech_result)
    
    # Get AI response
    ai_response = _get_ai_response(call_sid, speech_result)
    
    # Log AI response
    _log_transcript(call_sid, "assistant", ai_response)
    
    # Check if conversation should end
    should_end = _should_end_call(ai_response)
    
    response = VoiceResponse()
    if should_end:
        response.say(ai_response, voice="Polly.Joanna")
        response.hangup()
    else:
        gather = Gather(
            input="speech",
            action=f"{BASE_URL}/voice/respond",
            method="POST",
            speech_timeout="auto",
            language="en-US",
        )
        gather.say(ai_response, voice="Polly.Joanna")
        response.append(gather)
        response.say("Are you still there?", voice="Polly.Joanna")
        gather2 = Gather(
            input="speech",
            action=f"{BASE_URL}/voice/respond",
            method="POST",
            speech_timeout="auto",
        )
        response.append(gather2)
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/voice/status")
async def handle_status(request: Request):
    """Handle Twilio call status callbacks."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    call_status = form.get("CallStatus", "unknown")
    duration = form.get("CallDuration", "0")
    
    logger.info(f"Call {call_sid} status: {call_status} (duration: {duration}s)")
    
    # Update call log
    db = SessionLocal()
    try:
        call_log = db.query(CallLog).filter(CallLog.call_sid == call_sid).first()
        if call_log:
            call_log.status = call_status
            call_log.duration = int(duration) if duration else 0
            call_log.ended_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
    
    # Clean up conversation state
    conversations.pop(call_sid, None)
    
    return {"status": "ok"}


# --- Outbound Calls ---
@app.post("/calls/outbound")
async def make_outbound_call(req: OutboundCallRequest):
    """Initiate an outbound AI-powered call."""
    if req.workflow not in WORKFLOWS:
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {req.workflow}. Available: {list(WORKFLOWS.keys())}")
    
    try:
        call = twilio_client.calls.create(
            to=req.to,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{BASE_URL}/voice/outbound-connect?workflow={req.workflow}",
            status_callback=f"{BASE_URL}/voice/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )
        
        # Log the call
        db = SessionLocal()
        try:
            call_log = CallLog(
                call_sid=call.sid,
                direction="outbound",
                from_number=TWILIO_PHONE_NUMBER,
                to_number=req.to,
                workflow=req.workflow,
                status="initiated",
                started_at=datetime.utcnow(),
                context=json.dumps(req.context) if req.context else None,
            )
            db.add(call_log)
            db.commit()
        finally:
            db.close()
        
        logger.info(f"Outbound call initiated: {call.sid} to {req.to}")
        return {"call_sid": call.sid, "status": "initiated", "workflow": req.workflow}
    
    except Exception as e:
        logger.error(f"Failed to initiate outbound call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/outbound-connect")
async def handle_outbound_connect(request: Request, workflow: str = "lead_qualification"):
    """Handle outbound call connection — start the AI conversation."""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    
    # Initialize conversation
    system_prompt = get_system_prompt(workflow)
    conversations[call_sid] = [{"role": "system", "content": system_prompt}]
    
    # Generate opening
    greeting = _get_ai_response(call_sid, None, is_greeting=True)
    _log_transcript(call_sid, "assistant", greeting)
    
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"{BASE_URL}/voice/respond",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(greeting, voice="Polly.Joanna")
    response.append(gather)
    
    return Response(content=str(response), media_type="application/xml")


# --- Call History ---
@app.get("/calls")
async def list_calls(limit: int = 20, offset: int = 0):
    """List all calls with metadata."""
    db = SessionLocal()
    try:
        calls = db.query(CallLog).order_by(CallLog.started_at.desc()).offset(offset).limit(limit).all()
        return [
            {
                "call_sid": c.call_sid,
                "direction": c.direction,
                "from": c.from_number,
                "to": c.to_number,
                "workflow": c.workflow,
                "status": c.status,
                "duration": c.duration,
                "started_at": c.started_at.isoformat() if c.started_at else None,
            }
            for c in calls
        ]
    finally:
        db.close()


@app.get("/calls/{call_sid}")
async def get_call(call_sid: str):
    """Get call details including full transcript."""
    db = SessionLocal()
    try:
        call = db.query(CallLog).filter(CallLog.call_sid == call_sid).first()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        transcripts = (
            db.query(CallTranscript)
            .filter(CallTranscript.call_sid == call_sid)
            .order_by(CallTranscript.timestamp.asc())
            .all()
        )
        
        return {
            "call_sid": call.call_sid,
            "direction": call.direction,
            "from": call.from_number,
            "to": call.to_number,
            "workflow": call.workflow,
            "status": call.status,
            "duration": call.duration,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            "transcript": [
                {"role": t.role, "content": t.content, "timestamp": t.timestamp.isoformat()}
                for t in transcripts
            ],
        }
    finally:
        db.close()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat()}


# --- Internal Helpers ---
def _get_ai_response(call_sid: str, user_input: Optional[str], is_greeting: bool = False) -> str:
    """Generate AI response using OpenAI."""
    if call_sid not in conversations:
        conversations[call_sid] = [
            {"role": "system", "content": get_system_prompt("customer_support")}
        ]
    
    messages = conversations[call_sid]
    
    if user_input:
        messages.append({"role": "user", "content": user_input})
    elif is_greeting:
        messages.append({"role": "user", "content": "[Call connected. Deliver your opening greeting.]"})
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=200,
            temperature=0.7,
        )
        
        ai_text = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": ai_text})
        
        return ai_text
    
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "I apologize, I'm having a technical issue. Let me connect you with a human agent."


def _should_end_call(response: str) -> bool:
    """Check if the AI response indicates the call should end."""
    end_markers = ["goodbye", "have a great day", "thank you for calling", "ending the call", "[END_CALL]"]
    return any(marker.lower() in response.lower() for marker in end_markers)


def _log_transcript(call_sid: str, role: str, content: str):
    """Log a transcript entry to the database."""
    db = SessionLocal()
    try:
        entry = CallTranscript(
            call_sid=call_sid,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log transcript: {e}")
    finally:
        db.close()
