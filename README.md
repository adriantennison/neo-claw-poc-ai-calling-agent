# AI Calling Agent — POC

An AI-powered voice calling agent using **Twilio** for telephony, **OpenAI GPT-4o** for conversational intelligence, and **SQLite** for call logging. Handles both inbound and outbound calls via Twilio webhooks with per-call conversation state.

## Features

- Inbound and outbound calls via Twilio Voice API
- LLM-powered conversations using OpenAI GPT-4o
- Natural voice synthesis via Twilio's Amazon Polly integration (Polly.Joanna)
- Speech-to-text via Twilio Gather
- Call logging and full transcript storage in SQLite
- Configurable workflows: lead qualification, appointment booking, customer support

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Twilio     │────▶│  FastAPI      │────▶│  OpenAI     │
│  (Telephony) │◀────│  Server       │◀────│  GPT-4o     │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  SQLite DB   │
                    │ (Call Logs)  │
                    └──────────────┘
```

Twilio sends webhook POST requests to FastAPI on each call event. FastAPI maintains in-memory conversation state keyed by Twilio `CallSid`, queries OpenAI for responses, and returns TwiML using `<Say>` (Polly voice) and `<Gather>` for speech input. All call metadata and transcripts are persisted to SQLite.

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

### 3. Run the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Expose with ngrok (for Twilio webhooks)

```bash
ngrok http 8000
```

Set `BASE_URL` in your `.env` to the ngrok HTTPS URL, then configure your Twilio phone number's voice webhook to:

```
POST https://<ngrok-url>/voice/inbound
```

### 5. Make an Outbound Call

```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{"to": "+1234567890", "workflow": "lead_qualification"}'
```

## Call Workflows

### lead_qualification
Qualifies leads by asking about their needs, budget, timeline, and decision-making process.

### appointment_booking
Books appointments by collecting preferred date/time, contact details, and purpose.

### customer_support
Handles common support queries and escalates complex issues to human agents.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/voice/inbound` | Twilio webhook — handles incoming calls, returns TwiML greeting |
| POST | `/voice/respond` | Twilio webhook — processes speech input, returns AI response as TwiML |
| POST | `/voice/status` | Twilio status callback — updates call log on status changes |
| POST | `/voice/outbound-connect` | Twilio webhook — connects outbound call and starts conversation |
| POST | `/calls/outbound` | Initiate an outbound call with a specified workflow |
| GET | `/calls` | List all calls with metadata (supports `limit` and `offset`) |
| GET | `/calls/{call_sid}` | Get call details and full transcript |
| GET | `/health` | Health check |

## Tech Stack

- **Python 3.11+** / FastAPI
- **Twilio** — Voice API, Gather (speech-to-text), Say with Amazon Polly voices
- **OpenAI** — GPT-4o for conversation
- **SQLite** / SQLAlchemy — Call logging and transcript storage
- **Pydantic** — Request validation
- **python-dotenv** — Environment config

## License

MIT
