# AI Calling Agent — POC

A production-ready AI-powered voice calling agent using **Twilio** for telephony, **OpenAI** for conversational intelligence, and optional **ElevenLabs** for more natural text-to-speech. Handles both inbound and outbound calls with real-time conversation management over standard Twilio voice webhooks.

## Features

- 📞 **Inbound & Outbound Calls** via Twilio Voice API
- 🤖 **LLM-Powered Conversations** using OpenAI GPT-4
- 🗣️ **Natural Voice** using ElevenLabs TTS when configured
- 🔁 **Clean Fallback Voice Path** using Twilio `<Say>` / Polly voices when ElevenLabs is not configured
- 📝 **Call Transcription** with speech recognition via Twilio `<Gather>`
- 📊 **Call Logging & Analytics** — every call logged with transcript
- 🔄 **Configurable Workflows** — lead qualification, appointment booking, support
- 🎵 **Hosted MP3 Playback** — synthesized ElevenLabs responses are served back to Twilio via `<Play>`

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Twilio    │────▶│   FastAPI     │────▶│   OpenAI     │
│ (Telephony) │◀────│   Server      │◀────│   GPT-4      │
└─────────────┘     │              │     └─────────────┘
                    │              │     ┌─────────────┐
                    │              │────▶│ ElevenLabs  │
                    │              │◀────│   TTS API   │
                    └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  SQLite DB   │
                    │ (Call Logs)  │
                    └──────────────┘
```

### Voice Response Flow

1. Twilio sends inbound/outbound webhook requests to FastAPI
2. FastAPI gets the next assistant message from OpenAI
3. If `ELEVENLABS_API_KEY` is configured, the app generates MP3 audio with ElevenLabs and stores it temporarily
4. Twilio plays that audio back using `<Play>`
5. If ElevenLabs is not configured or synthesis fails, Twilio falls back to `<Say>` using Polly voices
6. Caller speech is captured with Twilio `<Gather>` and posted back to the app for the next turn

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Fill in your API keys
```

Required:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `OPENAI_API_KEY`

Optional for premium voice output:
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID` (defaults to `21m00Tcm4TlvDq8ikWAM`)

### 3. Run the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Expose with ngrok (for Twilio webhooks)

```bash
ngrok http 8000
```

Then set your Twilio phone number's voice webhook to `https://<ngrok-url>/voice/inbound`.

### 5. Make an Outbound Call

```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{"to": "+1234567890", "workflow": "lead_qualification"}'
```

## Call Workflows

### Lead Qualification
Qualifies leads by asking about their needs, budget, timeline, and decision-making process.

### Appointment Booking
Books appointments by collecting preferred date/time, contact details, and purpose.

### Customer Support
Handles common support queries, escalates complex issues to human agents.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/inbound` | Twilio webhook for inbound calls |
| POST | `/voice/respond` | Twilio speech result webhook for next-turn responses |
| POST | `/voice/outbound-connect` | Twilio webhook for outbound call connection |
| POST | `/voice/status` | Twilio status callback |
| POST | `/calls/outbound` | Initiate an outbound call |
| GET | `/calls` | List all calls with metadata |
| GET | `/calls/{call_id}` | Get call details + transcript |
| GET | `/audio/{call_sid}/{index}` | Serve generated ElevenLabs MP3 audio |
| GET | `/health` | Health check |

## Tech Stack

- **Python 3.11+** / FastAPI
- **Twilio** — Voice API, `<Gather>`, `<Play>`, `<Say>`
- **OpenAI** — GPT-4 for conversation
- **ElevenLabs** — Optional natural TTS via HTTP API
- **SQLite** — Call logging
- **Pydantic** — Data validation

## Notes

- This POC uses standard Twilio HTTP webhooks and TwiML responses.
- It does **not** use Twilio Media Streams or WebSocket audio streaming.
- If ElevenLabs is unavailable or not configured, the call flow still works via Twilio-native TTS.

## License

MIT
