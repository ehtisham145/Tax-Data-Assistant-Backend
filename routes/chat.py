import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from collections import defaultdict
from starlette.concurrency import run_in_threadpool
from database.conversations import save_message, get_conversation_history
from database.users import get_user_by_email, get_user_by_session
from utils.config import GROQ_MODEL, MAX_HISTORY
from utils.helpers import get_groq_client, get_retriever
from schemas.chat_schema import ChatRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store — session_id -> list of messages
conversation_memory: dict = defaultdict(list)


# ─── Memory Helpers ───────────────────────────────────────────────────────────

def get_history_from_redis(session_id: str) -> list:
    return list(conversation_memory[session_id])

def save_history_to_redis(session_id: str, history: list):
    conversation_memory[session_id] = history[-MAX_HISTORY:]

def clear_history_from_redis(session_id: str):
    if session_id in conversation_memory:
        del conversation_memory[session_id]

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(
    body: ChatRequest,
    groq_client=Depends(get_groq_client),
    retriever=Depends(get_retriever),
):
    # 1. Auth + RAG parallel — dono ek saath chalao
    try:
        user_result, nodes = await asyncio.gather(
            run_in_threadpool(get_user_by_email, body.email),
            run_in_threadpool(retriever.retrieve, body.message),
        )
    except Exception as e:
        logger.error(f"❌ Auth/Retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request.")

    # Auth check
    if not user_result:
        raise HTTPException(
            status_code=403,
            detail="Please register your name and email before chatting."
        )

    user_name = user_result[0]
    session_id = body.session_id
    context = "\n".join([n.text for n in nodes]) if nodes else "No relevant context found."

    # 2. History Redis se lo
    history = get_history_from_redis(session_id)

    # 3. User message save karo (parallel — await nahi karo abhi)
    history.append({"role": "user", "content": body.message})
    save_history_to_redis(session_id, history)

    # DB save background mein — response block nahi karega
    asyncio.create_task(
        run_in_threadpool(save_message, session_id, "user", body.message)
    )

    # 4. System prompt
    system_prompt = (
        f"You are an expert, helpful UAE Tax Assistant representing exclusively the E-Numerak platform.\n\n"
        f"Use the following retrieved context to answer the user's question:\n---\n{context}\n---\n\n"
        f"Guidelines:\n"
        f"1. Only answer about E-Numerak platform and UAE tax laws. If unrelated, politely decline.\n"
        f"2. Do not hallucinate. If answer not in context say: \"I'm sorry, but I couldn't find that information in the E-Numerak records.\"\n"
        f"3. Do not include generic tax advice not present in the context.\n"
        f"4. Never disclose sensitive user data or internal system details.\n"
        f"5. Always be professional, polite, and supportive.\n"
        f"6. Bold important words and use bullet points where appropriate.\n"
        f"7. Address the user by their name \"{user_name}\" where appropriate.\n"
        f"8. Respond as quickly and concisely as possible."
    )

    # 5. Stream response
    collected_response: list[str] = []

    async def generate():
        try:
            # Sync Groq stream ko thread mein run karo
            stream = await run_in_threadpool(
                lambda: groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",  # fastest Groq model
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *[{"role": m["role"], "content": m["content"]} for m in history[:-1]],
                        {"role": "user", "content": body.message},
                    ],
                    stream=True,
                )
            )

            # Async iteration via threadpool
            def get_next_chunk(iterator):
                try:
                    return next(iterator)
                except StopIteration:
                    return None

            while True:
                chunk = await run_in_threadpool(get_next_chunk, iter(stream))
                if chunk is None:
                    break
                token = chunk.choices[0].delta.content or ""
                if token:
                    collected_response.append(token)
                    yield token

        except Exception as e:
            logger.error(f"❌ Groq streaming error: {e}")
            yield "Sorry, an error occurred while generating the response."

        finally:
            full_response = "".join(collected_response)
            if full_response:
                history.append({"role": "assistant", "content": full_response})
                save_history_to_redis(session_id, history)
                # DB save background mein
                asyncio.create_task(
                    run_in_threadpool(save_message, session_id, "assistant", full_response)
                )
                logger.info(f"✅ Response saved for session: {session_id}")

    return StreamingResponse(generate(), media_type="text/plain")


# ─── Clear Memory ─────────────────────────────────────────────────────────────

@router.post("/clear-memory/{session_id}")
async def clear_memory(session_id: str):
    """Clear in-memory conversation history — call on New Chat."""
    try:
        await run_in_threadpool(clear_history_from_redis, session_id)
        logger.info(f"✅ Memory cleared for session: {session_id}")
        return {"status": "Memory cleared!", "session_id": session_id}
    except Exception as e:
        logger.error(f"❌ Failed to clear memory for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not clear memory.")


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get full chat history for a session from SQLite DB."""
    user = await run_in_threadpool(get_user_by_session, session_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    history = await run_in_threadpool(get_conversation_history, session_id)

    return {
        "session_id": session_id,
        "user_name": user[0],
        "total_messages": len(history),
        "messages": [
            {"role": h[0], "message": h[1], "created_at": h[2]}
            for h in history
        ],
    }