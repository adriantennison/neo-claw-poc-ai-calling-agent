# neo-claw-poc-ai-calling-agent

FastAPI backend handling inbound Twilio phone calls with GPT-4o conversational AI.

## Features

- Twilio request signature validation on every inbound POST
- Per-call conversation history (multi-turn, keyed by `CallSid`)
- GPT-4o with graceful error fallback (TwiML `<Say>` + `<Hangup>`)
- Configurable voice and language via env vars
- Structured logging throughout

## Structure

```
src/
├── main.py                      # FastAPI app entry point
├── routes/calls.py              # /call/incoming, /call/respond
├── services/openai_service.py   # GPT-4o multi-turn conversation
├── services/twilio_service.py   # Twilio signature validation
└── utils/logger.py              # Logging setup
tests/
└── test_calls.py
```

## Setup

```bash
cp .env.example .env
pip install -r requirements.txt
cd src && uvicorn main:app --reload
```

## Docker

```bash
docker build -t ai-calling-agent .
docker run -p 8000:8000 --env-file .env ai-calling-agent
```

## Tests

```bash
pytest tests/
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/call/incoming` | Twilio inbound call webhook |
| POST | `/call/respond` | Process speech, return GPT-4o TwiML |
| GET | `/health` | Health check |

## Environment Variables

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token (used for signature validation) |
| `TWILIO_PHONE_NUMBER` | Your Twilio phone number |
| `TWILIO_VOICE` | TTS voice (default: `Polly.Joanna`) |
| `TWILIO_LANGUAGE` | Speech recognition language (default: `en-US`) |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o |
