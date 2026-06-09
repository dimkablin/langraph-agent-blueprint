"""Shared prompt and tool-schema wording for workspace-relative paths."""

from __future__ import annotations


_PATH_EXAMPLE_ROOT = "/workspace/docker-selection-smoke/calculator"
_PATH_EXAMPLE_GOOD = "backend/requirements.txt"
_PATH_EXAMPLE_BAD = "calculator/backend/requirements.txt"


PROJECT_RELATIVE_PATH_DESCRIPTION = (
    "Project-relative path from the workspace root. Do not prefix the path with the workspace "
    f"root directory name itself; for example, if the workspace root is {_PATH_EXAMPLE_ROOT}, "
    f"use {_PATH_EXAMPLE_GOOD}, not {_PATH_EXAMPLE_BAD}."
)

PROJECT_RELATIVE_DIRECTORY_DESCRIPTION = (
    "Optional project-relative directory from the workspace root. Do not prefix the path with "
    f"the workspace root directory name itself; for example, use backend, not calculator/backend, "
    f"when the workspace root is {_PATH_EXAMPLE_ROOT}."
)

PROJECT_RELATIVE_CWD_DESCRIPTION = (
    "Optional project-relative working directory from the workspace root. Do not prefix the cwd "
    f"with the workspace root directory name itself; for example, use backend, not calculator/backend, "
    f"when the workspace root is {_PATH_EXAMPLE_ROOT}."
)


def build_path_use_contract(project_root: str) -> str:
    """Return runtime guidance that keeps model tool paths anchored to project_root."""

    return f"""Path-use contract:
- The Project root entry is the authoritative workspace root for file, search, notebook, and shell tools.
- For read_file, write_file, edit_file, glob, grep, notebook tools, and shell cwd, prefer project-relative paths from that workspace root.
- Do not prefix project-relative paths with the workspace root directory name itself.
- Example: if Project root is {_PATH_EXAMPLE_ROOT}, use {_PATH_EXAMPLE_GOOD}, not {_PATH_EXAMPLE_BAD} or {_PATH_EXAMPLE_ROOT}/{_PATH_EXAMPLE_BAD}.
- Current authoritative workspace root: {project_root}
- If a path is uncertain, discover it with glob, grep, or a read-only shell listing before using it."""
