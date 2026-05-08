from app.tools.sql_tool import SQLTool
from app.tools.pdf_tool import PDFTool
from app.tools.csv_tool import CSVTool
from app.tools.base import BaseTool
from functools import lru_cache


@lru_cache()
def get_tool_registry() -> dict[str, BaseTool]:
    return {
        "query_database":   SQLTool(),
        "search_documents": PDFTool(),
        "analyze_csv_data": CSVTool(),
    }


def get_groq_tool_schemas() -> list[dict]:
    return [tool.to_groq_schema() for tool in get_tool_registry().values()]


async def execute_tool(tool_name: str, arguments: dict):
    registry = get_tool_registry()
    tool = registry.get(tool_name)
    if not tool:
        return {"error": f"Tool '{tool_name}' not found."}
    return await tool.run(**arguments)
