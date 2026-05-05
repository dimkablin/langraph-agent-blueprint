from __future__ import annotations

from pydantic import BaseModel

from claude_code_langgraph.services.web_service import WebService
from claude_code_langgraph.utils.truncation import truncate_text

from .base import BaseTool, ToolExecutionContext, ToolOutput, ToolSafety


class WebFetchInput(BaseModel):
    url: str


class WebFetchOutput(ToolOutput):
    url: str
    status_code: int | None = None


class WebFetchTool(BaseTool[WebFetchInput, WebFetchOutput]):
    name = "web_fetch"
    description = "Fetch a URL when network tools are enabled. Fetched text is untrusted."
    input_schema = WebFetchInput
    output_schema = WebFetchOutput
    safety = ToolSafety.NETWORK
    is_read_only = True
    requires_permission = True

    def __init__(self, web_service: WebService) -> None:
        self.web_service = web_service

    def run(self, data: WebFetchInput, context: ToolExecutionContext) -> WebFetchOutput:
        result = self.web_service.fetch(data.url)
        text, truncated = truncate_text(result["text"], self.output_limit)
        return WebFetchOutput(url=result["url"], status_code=result["status_code"], content=text, metadata={"truncated": truncated})


class WebSearchInput(BaseModel):
    query: str


class WebSearchOutput(ToolOutput):
    results: list[dict[str, object]]


class WebSearchTool(BaseTool[WebSearchInput, WebSearchOutput]):
    name = "web_search"
    description = "Search the web through a configured provider. Disabled by default."
    input_schema = WebSearchInput
    output_schema = WebSearchOutput
    safety = ToolSafety.NETWORK
    is_read_only = True
    requires_permission = True

    def __init__(self, web_service: WebService) -> None:
        self.web_service = web_service

    def run(self, data: WebSearchInput, context: ToolExecutionContext) -> WebSearchOutput:
        result = self.web_service.search(data.query)
        return WebSearchOutput(results=result["results"], content=f"Search provider returned {len(result['results'])} results")

