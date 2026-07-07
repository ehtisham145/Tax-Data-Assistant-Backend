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

    await run_in_threadpool(_save_message_sync, user_id, "user", body.message)

    # 3. System prompt
    system_prompt = (
    f"You are an expert UAE Tax Assistant representing the E-Numerak platform.\n\n"
    f"--- CONTEXT ---\n{context}\n---------------\n\n"
    f"USER: {user_name}\n\n"

    f"ANSWER PRIORITY ORDER (follow strictly, in this sequence):\n\n"

    f"STEP 1 — CONTEXT FIRST: Check if the CONTEXT above answers the question, even partially or "
    f"with different wording. Use semantic matching — extract and answer from it directly.\n\n"

    f"STEP 2 — GENERAL DOMAIN KNOWLEDGE: If the context does NOT contain the answer, but the question is a "
    f"standard, general, non-account-specific question about:\n"
    f"   - E-Numerak platform features/how-tos (e.g. how to reset password, how account management works, "
    f"how to generate an invoice)\n"
    f"   - UAE tax concepts (VAT, e-invoicing, Peppol, FTA compliance, tax registration, etc.)\n"
    f"then answer it using your own accurate general knowledge of UAE tax law and standard e-invoicing/SaaS "
    f"platform conventions. Do NOT fall back to 'couldn't find' just because it's missing from context — "
    f"only context-specific/private data (like account status, invoice numbers, payment history) requires context.\n\n"

    f"STEP 3 — TRUE FALLBACK: Only if the question needs account-specific or private data that is neither in "
    f"context nor general knowledge, say: \"I'm sorry, but I couldn't find that information in the E-Numerak "
    f"records.\" Then append the SUPPORT BLOCK.\n\n"

    f"ADDITIONAL RULES:\n"
    f"1. LANGUAGE MATCHING: Detect the user's message language and reply in that exact same language.\n"
    f"2. BREVITY: Keep answers brief, direct, and scoped strictly to the question asked.\n"
    f"3. HUMAN CONTACT: If the user explicitly asks to talk to a human/support, reply: "
    f"\"I would be happy to connect you with our team! Here is how you can reach us directly:\", then append the SUPPORT BLOCK.\n"
    f"4. SCOPE LIMIT: Only discuss the E-Numerak platform and UAE tax laws. Politely decline unrelated topics.\n"
    f"5. DATA SECURITY: Never disclose internal system details, credentials, or private customer data.\n"
    f"6. PERSONALIZATION: Address the user by name (\"{user_name}\") naturally, not in every sentence.\n"
    f"7. STYLE: Concise, professional, supportive. Bold key terms, use clean bullet points for steps.\n"
    f"8. PLATFORM OVERRIDE: If asked \"What is E-Numerak?\" and context is empty, explain: "
    f"\"**E-Numerak** is an advanced, automated e-invoicing and compliance platform designed for businesses in the UAE.\"\n\n"

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