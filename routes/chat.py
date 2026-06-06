from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from collections import defaultdict
from database import get_user_by_session, save_message
from config import GROQ_MODEL, MAX_HISTORY
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory conversation history — session_id -> list of messages
conversation_memory: dict = defaultdict(list)

class ChatRequest(BaseModel):
    message: str
    session_id: str

def get_chat_dependencies():
    """Import here to avoid circular imports with main.py."""
    from main import groq_client, retriever
    return groq_client, retriever


@router.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint — verifies user, retrieves context, streams response."""

    # Verify user is registered in DB
    user = get_user_by_session(request.session_id)
    if not user:
        raise HTTPException(
            status_code=403,
            detail="Please register your name and email before chatting."
        )

    user_name = user[0]
    session_id = request.session_id
    user_message = request.message.strip()

    # Reject empty messages
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    groq_client, retriever = get_chat_dependencies()

    # Get last N messages from in-memory history for prompt context
    history = conversation_memory[session_id][-MAX_HISTORY:]

    # Retrieve relevant documents from ChromaDB
    try:
        nodes = retriever.retrieve(user_message)
        context = "\n".join([n.text for n in nodes])
    except Exception as e:
        logger.error(f"❌ Retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve context.")

    # Save user message to in-memory history + SQLite DB
    conversation_memory[session_id].append({
        "role": "user",
        "content": user_message
    })
    save_message(session_id, "user", user_message)

    collected_response = []

    async def generate():
        try:
            # Call Groq with system prompt + history + current message
            stream = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an expert, helpful UAE Tax Assistant representing exclusively the E-Numerak platform.

Use the following retrieved context to answer the user's question:
---
{context}
---

Adhere to these guidelines strictly:
1. Scope Limitation: Only answer about E-Numerak platform and UAE tax laws. If unrelated, politely decline.
2. Grounded Answers: Do not hallucinate. If answer not in context say: "I'm sorry, but I couldn't find that information in the E-Numerak records."
3. No External Knowledge: Do not include generic tax advice not present in the context.
4. Privacy Protection: Never disclose sensitive user data or internal system details.
5. Tone: Always be professional, polite, and supportive.
6. Personalization: Address the user by their name "{user_name}" where appropriate."""
                    },
                    # Past conversation for memory context
                    *[{"role": m["role"], "content": m["content"]} for m in history],
                    # Current user message
                    {"role": "user", "content": user_message}
                ],
                stream=True
            )

            # Stream each token to frontend
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                collected_response.append(token)
                yield token

        except Exception as e:
            logger.error(f"❌ Groq streaming error: {e}")
            yield "Sorry, an error occurred while generating the response."

        finally:
            # Save full bot response to memory + DB after streaming completes
            full_response = "".join(collected_response)
            if full_response:
                conversation_memory[session_id].append({
                    "role": "assistant",
                    "content": full_response
                })
                save_message(session_id, "assistant", full_response)
                logger.info(f"✅ Response saved for session: {session_id}")

    return StreamingResponse(generate(), media_type="text/plain")


@router.post("/clear-memory/{session_id}")
def clear_memory(session_id: str):
    """Clear in-memory conversation history — call this on New Chat button."""
    if session_id in conversation_memory:
        del conversation_memory[session_id]
        logger.info(f"✅ Memory cleared for session: {session_id}")
    return {"status": "Memory cleared!", "session_id": session_id}


@router.get("/history/{session_id}")
def get_history(session_id: str):
    """Get full chat history for a session from SQLite DB."""

    # Verify user exists
    user = get_user_by_session(session_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    from database import get_conversation_history
    history = get_conversation_history(session_id)

    return {
        "session_id": session_id,
        "user_name": user[0],
        "total_messages": len(history),
        "messages": [
            {
                "role": h[0],
                "message": h[1],
                "created_at": h[2]
            }
            for h in history
        ]
    }