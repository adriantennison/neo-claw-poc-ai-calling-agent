import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")
os.environ.setdefault("TWILIO_VOICE", "Polly.Joanna")
os.environ.setdefault("TWILIO_LANGUAGE", "en-US")

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_twilio_validation():
    """Bypass Twilio signature validation for all tests."""
    with patch("routes.calls.validate_twilio_request", return_value=None):
        yield


def test_empty_speech_fallback():
    """Empty SpeechResult must re-prompt via Gather, never hang up silently."""
    response = client.post(
        "/call/respond",
        data={"SpeechResult": "", "CallSid": "CA_TEST_EMPTY"},
    )
    assert response.status_code == 200
    assert "I didn't catch that" in response.text
    assert "<Gather" in response.text


def test_gpt4o_roundtrip_mocked():
    """Successful GPT-4o round-trip must include AI reply in TwiML <Say>."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "I can help you with that!"

    with patch("services.openai_service.client.chat.completions.create", return_value=mock_completion):
        response = client.post(
            "/call/respond",
            data={"SpeechResult": "What are your hours?", "CallSid": "CA_TEST_ROUNDTRIP"},
        )

    assert response.status_code == 200
    assert "I can help you with that!" in response.text
    assert "<Gather" in response.text


def test_openai_error_returns_graceful_twiml():
    """OpenAI failure must return a graceful <Say> + <Hangup>, not a 500."""
    with patch(
        "services.openai_service.client.chat.completions.create",
        side_effect=Exception("OpenAI unavailable"),
    ):
        response = client.post(
            "/call/respond",
            data={"SpeechResult": "Hello there", "CallSid": "CA_TEST_ERROR"},
        )

    assert response.status_code == 200
    assert "technical difficulties" in response.text
    assert "<Hangup" in response.text


def test_conversation_history_maintained():
    """Multiple turns on same CallSid should accumulate history."""
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Turn response"

    with patch("services.openai_service.client.chat.completions.create", return_value=mock_completion) as mock_create:
        client.post("/call/respond", data={"SpeechResult": "First message", "CallSid": "CA_HISTORY"})
        client.post("/call/respond", data={"SpeechResult": "Second message", "CallSid": "CA_HISTORY"})

        second_call_messages = mock_create.call_args_list[1][1]["messages"]
        user_messages = [m["content"] for m in second_call_messages if m["role"] == "user"]
        assert "First message" in user_messages
        assert "Second message" in user_messages
