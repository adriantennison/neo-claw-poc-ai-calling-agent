# AI Calling Agent

A FastAPI backend that handles inbound Twilio phone calls and uses OpenAI GPT-4o to generate real-time conversational responses delivered via text-to-speech.

## What This Does

1. **Receives an inbound call** via Twilio at `POST /call/incoming`
   - Returns a TwiML `<Gather>` response that prompts the caller and listens for speech input
   - Uses Amazon Polly (Twilio's Polly.Joanna voice) for natural-sounding TTS

2. **Processes speech** at `POST /call/respond`
   - Receives the transcribed speech (`SpeechResult`) from Twilio
   - Sends it to OpenAI GPT-4o (`gpt-4o`) as a chat completion request
   - Returns the AI-generated reply as a TwiML voice response
   - Continues the conversation loop with another `<Gather>`

## Setup

```bash
cp .env.example .env
# Fill in your credentials in .env
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Configure your Twilio phone number's inbound webhook to:
- **Voice URL:** `https://your-domain.com/call/incoming` (HTTP POST)

## Environment Variables

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o access |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/call/incoming` | Twilio webhook — greets caller, collects speech |
| `POST` | `/call/respond` | Processes transcription, returns GPT-4o reply as TwiML |
| `GET` | `/health` | Health check |

## Tech Stack

- **FastAPI** — HTTP server and routing
- **Twilio** — inbound call handling and TwiML generation
- **OpenAI GPT-4o** — conversation logic and response generation
- **Uvicorn** — ASGI server
