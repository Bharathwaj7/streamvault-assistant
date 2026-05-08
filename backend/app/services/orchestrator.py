import json
import time
import asyncio
import hashlib
import re
import uuid
from groq import AsyncGroq, RateLimitError, BadRequestError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.registry import get_groq_tool_schemas, execute_tool
from app.schemas.chat import ChatResponse, ToolCallTrace, ChatMessage
from app.services.schema import get_db_schema

logger   = get_logger()
settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are StreamVault Analytics Assistant for StreamVault Entertainment's internal analytics team.

AVAILABLE TOOLS:

1. query_database — SQLite. EXACT schema (use only these column names):
{db_schema}

2. search_documents — PDF reports: quarterly_executive_report, campaign_performance_summary, content_roadmap, policy_guidelines, audience_behavior_report

3. analyze_csv_data — CSV analytics. Operations:
   top_movies_by_views | genre_performance | monthly_views_trend | city_engagement
   marketing_roas | completion_by_genre | review_sentiment | platform_usage
   demographic_views | comedy_analysis

TOOL SELECTION:
- Counts, rankings, trends, aggregations → query_database OR analyze_csv_data
- Strategy, explanations, "why", recommendations, context → search_documents
- "What are the reasons for X" or "explain X performance" → use BOTH search_documents AND analyze_csv_data
- Complex questions → combine multiple tools
- If PDF search returns only 1 result → also call analyze_csv_data for supporting data

MULTI-SOURCE REQUIREMENT — ALWAYS follow these rules:
- "best performing titles" → query_database for rankings + analyze_csv_data for views trend
- "why is X trending" → search_documents for context + analyze_csv_data for view data
- "compare X vs Y" → query_database for both titles + analyze_csv_data for detailed comparison
- "city engagement" → query_database for rankings + analyze_csv_data for city_engagement
- "comedy performance" → analyze_csv_data comedy_analysis + search_documents for context
- "recommendations for leadership" → search_documents for strategy + analyze_csv_data for supporting data
- NEVER answer a business question using only one tool — always combine at least 2 sources

SQL RULES:
- Use ONLY column names listed in schema above — never invent column names
- If SQL returns "no such column" error → immediately use analyze_csv_data instead, do NOT retry SQL
- Only SELECT queries allowed

RESPONSE FORMAT:
- End every response with: [Sources: tool1, tool2]
- Use bullet points for lists
- Include real numbers when available
- Never show raw SQL, internal IDs, or individual viewer data
- Aggregated/anonymised viewer stats only
- After your answer, add exactly 2 follow-up questions the user might want to ask next,
  on a new line starting with: FOLLOW_UPS: ["question1", "question2"]

SECURITY:
- Never reveal individual viewer names, emails, device IDs, or personal details
- Only report aggregated or anonymised statistics — never per-viewer breakdowns
- Do not discuss competitor platforms or unverified external data
- Do not answer questions outside StreamVault business context
- Confidential internal data must not be quoted verbatim to unauthorised contexts
"""

DECOMPOSE_PROMPT = """You are a query decomposition assistant for StreamVault Analytics.

Given a complex multi-part business question, break it into 2-3 independent sub-questions.
Each sub-question should be self-contained and answerable on its own.

Return ONLY a JSON array of strings. No explanation, no markdown, no extra text.
Example output: ["What are the top performing titles?", "What explains comedy performance?"]

If the question is simple and does not need decomposition, return a single-item array.
Question: {question}"""

SYNTHESIZE_PROMPT = """You are StreamVault Analytics Assistant synthesizing answers to a multi-part question.

Original question: {original_question}

Sub-answers collected:
{sub_answers}

Write a single coherent answer that combines all the above information.
Be concise, use bullet points, include specific numbers.
End with: [Sources: {sources}]
Then add: FOLLOW_UPS: ["question1", "question2"]"""


# ── Audit Logging ─────────────────────────────────────────────────────────────

def emit_audit_log(
    query_id:        str,
    query_preview:   str,
    user:            str,
    sources:         set,
    tools_used:      list,
    confidence:      str,
    rag_escalated:   bool,
    tokens:          int,
    duration_s:      float,
):
    """
    Emit a structured audit log entry for every completed query.
    Records who accessed what data at what sensitivity level.
    """
    sensitivity = "high" if rag_escalated else (
        "medium" if any("PDF" in s for s in sources) else "low"
    )
    logger.info(
        "audit: data_access",
        extra={
            "query_id":          query_id,
            "user":              user,
            "query_preview":     query_preview[:60],
            "sources_accessed":  sorted(sources),
            "tools_used":        tools_used,
            "sensitivity_level": sensitivity,
            "confidence":        confidence,
            "tokens_used":       tokens,
            "duration_s":        duration_s,
            "timestamp":         time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )


def compute_confidence(
    tool_results_count: int,
    rag_chunks_count:   int,
    iteration_cap_hit:  bool,
    tool_failed:        bool,
    rag_escalated:      bool = False,
    unverified_claims:  bool = False,
) -> str:
    score = 0
    if tool_results_count >= 3:
        score += 2
    elif tool_results_count >= 1:
        score += 1
    if rag_chunks_count >= 3:
        score += 2
    elif rag_chunks_count >= 1:
        score += 1
    if iteration_cap_hit:
        score -= 2
    if tool_failed:
        score -= 1
    if rag_escalated:
        score -= 1
    if unverified_claims:
        score -= 1
    if score >= 4:
        return "high"
    elif score >= 2:
        return "medium"
    else:
        return "low"


def extract_follow_ups(answer: str) -> tuple[str, list[str]]:
    follow_ups   = []
    clean_answer = answer
    if "FOLLOW_UPS:" in answer:
        parts = answer.split("FOLLOW_UPS:")
        clean_answer = parts[0].strip()
        try:
            follow_ups = json.loads(parts[1].strip())
            if not isinstance(follow_ups, list):
                follow_ups = []
        except (json.JSONDecodeError, IndexError):
            follow_ups = []
    return clean_answer, follow_ups


def make_cache_key(tool_name: str, arguments: dict) -> str:
    raw = json.dumps({"tool": tool_name, "args": arguments}, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r'\b\d+(?:\.\d+)?%?\b', text))


def extract_proper_nouns(text: str) -> set[str]:
    return set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text))


def build_ground_truth(tool_traces: list[ToolCallTrace]) -> str:
    parts = []
    for trace in tool_traces:
        parts.append(json.dumps(trace.result, default=str).lower())
    return " ".join(parts)


def check_hallucination(
    answer:      str,
    tool_traces: list[ToolCallTrace],
) -> tuple[bool, list[str]]:
    if not tool_traces:
        return False, []

    ground_truth = build_ground_truth(tool_traces)
    unverified   = []

    answer_numbers = extract_numbers(answer)
    for number in answer_numbers:
        try:
            val = float(number.replace('%', ''))
            if val <= 10 or (2000 <= val <= 2100):
                continue
        except ValueError:
            continue
        if number.lower() not in ground_truth:
            unverified.append(f"number: {number}")

    proper_nouns = extract_proper_nouns(answer)
    skip_words = {
        "StreamVault", "Sources", "SQL", "CSV", "PDF",
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday", "January",
        "February", "March", "April", "May", "June",
        "July", "August", "September", "October",
        "November", "December",
        "According", "Additionally", "Furthermore", "However",
        "Therefore", "Moreover", "Nevertheless", "Consequently",
        "Overall", "Finally", "Summary", "Note", "Based",
        "Given", "While", "Although", "Despite", "Since",
        "Follow", "Sources", "Helpful", "Confidence",
        "These", "This", "That", "Their", "There",
        "They", "Them", "Here", "Both", "Each",
        "Action", "Drama", "Comedy", "Thriller", "Romance",
        "Stellar", "Iron", "Neon", "Dark", "Last", "Echoes",
        "Velocity", "Punchline", "Comic", "Laugh", "Crimson",
        "Kingdom", "Protocol", "Dynasty", "Orbit", "Tomorrow",
        "Analysis", "Report", "Performance", "Review", "Data",
        "Audience", "Marketing", "Campaign", "Regional", "Genre",
        "Quarterly", "Executive", "Internal", "Platform",
        # Common words incorrectly flagged
        "Reviews", "Genres", "Titles", "Views", "Score",
        "Scores", "Users", "Viewers", "Content", "Strategy",
    }
    for noun in proper_nouns:
        if noun in skip_words:
            continue
        if len(noun) < 4:
            continue
        if '\n' in noun:          # ← skip multiline matches
            continue
        if noun.lower() not in ground_truth:
            unverified.append(f"claim: {noun}")

    has_unverified = len(unverified) > 0
    if has_unverified:
        logger.warning(
            "hallucination_guard: unverified claims detected",
            extra={"count": len(unverified), "items": unverified[:5]}
        )
    return has_unverified, unverified

    
async def call_groq_with_retry(client, **kwargs):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await client.chat.completions.create(**kwargs)
        except RateLimitError:
            wait_time = 15 * (attempt + 1)
            logger.warning(
                f"orchestrator: rate limit hit, retrying in {wait_time}s",
                extra={"attempt": attempt + 1, "wait_s": wait_time}
            )
            await asyncio.sleep(wait_time)
        except BadRequestError:
            raise
    raise Exception(
        "Groq rate limit exceeded. Please wait 60 seconds and try again."
    )


def is_complex_question(message: str) -> bool:
    patterns = [
        r'\band\s+also\b',
        r'\bas\s+well\s+as\b',
        r'\bplus\b',
        r'\badditionally\b',
        r'\bboth\s+.+\s+and\b',
        r'\band\s+what\b',
        r'\band\s+how\b',
        r'\band\s+why\b',
        r'\band\s+which\b',
    ]
    for pattern in patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return True
    if message.count('?') >= 2:
        return True
    return False


async def decompose_question(
    client:  AsyncGroq,
    message: str,
) -> list[str]:
    try:
        prompt = DECOMPOSE_PROMPT.format(question=message)
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r'```json|```', '', raw).strip()
        sub_queries = json.loads(raw)
        if isinstance(sub_queries, list) and len(sub_queries) > 0:
            logger.info(
                "decomposer: split question",
                extra={"original": message[:80], "parts": len(sub_queries)}
            )
            return sub_queries
    except Exception as e:
        logger.warning("decomposer: failed, using original",
                       extra={"exc": str(e)[:80]})
    return [message]


async def synthesize_answers(
    client:            AsyncGroq,
    original_question: str,
    sub_answers:       list[dict],
) -> str:
    all_sources = set()
    for sa in sub_answers:
        all_sources.update(sa.get("sources", []))

    sub_answers_text = ""
    for i, sa in enumerate(sub_answers, 1):
        sub_answers_text += f"\n--- Part {i}: {sa['question']} ---\n{sa['answer']}\n"

    prompt = SYNTHESIZE_PROMPT.format(
        original_question=original_question,
        sub_answers=sub_answers_text,
        sources=", ".join(sorted(all_sources)) or "multiple sources",
    )

    try:
        response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("synthesizer: failed, joining answers",
                       extra={"exc": str(e)[:80]})
        return "\n\n".join(sa["answer"] for sa in sub_answers)


async def _execute_tool_call(
    tool_name:       str,
    arguments:       dict,
    tool_call_cache: dict,
    tool_traces:     list,
    sources:         set,
    messages:        list,
    tool_call_id:    str,
) -> tuple[int, int, bool, bool]:
    start_ms = int(time.time() * 1000)
    result   = await execute_tool(tool_name, arguments)
    duration = int(time.time() * 1000) - start_ms

    rag_escalated_delta = False
    rag_chunks          = 0

    if tool_name == "query_database":
        sources.add("SQL Database")

    elif tool_name == "search_documents":
        if isinstance(result, dict):
            if result.get("escalation_needed") and result.get("next_level"):
                next_level    = result["next_level"]
                current_level = result.get("sensitivity_used", "low")
                logger.info(
                    "orchestrator: RAG escalating sensitivity",
                    extra={"from": current_level, "to": next_level}
                )
                rag_escalated_delta      = True
                arguments["sensitivity"] = next_level
                result = await execute_tool(tool_name, arguments)
                tool_call_cache[make_cache_key(tool_name, arguments)] = result

            if "passages" in result:
                rag_chunks = len(result["passages"])
                for p in result["passages"]:
                    sources.add(f"PDF: {p.get('source', 'document')}")

    elif tool_name == "analyze_csv_data":
        sources.add("CSV Analytics")

    result_ok = isinstance(result, dict) and "exc" not in result and "error" not in result
    tool_call_cache[make_cache_key(tool_name, arguments)] = result

    tool_traces.append(ToolCallTrace(
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        duration_ms=duration,
    ))

    messages.append({
        "role":         "tool",
        "tool_call_id": tool_call_id,
        "content":      json.dumps(result, default=str)[:2000],
    })

    rag_chunks_delta = rag_chunks if tool_name == "search_documents" else 0
    return (1 if result_ok else 0), rag_chunks_delta, (not result_ok), rag_escalated_delta


async def run_single_query(
    client:        AsyncGroq,
    tools:         list,
    system_prompt: str,
    message:       str,
    history:       list[ChatMessage],
) -> dict:
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-4:]:
        messages.append({"role": h.role.value, "content": h.content})
    messages.append({"role": "user", "content": message})

    tool_traces:       list[ToolCallTrace] = []
    sources:           set[str]            = set()
    total_tokens       = 0
    iteration_cap_hit  = False
    tool_failed        = False
    rag_chunks_count   = 0
    tool_results_count = 0
    rag_escalated      = False
    tool_call_cache:   dict                = {}

    MAX_ITERATIONS = 4
    for iteration in range(MAX_ITERATIONS):
        try:
            response = await call_groq_with_retry(
                client,
                model=settings.groq_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=600,
                temperature=0.1,
            )
        except BadRequestError as e:
            err_str = str(e)
            if "tool_use_failed" in err_str or "tool call validation" in err_str:
                if iteration == 0 and not tool_traces:
                    simplified = f"Show me data and analysis for: {message}"
                    messages[-1] = {"role": "user", "content": simplified}
                    try:
                        response = await call_groq_with_retry(
                            client,
                            model=settings.groq_model,
                            messages=messages,
                            tools=tools,
                            tool_choice="auto",
                            max_tokens=600,
                            temperature=0.1,
                        )
                    except Exception:
                        return {
                            "question": message, "answer": "",
                            "sources": [], "tool_traces": [],
                            "confidence": "low", "tokens": 0,
                        }
                else:
                    break
            else:
                raise
        except Exception as e:
            logger.error("run_single_query: failed", extra={"exc": str(e)[:80]})
            break

        total_tokens += response.usage.total_tokens if response.usage else 0
        msg           = response.choices[0].message

        messages.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (msg.tool_calls or [])
            ] if msg.tool_calls else [],
        })

        if not msg.tool_calls:
            final_answer             = msg.content or ""
            clean_answer, follow_ups = extract_follow_ups(final_answer)
            has_unverified, _        = check_hallucination(clean_answer, tool_traces)
            confidence = compute_confidence(
                tool_results_count, rag_chunks_count,
                iteration_cap_hit, tool_failed,
                rag_escalated=rag_escalated,
                unverified_claims=has_unverified,
            )
            return {
                "question":    message,
                "answer":      clean_answer,
                "sources":     sorted(sources),
                "tool_traces": tool_traces,
                "confidence":  confidence,
                "tokens":      total_tokens,
            }

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            cache_key = make_cache_key(tool_name, arguments)
            if cache_key in tool_call_cache:
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      json.dumps(tool_call_cache[cache_key], default=str)[:2000],
                })
                continue

            r_count, r_rag, r_failed, r_esc = await _execute_tool_call(
                tool_name, arguments, tool_call_cache,
                tool_traces, sources, messages, tool_call.id
            )
            tool_results_count += r_count
            rag_chunks_count   += r_rag
            tool_failed         = tool_failed or r_failed
            rag_escalated       = rag_escalated or r_esc

    return {
        "question":    message,
        "answer":      "",
        "sources":     sorted(sources),
        "tool_traces": tool_traces,
        "confidence":  "low",
        "tokens":      total_tokens,
    }


async def run_chat(
    message: str,
    history: list[ChatMessage],
    user:    str = "system",
) -> ChatResponse:

    start_time = time.time()
    query_id   = str(uuid.uuid4())
    client     = AsyncGroq(api_key=settings.groq_api_key)
    tools      = get_groq_tool_schemas()

    db_schema     = await get_db_schema()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)

    logger.info("orchestrator: starting chat", extra={"query": message[:100]})

    # ── Query Decomposition ───────────────────────────────────────────────────
    if is_complex_question(message):
        logger.info("orchestrator: complex question detected — decomposing")
        sub_queries = await decompose_question(client, message)

        if len(sub_queries) > 1:
            logger.info("orchestrator: running sub-queries",
                        extra={"count": len(sub_queries)})

            all_traces      = []
            all_sources     = set()
            total_tokens    = 0
            sub_answers     = []
            all_confidences = []

            for sub_query in sub_queries:
                logger.info("orchestrator: running sub-query",
                            extra={"query": sub_query[:80]})
                result = await run_single_query(
                    client, tools, system_prompt, sub_query, history
                )
                if result["answer"]:
                    sub_answers.append(result)
                    all_traces.extend(result["tool_traces"])
                    all_sources.update(result["sources"])
                    total_tokens += result["tokens"]
                    all_confidences.append(result["confidence"])

            if sub_answers:
                logger.info("orchestrator: synthesizing sub-answers",
                            extra={"count": len(sub_answers)})
                synthesized = await synthesize_answers(client, message, sub_answers)
                clean_answer, follow_ups = extract_follow_ups(synthesized)

                confidence_order = {"high": 2, "medium": 1, "low": 0}
                min_confidence = min(
                    all_confidences,
                    key=lambda c: confidence_order.get(c, 0),
                    default="medium"
                )

                emit_audit_log(
                    query_id      = query_id,
                    query_preview = message,
                    user          = user,
                    sources       = all_sources,
                    tools_used    = list({t.tool_name for t in all_traces}),
                    confidence    = min_confidence,
                    rag_escalated = False,
                    tokens        = total_tokens,
                    duration_s    = round(time.time() - start_time, 2),
                )

                logger.info("orchestrator: decomposed query complete",
                            extra={
                                "sub_queries":  len(sub_queries),
                                "confidence":   min_confidence,
                                "total_tokens": total_tokens,
                            })

                return ChatResponse(
                    answer=clean_answer,
                    sources=sorted(all_sources),
                    tool_traces=all_traces,
                    model=settings.groq_model,
                    tokens_used=total_tokens,
                    confidence=min_confidence,
                    follow_ups=follow_ups,
                    escalation_level=None,
                )

    # ── Single query agentic loop ─────────────────────────────────────────────
    messages_list = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages_list.append({"role": h.role.value, "content": h.content})
    messages_list.append({"role": "user", "content": message})

    tool_traces:       list[ToolCallTrace] = []
    sources:           set[str]            = set()
    total_tokens       = 0
    iteration_cap_hit  = False
    tool_failed        = False
    rag_chunks_count   = 0
    tool_results_count = 0
    rag_escalated      = False
    unverified_claims  = False
    tool_call_cache:   dict                = {}

    MAX_ITERATIONS = 5
    for iteration in range(MAX_ITERATIONS):
        logger.info(f"orchestrator: iteration {iteration + 1}")

        try:
            response = await call_groq_with_retry(
                client,
                model=settings.groq_model,
                messages=messages_list,
                tools=tools,
                tool_choice="auto",
                max_tokens=800,
                temperature=0.1,
            )

        except BadRequestError as e:
            err_str = str(e)
            if "tool_use_failed" in err_str or "tool call validation" in err_str:
                logger.warning(
                    "orchestrator: tool format error",
                    extra={"iteration": iteration + 1}
                )
                if iteration == 0 and not tool_traces:
                    simplified = f"Show me data and analysis for: {message}"
                    messages_list[-1] = {"role": "user", "content": simplified}
                    try:
                        retry_response = await call_groq_with_retry(
                            client,
                            model=settings.groq_model,
                            messages=messages_list,
                            tools=tools,
                            tool_choice="auto",
                            max_tokens=800,
                            temperature=0.1,
                        )
                        total_tokens += retry_response.usage.total_tokens if retry_response.usage else 0
                        retry_msg     = retry_response.choices[0].message

                        messages_list.append({
                            "role":       "assistant",
                            "content":    retry_msg.content or "",
                            "tool_calls": [
                                {
                                    "id":       tc.id,
                                    "type":     "function",
                                    "function": {
                                        "name":      tc.function.name,
                                        "arguments": tc.function.arguments,
                                    },
                                }
                                for tc in (retry_msg.tool_calls or [])
                            ] if retry_msg.tool_calls else [],
                        })

                        if not retry_msg.tool_calls:
                            final_answer             = retry_msg.content or ""
                            clean_answer, follow_ups = extract_follow_ups(final_answer)
                            confidence = compute_confidence(
                                tool_results_count, rag_chunks_count,
                                iteration_cap_hit, tool_failed,
                                rag_escalated=rag_escalated,
                            )
                            emit_audit_log(
                                query_id      = query_id,
                                query_preview = message,
                                user          = user,
                                sources       = sources,
                                tools_used    = [t.tool_name for t in tool_traces],
                                confidence    = confidence,
                                rag_escalated = rag_escalated,
                                tokens        = total_tokens,
                                duration_s    = round(time.time() - start_time, 2),
                            )
                            return ChatResponse(
                                answer=clean_answer,
                                sources=sorted(sources),
                                tool_traces=tool_traces,
                                model=settings.groq_model,
                                tokens_used=total_tokens,
                                confidence=confidence,
                                follow_ups=follow_ups,
                                escalation_level="medium" if rag_escalated else None,
                            )

                        for tool_call in retry_msg.tool_calls:
                            tool_name = tool_call.function.name
                            try:
                                arguments = json.loads(tool_call.function.arguments)
                            except json.JSONDecodeError:
                                arguments = {}
                            cache_key = make_cache_key(tool_name, arguments)
                            if cache_key in tool_call_cache:
                                messages_list.append({
                                    "role":         "tool",
                                    "tool_call_id": tool_call.id,
                                    "content":      json.dumps(tool_call_cache[cache_key], default=str)[:2000],
                                })
                                continue
                            r_count, r_rag, r_failed, r_esc = await _execute_tool_call(
                                tool_name, arguments, tool_call_cache,
                                tool_traces, sources, messages_list, tool_call.id
                            )
                            tool_results_count += r_count
                            rag_chunks_count   += r_rag
                            tool_failed         = tool_failed or r_failed
                            rag_escalated       = rag_escalated or r_esc
                        continue

                    except Exception:
                        pass

                confidence = compute_confidence(
                    tool_results_count, rag_chunks_count,
                    iteration_cap_hit, tool_failed=True,
                    rag_escalated=rag_escalated,
                )
                emit_audit_log(
                    query_id      = query_id,
                    query_preview = message,
                    user          = user,
                    sources       = sources,
                    tools_used    = [t.tool_name for t in tool_traces],
                    confidence    = "low",
                    rag_escalated = rag_escalated,
                    tokens        = total_tokens,
                    duration_s    = round(time.time() - start_time, 2),
                )
                if tool_traces:
                    return ChatResponse(
                        answer="I retrieved some data but hit a formatting issue. "
                               "Please try rephrasing slightly.",
                        sources=sorted(sources),
                        tool_traces=tool_traces,
                        model=settings.groq_model,
                        tokens_used=total_tokens,
                        confidence=confidence,
                        follow_ups=[],
                        escalation_level="medium" if rag_escalated else None,
                    )
                return ChatResponse(
                    answer="I had trouble calling the right tool. "
                           "Try rephrasing your question.",
                    sources=[],
                    tool_traces=[],
                    model=settings.groq_model,
                    tokens_used=total_tokens,
                    confidence="low",
                    follow_ups=[],
                    escalation_level=None,
                )
            raise

        except Exception as e:
            logger.error("orchestrator: groq call failed", extra={"exc": str(e)})
            raise

        total_tokens += response.usage.total_tokens if response.usage else 0
        choice        = response.choices[0]
        msg           = choice.message

        messages_list.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {
                        "name":      tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (msg.tool_calls or [])
            ] if msg.tool_calls else [],
        })

        if not msg.tool_calls:
            final_answer             = msg.content or "I couldn't generate a response."
            clean_answer, follow_ups = extract_follow_ups(final_answer)

            has_unverified, unverified_items = check_hallucination(
                clean_answer, tool_traces
            )
            unverified_claims = has_unverified

            if has_unverified:
                logger.warning(
                    "hallucination_guard: unverified claims detected",
                    extra={"count": len(unverified_items), "items": unverified_items[:5]}
                )

            confidence = compute_confidence(
                tool_results_count, rag_chunks_count,
                iteration_cap_hit, tool_failed,
                rag_escalated=rag_escalated,
                unverified_claims=unverified_claims,
            )

            logger.info("orchestrator: final answer ready",
                        extra={
                            "tokens":            total_tokens,
                            "confidence":        confidence,
                            "unverified_claims": has_unverified,
                        })

            emit_audit_log(
                query_id      = query_id,
                query_preview = message,
                user          = user,
                sources       = sources,
                tools_used    = list({t.tool_name for t in tool_traces}),
                confidence    = confidence,
                rag_escalated = rag_escalated,
                tokens        = total_tokens,
                duration_s    = round(time.time() - start_time, 2),
            )

            return ChatResponse(
                answer=clean_answer,
                sources=sorted(sources),
                tool_traces=tool_traces,
                model=settings.groq_model,
                tokens_used=total_tokens,
                confidence=confidence,
                follow_ups=follow_ups,
                escalation_level="medium" if rag_escalated else None,
            )

        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            cache_key = make_cache_key(tool_name, arguments)
            if cache_key in tool_call_cache:
                logger.info(
                    "orchestrator: duplicate tool call — served from cache",
                    extra={"tool": tool_name, "cache_key": cache_key[:8]}
                )
                messages_list.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      json.dumps(tool_call_cache[cache_key], default=str)[:2000],
                })
                continue

            logger.info(f"orchestrator: calling tool {tool_name}",
                        extra={"tool_args": arguments})

            r_count, r_rag, r_failed, r_esc = await _execute_tool_call(
                tool_name, arguments, tool_call_cache,
                tool_traces, sources, messages_list, tool_call.id
            )
            tool_results_count += r_count
            rag_chunks_count   += r_rag
            tool_failed         = tool_failed or r_failed
            rag_escalated       = rag_escalated or r_esc

    logger.warning("orchestrator: hit max iterations")
    iteration_cap_hit = True
    confidence = compute_confidence(
        tool_results_count, rag_chunks_count,
        iteration_cap_hit, tool_failed,
        rag_escalated=rag_escalated,
        unverified_claims=unverified_claims,
    )
    emit_audit_log(
        query_id      = query_id,
        query_preview = message,
        user          = user,
        sources       = sources,
        tools_used    = list({t.tool_name for t in tool_traces}),
        confidence    = confidence,
        rag_escalated = rag_escalated,
        tokens        = total_tokens,
        duration_s    = round(time.time() - start_time, 2),
    )
    return ChatResponse(
        answer="I gathered data but reached the processing limit. "
               "Please try a more specific question.",
        sources=sorted(sources),
        tool_traces=tool_traces,
        model=settings.groq_model,
        tokens_used=total_tokens,
        confidence=confidence,
        follow_ups=[],
        escalation_level="medium" if rag_escalated else None,
    )


# ── SSE Streaming ─────────────────────────────────────────────────────────────

async def run_chat_stream(
    message: str,
    history: list[ChatMessage],
    user:    str = "system",
):
    """
    Async generator yielding SSE event dicts as the agent works.
    """
    query_id   = str(uuid.uuid4())
    start_time = time.time()

    client = AsyncGroq(api_key=settings.groq_api_key)
    tools  = get_groq_tool_schemas()

    db_schema     = await get_db_schema()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(db_schema=db_schema)

    logger.info("orchestrator: starting stream", extra={"query": message[:100]})

    # ── Query Decomposition ───────────────────────────────────────────────────
    if is_complex_question(message):
        yield {"type": "decomposing", "message": "Breaking down complex question..."}
        sub_queries = await decompose_question(client, message)

        if len(sub_queries) > 1:
            yield {
                "type":        "decomposed",
                "sub_queries": sub_queries,
                "count":       len(sub_queries),
            }

            all_traces      = []
            all_sources     = set()
            total_tokens    = 0
            sub_answers     = []
            all_confidences = []

            for i, sub_query in enumerate(sub_queries):
                yield {
                    "type":  "sub_query_start",
                    "index": i + 1,
                    "total": len(sub_queries),
                    "query": sub_query,
                }
                result = await run_single_query(
                    client, tools, system_prompt, sub_query, history
                )
                if result["answer"]:
                    sub_answers.append(result)
                    all_traces.extend(result["tool_traces"])
                    all_sources.update(result["sources"])
                    total_tokens += result["tokens"]
                    all_confidences.append(result["confidence"])

                    for trace in result["tool_traces"]:
                        yield {
                            "type":            "tool_call",
                            "tool_name":       trace.tool_name,
                            "inputs":          {k: str(v)[:50] for k, v in trace.arguments.items()},
                            "outputs_summary": f"{len(str(trace.result))} chars",
                            "latency_ms":      trace.duration_ms,
                        }

                    yield {
                        "type":    "sub_query_done",
                        "index":   i + 1,
                        "sources": result["sources"],
                    }

            if sub_answers:
                yield {"type": "synthesizing", "message": "Synthesizing answers..."}
                synthesized = await synthesize_answers(client, message, sub_answers)
                clean_answer, follow_ups = extract_follow_ups(synthesized)

                confidence_order = {"high": 2, "medium": 1, "low": 0}
                min_confidence = min(
                    all_confidences,
                    key=lambda c: confidence_order.get(c, 0),
                    default="medium"
                )

                emit_audit_log(
                    query_id      = query_id,
                    query_preview = message,
                    user          = user,
                    sources       = all_sources,
                    tools_used    = list({t.tool_name for t in all_traces}),
                    confidence    = min_confidence,
                    rag_escalated = False,
                    tokens        = total_tokens,
                    duration_s    = round(time.time() - start_time, 2),
                )

                yield {
                    "type":             "response",
                    "answer":           clean_answer,
                    "sources":          sorted(all_sources),
                    "tools_used":       list({t.tool_name for t in all_traces}),
                    "confidence":       min_confidence,
                    "follow_ups":       follow_ups,
                    "query_id":         query_id,
                    "escalation_level": None,
                    "tool_traces":      [
                        {
                            "tool_name":   t.tool_name,
                            "arguments":   t.arguments,
                            "result":      t.result,
                            "duration_ms": t.duration_ms,
                        }
                        for t in all_traces
                    ],
                }
                return

    # ── Single query SSE loop ─────────────────────────────────────────────────
    messages_list = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages_list.append({"role": h.role.value, "content": h.content})
    messages_list.append({"role": "user", "content": message})

    tool_traces:       list[ToolCallTrace] = []
    sources:           set[str]            = set()
    total_tokens       = 0
    tool_failed        = False
    rag_chunks_count   = 0
    tool_results_count = 0
    rag_escalated      = False
    unverified_claims  = False
    tool_call_cache:   dict                = {}

    MAX_ITERATIONS = 5
    for iteration in range(MAX_ITERATIONS):
        try:
            response = await call_groq_with_retry(
                client,
                model=settings.groq_model,
                messages=messages_list,
                tools=tools,
                tool_choice="auto",
                max_tokens=800,
                temperature=0.1,
            )
        except BadRequestError as e:
            err_str = str(e)
            if "tool_use_failed" in err_str or "tool call validation" in err_str:
                if iteration == 0 and not tool_traces:
                    simplified = f"Show me data and analysis for: {message}"
                    messages_list[-1] = {"role": "user", "content": simplified}
                    yield {"type": "retry", "tool_name": "groq",
                           "attempt": 1, "error": "tool_format_error"}
                    try:
                        response = await call_groq_with_retry(
                            client,
                            model=settings.groq_model,
                            messages=messages_list,
                            tools=tools,
                            tool_choice="auto",
                            max_tokens=800,
                            temperature=0.1,
                        )
                    except Exception:
                        emit_audit_log(
                            query_id      = query_id,
                            query_preview = message,
                            user          = user,
                            sources       = sources,
                            tools_used    = [],
                            confidence    = "low",
                            rag_escalated = False,
                            tokens        = total_tokens,
                            duration_s    = round(time.time() - start_time, 2),
                        )
                        yield {
                            "type":             "response",
                            "answer":           "I had trouble processing your question. Please try rephrasing.",
                            "sources":          [],
                            "tools_used":       [],
                            "confidence":       "low",
                            "follow_ups":       [],
                            "query_id":         query_id,
                            "escalation_level": None,
                            "tool_traces":      [],
                        }
                        return
                else:
                    emit_audit_log(
                        query_id      = query_id,
                        query_preview = message,
                        user          = user,
                        sources       = sources,
                        tools_used    = [t.tool_name for t in tool_traces],
                        confidence    = "low",
                        rag_escalated = rag_escalated,
                        tokens        = total_tokens,
                        duration_s    = round(time.time() - start_time, 2),
                    )
                    yield {
                        "type":             "response",
                        "answer":           "I retrieved some data but hit a formatting issue. Please try rephrasing.",
                        "sources":          sorted(sources),
                        "tools_used":       [t.tool_name for t in tool_traces],
                        "confidence":       "low",
                        "follow_ups":       [],
                        "query_id":         query_id,
                        "escalation_level": "medium" if rag_escalated else None,
                        "tool_traces":      [
                            {"tool_name": t.tool_name, "arguments": t.arguments,
                             "result": t.result, "duration_ms": t.duration_ms}
                            for t in tool_traces
                        ],
                    }
                    return
            raise

        total_tokens += response.usage.total_tokens if response.usage else 0
        msg           = response.choices[0].message

        messages_list.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [
                {
                    "id":       tc.id,
                    "type":     "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in (msg.tool_calls or [])
            ] if msg.tool_calls else [],
        })

        if not msg.tool_calls:
            final_answer             = msg.content or ""
            clean_answer, follow_ups = extract_follow_ups(final_answer)
            has_unverified, _        = check_hallucination(clean_answer, tool_traces)
            unverified_claims        = has_unverified
            confidence = compute_confidence(
                tool_results_count, rag_chunks_count,
                False, tool_failed,
                rag_escalated=rag_escalated,
                unverified_claims=unverified_claims,
            )
            logger.info("orchestrator: stream complete",
                        extra={"tokens": total_tokens, "confidence": confidence})

            emit_audit_log(
                query_id      = query_id,
                query_preview = message,
                user          = user,
                sources       = sources,
                tools_used    = list({t.tool_name for t in tool_traces}),
                confidence    = confidence,
                rag_escalated = rag_escalated,
                tokens        = total_tokens,
                duration_s    = round(time.time() - start_time, 2),
            )

            yield {
                "type":             "response",
                "answer":           clean_answer,
                "sources":          sorted(sources),
                "tools_used":       list({t.tool_name for t in tool_traces}),
                "confidence":       confidence,
                "follow_ups":       follow_ups,
                "query_id":         query_id,
                "escalation_level": "medium" if rag_escalated else None,
                "tool_traces":      [
                    {
                        "tool_name":   t.tool_name,
                        "arguments":   t.arguments,
                        "result":      t.result,
                        "duration_ms": t.duration_ms,
                    }
                    for t in tool_traces
                ],
            }
            return

        # Execute tool calls and emit events
        for tool_call in msg.tool_calls:
            tool_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            cache_key = make_cache_key(tool_name, arguments)
            if cache_key in tool_call_cache:
                messages_list.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      json.dumps(tool_call_cache[cache_key], default=str)[:2000],
                })
                yield {
                    "type":            "tool_call",
                    "tool_name":       tool_name,
                    "inputs":          {k: str(v)[:50] for k, v in arguments.items()},
                    "outputs_summary": "served from cache",
                    "latency_ms":      0,
                }
                continue

            start_ms = int(time.time() * 1000)
            result   = await execute_tool(tool_name, arguments)
            duration = int(time.time() * 1000) - start_ms

            if tool_name == "search_documents" and isinstance(result, dict):
                if result.get("escalation_needed") and result.get("next_level"):
                    next_level    = result["next_level"]
                    current_level = result.get("sensitivity_used", "low")
                    yield {
                        "type":       "rag_escalation",
                        "from_level": current_level,
                        "to_level":   next_level,
                    }
                    rag_escalated            = True
                    arguments["sensitivity"] = next_level
                    result = await execute_tool(tool_name, arguments)
                    tool_call_cache[make_cache_key(tool_name, arguments)] = result

                chunks_found = len(result.get("passages", []))
                yield {
                    "type":              "rag_retrieval",
                    "query":             arguments.get("query", ""),
                    "sensitivity_level": arguments.get("sensitivity", "medium"),
                    "chunks_found":      chunks_found,
                }
                rag_chunks_count += chunks_found
                for p in result.get("passages", []):
                    sources.add(f"PDF: {p.get('source', 'document')}")

            else:
                yield {
                    "type":            "tool_call",
                    "tool_name":       tool_name,
                    "inputs":          {k: str(v)[:50] for k, v in arguments.items()},
                    "outputs_summary": f"{len(str(result))} chars",
                    "latency_ms":      duration,
                }

            if tool_name == "query_database":
                sources.add("SQL Database")
            elif tool_name == "analyze_csv_data":
                sources.add("CSV Analytics")

            result_ok = isinstance(result, dict) and "exc" not in result and "error" not in result
            if result_ok:
                tool_results_count += 1
            else:
                tool_failed = True

            tool_call_cache[cache_key] = result
            tool_traces.append(ToolCallTrace(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                duration_ms=duration,
            ))
            messages_list.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      json.dumps(result, default=str)[:2000],
            })

    yield {"type": "cap_hit", "iterations": MAX_ITERATIONS, "partial_answer": True}
    confidence = compute_confidence(
        tool_results_count, rag_chunks_count,
        True, tool_failed, rag_escalated=rag_escalated,
    )
    emit_audit_log(
        query_id      = query_id,
        query_preview = message,
        user          = user,
        sources       = sources,
        tools_used    = list({t.tool_name for t in tool_traces}),
        confidence    = confidence,
        rag_escalated = rag_escalated,
        tokens        = total_tokens,
        duration_s    = round(time.time() - start_time, 2),
    )
    yield {
        "type":             "response",
        "answer":           "I gathered data but reached the processing limit. Please try a more specific question.",
        "sources":          sorted(sources),
        "tools_used":       list({t.tool_name for t in tool_traces}),
        "confidence":       confidence,
        "follow_ups":       [],
        "query_id":         query_id,
        "escalation_level": "medium" if rag_escalated else None,
        "tool_traces":      [
            {"tool_name": t.tool_name, "arguments": t.arguments,
             "result": t.result, "duration_ms": t.duration_ms}
            for t in tool_traces
        ],
    }