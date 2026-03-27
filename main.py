import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Calling Agent")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are a helpful AI phone assistant. Keep responses concise and conversational, "
    "suitable for voice. Respond in 1-3 sentences maximum."
)


@app.post("/call/incoming", response_class=PlainTextResponse)
async def call_incoming(request: Request):
    """
    Twilio webhook for inbound calls.
    Greets the caller and uses <Gather> to collect speech input.
    """
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/call/respond",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(
        "Hello, you've reached the AI assistant. How can I help you today?",
        voice="Polly.Joanna",
    )
    response.append(gather)
    # Fallback if no input received
    response.say("I didn't catch that. Please call back and try again.")
    return str(response)


@app.post("/call/respond", response_class=PlainTextResponse)
async def call_respond(SpeechResult: str = Form(default=""), CallSid: str = Form(default="")):
    """
    Processes the transcribed speech via OpenAI GPT-4o and returns a TwiML voice response.
    Collects follow-up input to continue the conversation.
    """
    response = VoiceResponse()

    if not SpeechResult.strip():
        gather = Gather(
            input="speech",
            action="/call/respond",
            method="POST",
            speech_timeout="auto",
            language="en-US",
        )
        gather.say("I didn't catch that. Could you repeat yourself?", voice="Polly.Joanna")
        response.append(gather)
        return str(response)

    # Get GPT-4o response
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": SpeechResult},
        ],
        max_tokens=150,
        temperature=0.7,
    )
    ai_reply = completion.choices[0].message.content.strip()

    # Continue the conversation with another Gather
    gather = Gather(
        input="speech",
        action="/call/respond",
        method="POST",
        speech_timeout="auto",
        language="en-US",
    )
    gather.say(ai_reply, voice="Polly.Joanna")
    gather.say("Is there anything else I can help you with?", voice="Polly.Joanna")
    response.append(gather)

    # End call gracefully if caller goes silent
    response.say("Thank you for calling. Goodbye!", voice="Polly.Joanna")
    response.hangup()

    return str(response)


@app.get("/health")
async def health():
    return {"status": "ok"}
