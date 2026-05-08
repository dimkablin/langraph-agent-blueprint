"""Conservative parser for user-facing @context references."""

from __future__ import annotations

from langgraph_agent_blueprint.models.context import ContextReference


def parse_context_references(text: str) -> list[ContextReference]:
    """Extract conservative @mentions without treating emails/usernames as files."""

    refs: list[ContextReference] = []
    index = 0
    while index < len(text):
        at = text.find("@", index)
        if at < 0:
            break
        if at > 0 and (text[at - 1].isalnum() or text[at - 1] in {"_", ".", "-"}):
            index = at + 1
            continue
        parsed = _parse_one(text, at)
        if parsed is None:
            index = at + 1
            continue
        ref, end = parsed
        refs.append(ref)
        index = end
    return refs


def _parse_one(text: str, at: int) -> tuple[ContextReference, int] | None:
    rest = text[at + 1 :]
    if not rest:
        return None
    if rest.startswith('"'):
        close = rest.find('"', 1)
        if close <= 1:
            return None
        value = rest[1:close]
        return ContextReference(kind=_infer_path_kind(value), value=value), at + close + 2
    for prefix, kind in [
        ("glob:", "glob"),
        ("notebook:", "notebook"),
        ("url:", "url"),
        ("mcp:", "mcp_resource"),
        ("plugin:", "plugin"),
    ]:
        if rest.startswith(prefix):
            payload = rest[len(prefix) :]
            markdown = _take_markdown_link(payload, at + 1 + len(prefix))
            if markdown is not None:
                value, end = markdown
            else:
                value, end = _take_token(payload, at + 1 + len(prefix))
            value = _strip_markdown_link(value)
            if not value:
                return None
            return ContextReference(kind=kind, value=value), end
    token, end = _take_token(rest, at + 1)
    if not token:
        return None
    if _looks_like_plain_username(token):
        return None
    return ContextReference(kind=_infer_path_kind(token), value=token), end


def _take_token(text: str, absolute_start: int) -> tuple[str, int]:
    stop_chars = set(" \t\r\n")
    end = 0
    while end < len(text) and text[end] not in stop_chars:
        end += 1
    token = text[:end].rstrip(".,;)")
    return token, absolute_start + end


def _strip_markdown_link(value: str) -> str:
    if value.startswith("[") and "](" in value:
        label_end = value.find("]")
        close = value.find(")", label_end)
        if label_end > 0 and close > label_end:
            return value[label_end + 2 : close]
    return value


def _take_markdown_link(text: str, absolute_start: int) -> tuple[str, int] | None:
    if not text.startswith("[") or "](" not in text:
        return None
    label_end = text.find("]")
    close = text.find(")", label_end)
    if label_end <= 0 or close <= label_end + 1:
        return None
    return text[label_end + 2 : close], absolute_start + close + 1


def _infer_path_kind(value: str) -> str:
    normalized = value.replace("\\", "/")
    if normalized.endswith("/"):
        return "directory"
    if normalized.lower().endswith(".ipynb"):
        return "notebook"
    return "file"


def _looks_like_plain_username(token: str) -> bool:
    if any(marker in token for marker in ["/", "\\", "."]):
        return False
    if token.endswith(":"):
        return False
    return token.replace("-", "").replace("_", "").isalnum()
