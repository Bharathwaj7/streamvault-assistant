from typing import Any
from app.tools.base import BaseTool
from app.db.chroma import get_pdf_collection
from app.core.logging import get_logger

logger = get_logger()

SENSITIVITY_LEVELS = ["low", "medium", "high"]


class PDFTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Search internal StreamVault PDF documents for qualitative insights, "
            "strategic context, policies, and narrative explanations. "
            "Use this tool when the question requires context from reports, "
            "such as: why a title is trending, campaign strategies, content roadmap plans, "
            "audience behaviour analysis, policy guidelines, or executive recommendations. "
            "Available documents: quarterly_executive_report, campaign_performance_summary, "
            "content_roadmap, policy_guidelines, audience_behavior_report. "
            "Returns the most relevant text passages with their source document."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type":        "string",
                    "description": "Natural language search query to find relevant document passages.",
                },
                "n_results": {
                    "type":        "integer",
                    "description": "Number of passages to retrieve (default 4, max 8).",
                    "default":     4,
                },
            },
            "required": ["query"],
        }

    async def run(
        self,
        query:       str,
        n_results:   int = 4,
        sensitivity: str = "medium",
    ) -> Any:
        n_results   = min(int(n_results), 8)
        sensitivity = sensitivity if sensitivity in SENSITIVITY_LEVELS else "low"

        logger.info("pdf_tool: searching documents",
                    extra={"query": query, "sensitivity": sensitivity})

        try:
            collection = get_pdf_collection()

            # Determine which sensitivity levels to include
            # low    → only low
            # medium → low + medium
            # high   → low + medium + high
            level_index      = SENSITIVITY_LEVELS.index(sensitivity)
            allowed_levels   = SENSITIVITY_LEVELS[:level_index + 1]

            # Query with sensitivity filter
            if len(allowed_levels) == 1:
                where_filter = {"sensitivity": {"$eq": allowed_levels[0]}}
            else:
                where_filter = {"sensitivity": {"$in": allowed_levels}}

            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            passages = []
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                passages.append({
                    "text":        doc,
                    "source":      meta.get("source", "unknown"),
                    "page":        meta.get("page", "?"),
                    "sensitivity": meta.get("sensitivity", "low"),
                    "relevance":   round(1 - dist, 3),
                })

            logger.info("pdf_tool: found passages",
                        extra={"count": len(passages), "sensitivity": sensitivity})

            # If no results at this level — suggest escalation
            if not passages:
                logger.info(
                    "pdf_tool: no results at sensitivity level, escalation needed",
                    extra={"sensitivity": sensitivity}
                )
                return {
                    "passages":           [],
                    "count":              0,
                    "sensitivity_used":   sensitivity,
                    "escalation_needed":  True,
                    "next_level":         SENSITIVITY_LEVELS[min(
                        level_index + 1, len(SENSITIVITY_LEVELS) - 1
                    )],
                }

            return {
                "passages":          passages,
                "count":             len(passages),
                "sensitivity_used":  sensitivity,
                "escalation_needed": False,
            }

        except Exception as e:
            logger.error("pdf_tool: search error", extra={"exc": str(e)})
            return {"exc": str(e)}