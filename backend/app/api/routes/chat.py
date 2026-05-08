from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.orchestrator import run_chat_stream
from app.api.dependencies import get_current_user
from app.core.logging import get_logger
import json
import time
import re

router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger()

# ── Prompt injection patterns ─────────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|above|all)",
    r"forget\s+(instructions|everything|context|above)",
    r"system\s*prompt",
    r"show\s+all\s+data",
    r"SELECT\s+\*",
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"return\s+all\s+rows",
    r"as\s+an\s+ai\s+you\s+must",
    r"\boverride\b",
    r"jailbreak",
    r"bypass\s+(security|filter|restriction)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+as\s+(if\s+you\s+are|a\b)",
]

INJECTION_REGEX = re.compile(
    "|".join(INJECTION_PATTERNS),
    re.IGNORECASE
)

AMBIGUOUS_PATTERNS = re.compile(
    r'^(show me|tell me|what is|how is|give me|get me)\s+'
    r'(performance|data|stats|results|metrics|numbers|info|information|details|analysis)\s*\??$',
    re.IGNORECASE
)

FOLLOW_UP_SUGGESTIONS = [
    "Which titles performed best in 2025?",
    "What explains weak comedy performance?",
    "Which city had the strongest engagement in April 2025?",
]


def check_prompt_injection(message: str) -> bool:
    return bool(INJECTION_REGEX.search(message))


def check_ambiguity(message: str) -> str | None:
    msg = message.strip()
    if AMBIGUOUS_PATTERNS.match(msg):
        return (
            "Could you be more specific? For example, which title, genre, "
            "city, or time period are you interested in?\n\n"
            "Try asking something like:\n"
            "- *Which titles performed best in 2025?*\n"
            "- *What explains weak comedy performance?*\n"
            "- *Show me marketing spend by channel*"
        )
    words = msg.split()
    if len(words) <= 2 and '?' not in msg and not any(
        w.lower() in ['compare', 'show', 'list', 'explain', 'what', 'why', 'how', 'which']
        for w in words
    ):
        return (
            "Your question is a bit brief — could you add more context?\n\n"
            "For example:\n"
            "- *Compare Dark Orbit vs Last Kingdom*\n"
            "- *Why is Stellar Run trending recently?*\n"
            "- *Which city had the strongest engagement?*"
        )
    compare_pattern = re.compile(r'\bcompare\b', re.IGNORECASE)
    if compare_pattern.search(msg) and 'vs' not in msg.lower() and 'versus' not in msg.lower():
        return (
            "It looks like you want to compare something — "
            "could you specify what to compare?\n\n"
            "For example: *Compare Dark Orbit vs Last Kingdom performance*"
        )
    return None


def normalize_question(message: str) -> str:
    msg = message.strip()

    # Rewrite "why" questions
    why = re.compile(
        r'^why\s+(is|are|does|do|did|has|have|was|were)\s+',
        re.IGNORECASE
    )
    if why.match(msg):
        stripped = why.sub('', msg).rstrip('?').strip()
        return f"What are the reasons for {stripped}?"

    # Rewrite "which X has the highest/lowest Y"
    which_has = re.compile(
        r'^which\s+(\w+)\s+has\s+the\s+(highest|lowest|best|worst|most|least)\s+(.+?)\??$',
        re.IGNORECASE
    )
    m = which_has.match(msg)
    if m:
        entity      = m.group(1)
        superlative = m.group(2).lower()
        metric      = m.group(3).strip()
        return f"List {entity}s ranked by {metric} from {superlative} to opposite?"

    # Rewrite "what is the highest/lowest X"
    what_is = re.compile(
        r'^what\s+is\s+the\s+(highest|lowest|best|worst|total|average|most|least)\s+',
        re.IGNORECASE
    )
    if what_is.match(msg):
        superlative = what_is.search(msg).group(1).lower()
        stripped    = what_is.sub('', msg).rstrip('?').strip()
        return f"Show me the {superlative} {stripped}?"

    # Rewrite "how many/much" — fixed to avoid "total count of total X"
    how_many = re.compile(r'^how\s+(many|much)\s+', re.IGNORECASE)
    if how_many.match(msg):
        stripped = how_many.sub('', msg).rstrip('?').strip()
        return f"Show me {stripped}?"

    # Rewrite "can/could/would you"
    polite = re.compile(r'^(can|could|would|will)\s+you\s+', re.IGNORECASE)
    if polite.match(msg):
        stripped = polite.sub('', msg).rstrip('?').strip()
        return f"Show me {stripped}?"

    # Rewrite "tell me about"
    tell_me = re.compile(
        r'^tell\s+me\s+(about|more about|regarding)\s+',
        re.IGNORECASE
    )
    if tell_me.match(msg):
        stripped = tell_me.sub('', msg).rstrip('?').strip()
        return f"Provide an analysis of {stripped}?"

    # Rewrite "is/are X better than Y"
    comparison = re.compile(
        r'^(is|are)\s+(.+?)\s+(better|worse|higher|lower|more|less)\s+than\s+',
        re.IGNORECASE
    )
    if comparison.match(msg):
        stripped = msg.rstrip('?').strip()
        return f"Compare the performance metrics for {stripped}?"

    return message


def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    start = time.time()

    # ── Prompt injection check ────────────────────────────────────────────────
    if check_prompt_injection(request.message):
        logger.warning(
            "chat: prompt injection attempt detected",
            extra={"user": current_user["username"], "preview": request.message[:100]}
        )
        async def blocked_stream():
            yield sse_event({
                "type":             "response",
                "answer":           "Your query contains instructions that cannot be processed. "
                                    "Please ask a business question about StreamVault data.",
                "sources":          [],
                "tools_used":       [],
                "confidence":       "low",
                "follow_ups":       [],
                "query_id":         "",
                "escalation_level": None,
                "tool_traces":      [],
            })
        return StreamingResponse(blocked_stream(), media_type="text/event-stream")

    # ── Ambiguity check ───────────────────────────────────────────────────────
    clarification = check_ambiguity(request.message)
    if clarification:
        logger.info("chat: ambiguous question detected",
                    extra={"user": current_user["username"],
                           "preview": request.message[:80]})
        async def clarify_stream():
            yield sse_event({
                "type":             "response",
                "answer":           clarification,
                "sources":          [],
                "tools_used":       [],
                "confidence":       "low",
                "follow_ups":       FOLLOW_UP_SUGGESTIONS,
                "query_id":         "",
                "escalation_level": None,
                "tool_traces":      [],
            })
        return StreamingResponse(clarify_stream(), media_type="text/event-stream")

    # ── Normalize question ────────────────────────────────────────────────────
    original_message = request.message
    message          = normalize_question(request.message)
    if message != original_message:
        logger.info(
            "chat: normalized question",
            extra={
                "original":   original_message[:80],
                "normalized": message[:80],
            }
        )

    logger.info(
        "chat: new request",
        extra={"user": current_user["username"], "msg_preview": request.message[:100]}
    )

    async def event_stream():
        try:
            async for event in run_chat_stream(
                message,
                request.history,
                user=current_user["username"],   # ← pass real username
            ):
                yield sse_event(event)
            duration = round(time.time() - start, 2)
            logger.info(
                "chat: completed",
                extra={"user": current_user["username"], "duration_s": duration}
            )
        except Exception as e:
            logger.error("chat: error", extra={"err": str(e)})
            yield sse_event({
                "type":             "response",
                "answer":           f"Chat processing failed: {str(e)}",
                "sources":          [],
                "tools_used":       [],
                "confidence":       "low",
                "follow_ups":       [],
                "query_id":         "",
                "escalation_level": None,
                "tool_traces":      [],
            })

    return StreamingResponse(event_stream(), media_type="text/event-stream")