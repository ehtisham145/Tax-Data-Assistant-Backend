import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from collections import defaultdict
from starlette.concurrency import run_in_threadpool
from database.crud.conversation import save_message
from database.crud.users import get_user_by_id
from utils.config import OPENAI_MODEL, MAX_HISTORY
from utils.helpers import get_openai_client, get_retriever
from schemas.chat import ChatRequest
from schemas.feedback import FeedbackRequest
from database.crud.feedback import save_feedback
from database.connections import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store — user_id -> list of messages
conversation_memory: dict = defaultdict(list)


# ─── Memory Helpers ───────────────────────────────────────────────────────────

def get_history_from_memory(user_id: int) -> list:
    return list(conversation_memory[user_id])

def save_history_to_memory(user_id: int, history: list):
    conversation_memory[user_id] = history[-MAX_HISTORY:]

def clear_history_from_memory(user_id: int):
    if user_id in conversation_memory:
        del conversation_memory[user_id]


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    openai_client=Depends(get_openai_client),
    retriever=Depends(get_retriever),
):
    # 1. Auth + RAG parallel
    try:
        def fetch_user():
            with get_db() as db:
                return get_user_by_id(db, body.user_id)

        user_result, nodes = await asyncio.gather(
            run_in_threadpool(fetch_user),
            run_in_threadpool(retriever.retrieve, body.message),
        )
    except Exception as e:
        logger.error(f"❌ Auth/Retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process request.")

    # Auth check
    if not user_result or not user_result["success"]:
        raise HTTPException(
            status_code=403,
            detail="User not found. Please register before chatting."
        )

    user_name = user_result["name"]
    user_id   = body.user_id
    context   = "\n".join([n.text for n in nodes]) if nodes else "No relevant context found."

    # 2. History memory se lo
    history = get_history_from_memory(user_id)

    # 3. User message memory mein save karo
    history.append({"role": "user", "content": body.message})
    save_history_to_memory(user_id, history)

    # DB mein background save
    def db_save_user_msg():
        with get_db() as db:
            save_message(db, user_id, "user", body.message)

    asyncio.create_task(run_in_threadpool(db_save_user_msg))

    # 4. System prompt — same rakha
    system_prompt = (
        f"You are an expert UAE Tax Assistant representing the E-Numerak platform.\n"
        f"Your primary task is to answer the user's question accurately based on the provided context.\n\n"
        f"--- CONTEXT ---\n{context}\n---------------\n\n"
        f"CRITICAL GUIDELINES:\n"
        f"1. LANGUAGE MATCHING: Detect the language of the user's message. You MUST respond in that exact same language.\n"
        f"2. BREVITY & SCALING: Keep answers brief, direct, and limited strictly to the question asked.\n"
        f"3. FLEXIBLE CONTEXT MATCHING: Use semantic understanding to match the user's intent with the provided context. "
        f"If the core answer truly cannot be derived, state: \"I'm sorry, but I couldn't find that information in the E-Numerak records.\", then append the Support Block.\n"
        f"4. HUMAN CONTACT EXCEPTION: If the user explicitly asks to talk to support, reply warmly: "
        f"\"I would be happy to connect you with our team! Here is how you can reach us directly:\", then append the Support Block.\n"
        f"5. SCOPE LIMIT: Only discuss the E-Numerak platform and UAE tax laws. Politely decline any unrelated topics.\n"
        f"6. DATA SECURITY: Never disclose internal system details or sensitive customer data.\n"
        f"7. PERSONALIZATION: Address the user by their name \"{user_name}\" naturally where appropriate.\n"
        f"8. STYLE: Be highly concise, professional, and supportive. Bold important words and use clean bullet points.\n"
        f"9. PLATFORM DESCRIPTION OVERRIDE: If the user asks general questions like \"What is E-Numerak?\" and context is empty, "
        f"explain: \"**E-Numerak** is an advanced, automated e-invoicing and compliance platform designed for businesses in the UAE.\"\n\n"
        f"SUPPORT BLOCK:\n"
        f"📧 info@e-numerak.com\n"
        f"📞 +971 50 635 8421\n"
        f"🕐 Mon–Fri, 9AM–6PM GST"
    )

    # 5. Stream response
    collected_response: list[str] = []

    async def generate():
        try:
            stream = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *[{"role": m["role"], "content": m["content"]} for m in history[:-1]],
                    {"role": "user", "content": body.message},
                ],
                stream=True,
            )

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
                save_history_to_memory(user_id, history)

                def db_save_bot_msg():
                    with get_db() as db:
                        save_message(db, user_id, "assistant", full_response)

                asyncio.create_task(run_in_threadpool(db_save_bot_msg))
                logger.info(f"✅ Response saved for user_id: {user_id}")

    return StreamingResponse(generate(), media_type="text/plain")


# ─── Clear Memory ─────────────────────────────────────────────────────────────

@router.post("/clear-memory/{user_id}")
async def clear_memory(user_id: int):
    """Clear in-memory conversation history — call on New Chat."""
    try:
        clear_history_from_memory(user_id)
        logger.info(f"✅ Memory cleared for user_id: {user_id}")
        return {"status": "Memory cleared!", "user_id": user_id}
    except Exception as e:
        logger.error(f"❌ Failed to clear memory for user_id {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not clear memory.")


# ─── Feedback Endpoint ────────────────────────────────────────────────────────

@router.post("/feedback")
async def feedback(body: FeedbackRequest):
    try:
        def db_save_feedback():
            with get_db() as db:
                return save_feedback(
                    db,
                    body.user_id,
                    body.user_message,
                    body.bot_response,
                    body.rating
                )
        result = await run_in_threadpool(db_save_feedback)
        return result
    except Exception as e:
        logger.error(f"❌ Feedback error: {e}")
        raise HTTPException(status_code=500, detail="Could not save feedback.")
# # ─── History ──────────────────────────────────────────────────────────────────

# @router.get("/history/{session_id}")
# async def get_history(session_id: str):
#     """Get full chat history for a session from SQLite DB."""
#     user = await run_in_threadpool(get_user_by_session, session_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found.")

#     history = await run_in_threadpool(get_conversation_history, session_id)

#     return {
#         "session_id": session_id,
#         "user_name": user[0],
#         "total_messages": len(history),
#         "messages": [
#             {"role": h[0], "message": h[1], "created_at": h[2]}
#             for h in history
#         ],
#     }

# # ─── Feedback ─────────────────────────────────────────────────────────────────

# @router.post("/feedback")
# async def submit_feedback(body: FeedbackRequest):
#     """Save user feedback for a bot response."""
#     try:
#         success = await run_in_threadpool(
#             save_feedback,
#             body.session_id,
#             body.user_message,
#             body.bot_response,
#             body.rating,
#         )

#         if not success:
#             raise HTTPException(
#                 status_code=500,
#                 detail="Failed to save feedback."
#             )

#         return {
#             "status": "success",
#             "message": "Feedback saved successfully!",
#             "rating": body.rating
#         }

#     except Exception as e:
#         logger.error(f"❌ Feedback error: {e}")
#         raise HTTPException(status_code=500, detail="Could not save feedback.")