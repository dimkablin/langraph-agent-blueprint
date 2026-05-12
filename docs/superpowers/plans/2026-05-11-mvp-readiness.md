# MVP Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the project from runtime-ready to a clearly releasable MVP against the P0/P1 intent in `docs/MVP_CHECKLIST.md`.

**Architecture:** Keep the existing LangGraph-owned runtime and close the remaining MVP gaps around measurable acceptance, plan-mode UX, safe edit rollback, verification automation, and first-run product flow. Treat P2/P3 Claude Code parity as future work unless it blocks the usable coding-agent loop.

**Tech Stack:** Python 3.11+, LangGraph, Pydantic v2, Typer/Rich CLI, FastAPI optional API, React/Vite frontend, Node test runner, pytest, checked-in eval scenarios.

---

## Current Readiness Snapshot

Formal status in `docs/MVP_CHECKLIST.md`: the checklist is aspirational and all boxes are unchecked, so it is not currently a reliable status tracker.

Verified on 2026-05-11:

- `python -m pytest -q`: passed.
- `npm.cmd --prefix frontend run test:static`: passed.
- `npm.cmd --prefix frontend run test`: passed outside the Windows sandbox after sandbox `spawn EPERM`.
- `npm.cmd --prefix frontend run build`: passed outside the Windows sandbox after sandbox `spawn EPERM`.

Current interpretation:

- Backend/runtime MVP: mostly ready.
- Browser frontend MVP: functional thin client, but needs product-level smoke and packaging checks.
- Full Claude Code parity from `docs/MVP_CHECKLIST.md`: intentionally far beyond MVP.

---

### Task 1: Convert MVP Checklist Into a Status Source

**Files:**
- Modify: `docs/MVP_CHECKLIST.md`
- Modify: `docs/CAPABILITY_STATUS_MATRIX.md`
- Modify: `docs/FINAL_ACCEPTANCE_REPORT.md`

- [ ] **Step 1: Define status vocabulary at the top of `docs/MVP_CHECKLIST.md`**

Add this block after the priority legend:

```markdown
## Status vocabulary

- `[x]` means implemented and covered by automated test, eval, or documented smoke.
- `[~]` means partially implemented or implemented with a documented limitation.
- `[ ]` means not implemented or not accepted for MVP.
- `[defer]` means intentionally outside MVP.

MVP acceptance uses P0 plus the explicit Phase 1 implementation order near the bottom of this document. P1/P2/P3 are not required to call the first MVP releasable.
```

- [ ] **Step 2: Mark P0 items against current evidence**

Update P0 sections using this rule:

```text
[x] for tested runtime behavior in CAPABILITY_STATUS_MATRIX or current tests.
[~] for present but limited behavior, such as plan mode, rewind, web_search, subagent nested approval, snapshots/rollback.
[defer] for non-MVP parity items.
```

- [ ] **Step 3: Add an MVP summary table to `docs/CAPABILITY_STATUS_MATRIX.md`**

Add a section with these rows:

```markdown
## MVP Summary

| Area | MVP status | Evidence | Remaining gap |
| --- | --- | --- | --- |
| Graph agent loop | ready | pytest, runtime smoke | stronger real-provider task eval |
| CLI/headless | ready | `/help`, `/status`, `query`, stream-json | session list/rename/delete polish |
| Core tools | ready | file/search/shell/todo/notebook tests | richer diff/rollback UX |
| Permissions | ready | permission tests and approval contract | protected-path coverage review |
| Session persistence | ready | resume/export/todo/memory tests | branch/checkpoint UX |
| Plan mode | partial | permission-mode state exists | user-facing `/plan` and approval flow |
| Verification loop | partial | shell tools can run tests | automatic inference/retry loop |
| Frontend thin client | partial-ready | static/unit/build tests | full API plus browser smoke |
```

- [ ] **Step 4: Run documentation validation**

Run:

```powershell
rg -n "\[~\]|\[defer\]|MVP Summary" docs\MVP_CHECKLIST.md docs\CAPABILITY_STATUS_MATRIX.md
```

Expected: the new status markers and summary table are visible.

- [ ] **Step 5: Commit**

```powershell
git add docs\MVP_CHECKLIST.md docs\CAPABILITY_STATUS_MATRIX.md docs\FINAL_ACCEPTANCE_REPORT.md
git commit -m "docs: mark MVP readiness status"
```

### Task 2: Add a Single MVP Verification Command

**Files:**
- Create: `scripts/verify_mvp.ps1`
- Modify: `README.md`

- [ ] **Step 1: Create `scripts/verify_mvp.ps1`**

```powershell
param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"

Write-Host "== Python tests =="
python -m pytest -q

Write-Host "== Frontend static tests =="
npm.cmd --prefix frontend run test:static

Write-Host "== Frontend unit tests =="
npm.cmd --prefix frontend run test

if (-not $SkipFrontendBuild) {
    Write-Host "== Frontend production build =="
    npm.cmd --prefix frontend run build
}

Write-Host "== Eval scenarios =="
lg-agent eval run --all
```

- [ ] **Step 2: Document sandbox caveat in `README.md`**

Add under `## Tests`:

```markdown
For MVP acceptance on Windows, use:

```powershell
.\scripts\verify_mvp.ps1
```

If Node or Vite fails inside a restricted sandbox with `spawn EPERM`, rerun the same command outside that sandbox. This is an environment restriction, not an application failure, when the unrestricted command passes.
```

- [ ] **Step 3: Run the script**

Run:

```powershell
.\scripts\verify_mvp.ps1
```

Expected: pytest, frontend static tests, frontend unit tests, frontend build, and eval scenarios pass.

- [ ] **Step 4: Commit**

```powershell
git add scripts\verify_mvp.ps1 README.md
git commit -m "test: add MVP verification script"
```

### Task 3: Make Plan Mode User-Facing

**Files:**
- Modify: `src/langgraph_agent_blueprint/commands/builtin.py`
- Modify: `src/langgraph_agent_blueprint/commands/registry.py`
- Modify: `src/langgraph_agent_blueprint/graph/nodes/command_router.py`
- Modify: `src/langgraph_agent_blueprint/graph/state.py`
- Test: `tests/test_command_router.py`
- Test: `tests/test_permission_service_metadata_driven.py`

- [ ] **Step 1: Add `/plan` command metadata and handler**

In `commands/builtin.py`, add:

```python
def _plan(args: str, state: dict[str, Any]) -> CommandResult:
    if args.strip() in {"off", "exit", "disable"}:
        return CommandResult(True, "Plan mode disabled.", metadata={"plan_mode": {"enabled": False, "approved": False}})
    return CommandResult(True, "Plan mode enabled. Side-effecting tools require approval.", metadata={"plan_mode": {"enabled": True, "approved": False}})
```

Register it before unsupported commands:

```python
Command("plan", "Enable or disable plan mode", "session", _plan),
```

- [ ] **Step 2: Ensure command metadata mutates graph state**

In `graph/nodes/command_router.py`, merge `metadata["plan_mode"]` into state when present.

- [ ] **Step 3: Remove `/plan` from unsupported assumptions**

In `commands/registry.py`, keep unsupported commands limited to:

```python
unsupported = {"rewind", "branch", "rename", "tag"}
```

- [ ] **Step 4: Add tests**

Add tests asserting:

```python
def test_plan_command_enables_plan_mode(runtime):
    result = runtime.invoke("/plan")
    assert result["plan_mode"]["enabled"] is True

def test_plan_mode_blocks_write_without_approval(permission_service, write_tool_metadata):
    state = {"plan_mode": {"enabled": True, "approved": False}}
    check = permission_service.check(write_tool_metadata, state)
    assert check.decision == "ask"
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests\test_command_router.py tests\test_permission_service_metadata_driven.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src\langgraph_agent_blueprint\commands src\langgraph_agent_blueprint\graph tests
git commit -m "feat: expose plan mode command"
```

### Task 4: Close Safe Edit Rollback and Rewind MVP Gap

**Files:**
- Modify: `src/langgraph_agent_blueprint/services/file_service.py`
- Modify: `src/langgraph_agent_blueprint/storage/session_storage.py`
- Modify: `src/langgraph_agent_blueprint/commands/builtin.py`
- Modify: `src/langgraph_agent_blueprint/commands/registry.py`
- Test: `tests/test_file_tools.py`
- Test: `tests/test_session_storage.py`
- Test: `tests/test_command_router.py`

- [ ] **Step 1: Persist file snapshots before write/edit**

Add a `snapshot_file(path: Path, content: str) -> dict[str, str]` helper that records path, sha256, timestamp, and content location under the session storage area.

- [ ] **Step 2: Wire snapshots into `write_text` and `edit_text`**

Before writing, store the previous content if the target exists. Return the snapshot id in tool output metadata.

- [ ] **Step 3: Implement `/rewind` for message state and file snapshots**

Replace `_not_implemented("rewind")` with a real command that accepts:

```text
/rewind last
/rewind messages 3
```

For MVP, support message rewind first and document file restore as available from stored snapshots if automatic file restore is not accepted.

- [ ] **Step 4: Add tests**

Assert:

```python
def test_edit_creates_snapshot_before_mutation(...):
    ...
    assert snapshot["content"] == "old value"

def test_rewind_removes_last_assistant_message(...):
    ...
    assert len(messages_after) == len(messages_before) - 1
```

- [ ] **Step 5: Run tests**

```powershell
python -m pytest tests\test_file_tools.py tests\test_session_storage.py tests\test_command_router.py -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src\langgraph_agent_blueprint tests
git commit -m "feat: add edit snapshots and rewind baseline"
```

### Task 5: Add Verification Loop Acceptance

**Files:**
- Modify: `src/langgraph_agent_blueprint/services/diagnostics_service.py`
- Create: `src/langgraph_agent_blueprint/services/verification_service.py`
- Create: `src/langgraph_agent_blueprint/commands/verify.py`
- Modify: `src/langgraph_agent_blueprint/commands/builtin.py`
- Test: `tests/test_command_router.py`
- Test: `tests/test_graph_smoke.py`

- [ ] **Step 1: Implement project command inference**

Create `VerificationService.infer_commands(project_root)` returning:

```python
{
    "python_tests": "python -m pytest -q" if pyproject exists,
    "frontend_static": "npm.cmd --prefix frontend run test:static" if frontend/package.json has script,
    "frontend_tests": "npm.cmd --prefix frontend run test" if frontend/package.json has script,
    "frontend_build": "npm.cmd --prefix frontend run build" if frontend/package.json has script,
}
```

- [ ] **Step 2: Expose `/verify`**

Add `/verify` as a command that reports inferred commands and runs only safe read-only diagnostics by default. For command execution, require explicit user approval through shell tool flow.

- [ ] **Step 3: Add acceptance eval**

Create an eval scenario that asks the fake provider to call `/verify` and asserts that inferred pytest/npm commands are reported.

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests\test_command_router.py tests\test_graph_smoke.py -q
lg-agent eval run --all
```

Expected: tests pass and eval scenarios pass.

- [ ] **Step 5: Commit**

```powershell
git add src\langgraph_agent_blueprint tests evals
git commit -m "feat: add verification command baseline"
```

### Task 6: Decide Web Search MVP Contract

**Files:**
- Modify: `docs/MVP_CHECKLIST.md`
- Modify: `docs/TOOLS.md`
- Modify: `src/langgraph_agent_blueprint/services/web_service.py`
- Test: `tests/test_web_tools.py`

- [ ] **Step 1: Choose the MVP behavior**

Use this decision:

```text
MVP does not require a live search provider.
MVP requires explicit unavailable status when no provider is configured.
```

- [ ] **Step 2: Mark `WebSearch` as partial in `docs/MVP_CHECKLIST.md`**

Set WebSearch to `[~]` with this note:

```markdown
Implemented as a tool and honest disabled state; live provider integration is post-MVP unless a provider is configured.
```

- [ ] **Step 3: Keep tests strict**

Ensure `tests/test_web_tools.py` asserts:

```python
assert "Web search provider is not configured" in result.content
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests\test_web_tools.py -q
```

Expected: web search unavailable path passes and does not return empty success.

- [ ] **Step 5: Commit**

```powershell
git add docs\MVP_CHECKLIST.md docs\TOOLS.md src\langgraph_agent_blueprint\services\web_service.py tests\test_web_tools.py
git commit -m "docs: define web search MVP contract"
```

### Task 7: First-Run Product Smoke

**Files:**
- Create: `tests/test_cli_mvp_smoke.py`
- Create: `frontend/tests/api-contract-smoke.test.ts`
- Modify: `README.md`

- [ ] **Step 1: Add CLI smoke test**

Test:

```python
def test_cli_status_smoke(cli_runner, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    result = cli_runner.invoke(app, ["query", "/status"])
    assert result.exit_code == 0
    assert "provider/model" in result.output
```

- [ ] **Step 2: Add frontend API contract smoke**

Test that required endpoints are referenced by the frontend client:

```typescript
assert.match(source, /\/chat\/stream/);
assert.match(source, /\/approval/);
assert.match(source, /\/sessions/);
assert.match(source, /\/commands/);
assert.match(source, /\/tools/);
```

- [ ] **Step 3: Update README MVP run path**

Add a short path:

```markdown
1. Set `LLM_PROVIDER=fake`.
2. Run `lg-agent query "/status"`.
3. Run `lg-agent serve --factory --host 127.0.0.1 --port 8000`.
4. Run `npm.cmd --prefix frontend run dev`.
```

- [ ] **Step 4: Run tests**

```powershell
python -m pytest tests\test_cli_mvp_smoke.py -q
npm.cmd --prefix frontend run test
```

Expected: CLI and frontend contract smoke pass.

- [ ] **Step 5: Commit**

```powershell
git add tests\test_cli_mvp_smoke.py frontend\tests\api-contract-smoke.test.ts README.md
git commit -m "test: add first-run MVP smoke coverage"
```

### Task 8: Freeze MVP Scope and Defer Non-MVP Parity

**Files:**
- Modify: `docs/REFERENCE_DELTA_ROADMAP.md`
- Modify: `docs/MVP_CHECKLIST.md`
- Modify: `README.md`

- [ ] **Step 1: Add explicit MVP boundary**

State that these are post-MVP:

```markdown
- Parallel/background subagents and nested approval resume.
- MCP HTTP/OAuth/server mode and automatic marketplace discovery.
- Plugin marketplace install/update polish.
- IDE/LSP integration.
- Cloud/Slack/mobile/remote sessions.
- Enterprise managed policy, auto classifier, and audit exports.
```

- [ ] **Step 2: Add release criteria**

Add:

```markdown
MVP release criteria:

- Core runtime tests pass.
- Frontend static/unit/build pass.
- Eval scenarios pass.
- One fake-provider CLI smoke passes.
- One real-provider read-file smoke is documented or intentionally skipped with reason.
- README has a working first-run path.
```

- [ ] **Step 3: Run final verification**

```powershell
.\scripts\verify_mvp.ps1
```

Expected: full MVP verification passes.

- [ ] **Step 4: Commit**

```powershell
git add docs\REFERENCE_DELTA_ROADMAP.md docs\MVP_CHECKLIST.md README.md
git commit -m "docs: freeze MVP scope"
```

---

## Execution Order

1. Task 1: make readiness measurable.
2. Task 2: add one repeatable MVP verification command.
3. Task 3: expose plan mode because it is central to safe agent behavior.
4. Task 4: close safe edit snapshots/rewind.
5. Task 5: add verification loop acceptance.
6. Task 6: define web search as partial or configured-provider-only.
7. Task 7: cover first-run product smoke.
8. Task 8: freeze scope and defer non-MVP parity.

## Stop Criteria

The project can be called MVP-ready when:

- `.\scripts\verify_mvp.ps1` passes in a normal Windows shell.
- `docs/MVP_CHECKLIST.md` has every required P0 item marked `[x]` or `[~]` with an explicit limitation.
- P2/P3 features are marked as deferred, not silently missing.
- README describes a first-run path that a fresh developer can execute.
