import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from collections import defaultdict
from starlette.concurrency import run_in_threadpool
from database.conversations import save_message, get_conversation_history
from database.users import get_user_by_email, get_user_by_session
from utils.config import OPENAI_MODEL, MAX_HISTORY
from utils.helpers import get_openai_client, get_retriever
from schemas.chat_schema import ChatRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store — session_id -> list of messages
conversation_memory: dict = defaultdict(list)


# ─── Memory Helpers ───────────────────────────────────────────────────────────

def get_history_from_memory(session_id: str) -> list:
    return list(conversation_memory[session_id])

def save_history_to_memory(session_id: str, history: list):
    conversation_memory[session_id] = history[-MAX_HISTORY:]

def clear_history_from_memory(session_id: str):
    if session_id in conversation_memory:
        del conversation_memory[session_id]


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    openai_client=Depends(get_openai_client),
    retriever=Depends(get_retriever),
):
    # 1. Auth + RAG parallel
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

    # 2. History memory se lo
    history = get_history_from_memory(session_id)

    # 3. User message memory mein save karo
    history.append({"role": "user", "content": body.message})
    save_history_to_memory(session_id, history)

    # DB save background mein — response block nahi karega
    asyncio.create_task(
        run_in_threadpool(save_message, session_id, "user", body.message)
    )

    # 4. System prompt
    system_prompt = (
    f"You are an expert UAE Tax Assistant representing the E-Numerak platform.\n"
    f"Your primary task is to answer the user's question using ONLY the provided context.\n\n"
    f"--- CONTEXT ---\n{context}\n---------------\n\n"
    f"CRITICAL GUIDELINES:\n"
    f"1. LANGUAGE MATCHING: Detect the language of the user's message. You MUST respond in that exact same language.\n"
    f"2. BREVITY & SCALING: Keep answers brief, direct, and limited strictly to the question asked. Do not give extensive historical details or unrequested deep dives unless the user explicitly asks for \"detailed information\" or \"in-depth analysis\".\n"
    f"3. STRICT CONTEXT: Do not hallucinate or give external tax advice. If a factual question cannot be answered using only the context, state exactly: \"I'm sorry, but I couldn't find that information in the E-Numerak records.\", then append the Support Block below.\n"
    f"4. HUMAN CONTACT EXCEPTION: If the user explicitly asks to talk to support, contact the team, or connect with a human, BYPASS the \"I'm sorry\" fallback text in Guideline 3. Instead, reply warmly: \"I would be happy to connect you with our team! Here is how you can reach us directly:\", then append the Support Block.\n"
    f"5. SCOPE LIMIT: Only discuss the E-Numerak platform and UAE tax laws. Politely decline any unrelated topics.\n"
    f"6. DATA SECURITY: Never disclose internal system details or sensitive customer data.\n"
    f"7. PERSONALIZATION: Address the user by their name \"{user_name}\" naturally where appropriate.\n"
    f"8. STYLE: Be highly concise, professional, and supportive. Bold important words and use clean bullet points for readability.\n"
    f"9. PLATFORM DESCRIPTION OVERRIDE: If the user asks general questions like \"What is E-Numerak?\" or \"Tell me about E-Numerak in detail\" and the retrieved context is empty, bypass Guideline 3 and explain: \"**E-Numerak** is an advanced, automated e-invoicing and compliance platform designed for businesses in the UAE. We streamline the creation, management, and compliance tracking of tax invoices in alignment with UAE corporate tax laws and UAE PINT standards.\"\n\n"
    f"SUPPORT BLOCK:\n"
    f"For further assistance, please contact our team directly:\n"
    f"📧 info@e-numerak.com\n"
    f"📞 +971 50 635 8421\n"
    f"🕐 Mon–Fri, 9AM–6PM GST"
)
    

    # 5. Stream response
    collected_response: list[str] = []

    async def generate():
        try:
            # OpenAI async streaming — no run_in_threadpool needed
            stream = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *[{"role": m["role"], "content": m["content"]} for m in history[:-1]],
                    {"role": "user", "content": body.message},
                ],
                stream=True,
            )

            # AsyncOpenAI supports async iteration natively
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    collected_response.append(token)
                    yield token

        except Exception as e:
            logger.error(f"❌ OpenAI streaming error: {e}")
            yield "Sorry, an error occurred while generating the response."

        finally:
            full_response = "".join(collected_response)
            if full_response:
                history.append({"role": "assistant", "content": full_response})
                save_history_to_memory(session_id, history)
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
        clear_history_from_memory(session_id)
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