# ─── Dependency: groq_client + retriever ─────────────────────────────────────

def get_groq_client():
    """Proper FastAPI dependency — no circular import hack needed."""
    from main import groq_client
    return groq_client

def get_retriever():
    from main import retriever
    return retriever

def get_openai_client():
    from main import openai_client
    return openai_client