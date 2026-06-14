import logging
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from database_setup.connections import get_db, get_db_ctx
from database_setup.crud.conversation import save_message, get_history as get_history_db
from database_setup.crud.users import get_user_by_id
from schemas.chat import ChatRequest, HistoryResponse, HistoryItem
from utils.config import OPENAI_MODEL, MAX_HISTORY
from utils.helpers import get_openai_client, get_retriever

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store — user_id -> list of messages
# NOTE: single-process only. Under multi-worker deployment, each worker has
# its own copy; user history will be inconsistent across workers.
conversation_memory: dict = defaultdict(list)


# ─── Memory Helpers ───────────────────────────────────────────────────────────

def get_history_from_memory(user_id: int) -> list:
    return list(conversation_memory[user_id])


def save_history_to_memory(user_id: int, history: list):
    conversation_memory[user_id] = history[-MAX_HISTORY:]


def clear_history_from_memory(user_id: int):
    conversation_memory.pop(user_id, None)


# ─── Background save helpers ──────────────────────────────────────────────────

def _save_message_sync(user_id: int, role: str, message: str):
    """Runs in threadpool via BackgroundTasks. Errors are logged, not silent."""
    try:
        with get_db_ctx() as db:
            save_message(db, user_id, role, message)
    except Exception as e:
        logger.error(f"Failed to persist {role} message for user_id={user_id}: {e}", exc_info=True)


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    background_tasks: BackgroundTasks,
    openai_client=Depends(get_openai_client),
    retriever=Depends(get_retriever),
    db: Session = Depends(get_db),
):
    # 1. Auth check (DB session via Depends, retrieval via threadpool)
    try:
        user_result = await run_in_threadpool(get_user_by_id, db, body.user_id)
        nodes = await run_in_threadpool(retriever.retrieve, body.message)
    except Exception as e:
        logger.error(f"Auth/retrieval error for user_id={body.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process request.")

    if not user_result or not user_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found. Please register before chatting.",
        )

    user_name = user_result["name"]
    user_id = body.user_id
    context = "\n".join(n.text for n in nodes) if nodes else "No relevant context found."

    # 2. Load history from memory, append new user message
    history = get_history_from_memory(user_id)
    history.append({"role": "user", "content": body.message})
    save_history_to_memory(user_id, history)

    # Persist user message after response is sent (guaranteed to run, errors logged)
    background_tasks.add_task(_save_message_sync, user_id, "user", body.message)

    # 3. System prompt
    system_prompt = (
        f"You are an expert UAE Tax Assistant representing the E-Numerak platform.\n"
        f"Your primary task is to answer the user's question accurately based on the provided context.\n\n"
        f"--- CONTEXT ---\n{context}\n---------------\n\n"
        f"CRITICAL GUIDELINES:\n"
        f"1. LANGUAGE MATCHING: Detect the language of the user's message. You MUST respond in that exact same language.\n"
        f"2. BREVITY & SCALING: Keep answers brief, direct, and limited strictly to the question asked.\n"
        f"3. FLEXIBLE CONTEXT MATCHING: Use semantic understanding to match the user's intent. "
        f"Even if wording differs, extract the relevant answer from context. "
        f"Only if truly not found, say: \"I'm sorry, but I couldn't find that information.\"\n"
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
        f"Email: info@e-numerak.com\n"
        f"Phone: +971 50 635 8421\n"
        f"Hours: Mon-Fri, 9AM-6PM GST"
    )

    # 4. Stream response
    collected_response: list[str] = []

    async def generate():
        try:
            stream = await openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *[{"role": m["role"], "content": m["content"]} for m in history],
                ],
                stream=True,
            )

            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    collected_response.append(token)
                    yield token

        except Exception as e:
            logger.error(f"OpenAI streaming error for user_id={user_id}: {e}", exc_info=True)
            yield "Sorry, an error occurred while generating the response."

        finally:
            full_response = "".join(collected_response)
            if full_response:
                history.append({"role": "assistant", "content": full_response})
                save_history_to_memory(user_id, history)
                # Persist after streaming finishes - direct call since we're
                # already past the response lifecycle here (generator finally block)
                await run_in_threadpool(_save_message_sync, user_id, "assistant", full_response)
                logger.info(f"Response saved for user_id={user_id}")

    return StreamingResponse(generate(), media_type="text/plain")


# ─── Clear Memory ─────────────────────────────────────────────────────────────

@router.post("/clear-memory/{user_id}")
async def clear_memory(user_id: int):
    """Clear in-memory conversation history — call on New Chat."""
    clear_history_from_memory(user_id)
    logger.info(f"Memory cleared for user_id={user_id}")
    return {"status": "Memory cleared", "user_id": user_id}


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/history/{user_id}", response_model=HistoryResponse)
async def get_history(
    user_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get chat history for a user from the SQLite DB."""
    user_result = await run_in_threadpool(get_user_by_id, db, user_id)
    if not user_result or not user_result.get("success"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    records = await run_in_threadpool(get_history_db, db, user_id, limit, offset)

    return HistoryResponse(
        success=True,
        history=[
            HistoryItem(role=r.role, message=r.message, created_at=r.created_at)
            for r in records
        ],
    )