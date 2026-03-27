import os
from openai import OpenAI
from utils.logger import get_logger

logger = get_logger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are a helpful AI phone assistant. Keep responses concise and conversational, "
    "suitable for voice. Respond in 1-3 sentences maximum."
)

# Per-call conversation history keyed by CallSid
conversation_histories: dict[str, list[dict]] = {}


def get_ai_response(call_sid: str, user_message: str) -> str:
    """Get GPT-4o response maintaining full conversation history per CallSid."""
    if call_sid not in conversation_histories:
        conversation_histories[call_sid] = []

    conversation_histories[call_sid].append({"role": "user", "content": user_message})
    turn = len(conversation_histories[call_sid])
    logger.info(f"GPT-4o called: CallSid={call_sid}, turn={turn}")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_histories[call_sid]

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=150,
        temperature=0.7,
    )
    reply = completion.choices[0].message.content.strip()
    conversation_histories[call_sid].append({"role": "assistant", "content": reply})
    logger.info(f"GPT-4o response: CallSid={call_sid}: {reply[:80]}")
    return reply


def clear_conversation(call_sid: str) -> None:
    """Remove conversation history for a completed or errored call."""
    conversation_histories.pop(call_sid, None)
    logger.debug(f"Conversation cleared: CallSid={call_sid}")
