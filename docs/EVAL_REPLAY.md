# Eval And Replay Harness

Phase 7 adds a deterministic eval/replay layer for the reference runtime. The harness is not a second agent runtime: it loads typed scenarios, creates an isolated workspace/storage fixture, then calls `AssistantGraphRuntime.invoke(...)` and `AssistantGraphRuntime.resume(...)`.

## Architecture

Flow:

```text
EvalScenario
-> EvalRunner
-> AssistantGraphRuntime
-> RuntimeEvents / final state / storage artifacts
-> EvalAssertionEngine
-> EvalReport
```

Core modules:

- `models/evals.py`: Pydantic scenario, expectation, and report models.
- `evals/loader.py`: YAML/JSON scenario loading and validation.
- `evals/runner.py`: temporary workspace/storage setup and real graph execution.
- `evals/assertions.py`: tolerant event/tool/skill/permission/MCP/subagent/context/final-response checks.
- `evals/reporter.py`: redacted JSON and Markdown reports.
- `services/eval_service.py`: small CLI-facing facade.

The harness uses the fake provider by default, disables network access, disables Langfuse, and uses local fixtures for MCP, plugins, and workspaces.

## Scenario Format

Scenarios live in `evals/scenarios/` and can be YAML or JSON.

```yaml
id: read-file-context
description: "@file context should resolve and enter system context."
provider: fake
workspace_fixture: basic_repo
steps:
  - input:
      text: "Summarize @README.md"
    expect:
      events:
        - type: context_fragment_added
          contains:
            kind: file
            title: README.md
      context_fragments:
        - kind: file
          title_contains: README
          trust: trusted_local
      final_response:
        contains:
          - README
```

Each step can include:

- `input.text`: user input sent through the graph.
- `input.approve`: optional approval decision for permission interrupts.
- `input.resume_payload`: optional extra resume payload.
- `expect`: typed expectations for the graph result after the step.

## Expectations

Supported expectation groups:

- `events`: runtime event type, count, and data subset checks.
- `tool_calls`: tool result name/status checks.
- `skills`: skill lifecycle event checks.
- `permissions`: permission required, approved, or rejected checks.
- `mcp_calls`: MCP server/tool/status checks.
- `subagents`: subagent finish/error/timeout checks.
- `context_fragments`: resolved context kind/title/content/trust checks.
- `files`: workspace file existence/content checks.
- `final_response`: contains/not-contains checks.

Assertions intentionally avoid exact full-prose equality. They are designed to catch contract regressions without making deterministic fake-provider wording the only acceptable answer.

## Fixtures

Checked-in fixtures:

- `evals/fixtures/workspaces/basic_repo/`: README, Python files, notebook, and edit fixtures.
- `tests/fixtures/mcp/fake_mcp_server.py`: local stdio MCP server reused by evals.
- `evals/fixtures/plugins/superpowers-minimal/`: minimal Superpowers-style plugin fixture.
- `evals/fixtures/plugins/hook-block/`: declarative hook fixture.

No eval requires a live LLM, external network, real Langfuse keys, or an external MCP server.

## CLI

List scenarios:

```powershell
lg-agent eval list
```

Run one scenario:

```powershell
lg-agent eval run basic-chat
```

Run all scenarios:

```powershell
lg-agent eval run --all
```

Write reports under a custom directory:

```powershell
lg-agent eval run mcp-echo --report-dir test_runs/evals
```

## Reports

Reports are written under `.eval_runs/` by default:

```text
.eval_runs/
  {timestamp}-{scenario-id}-{run-id}/
    report.json
    report.md
    scenario-results/
      {scenario_id}.json
      {scenario_id}.md
```

Reports include pass/fail, failures, event counts, compact tool calls, skills, permissions, MCP calls, subagent events, context fragment metadata, and final response excerpts. Secrets are redacted and long strings are truncated.

## Built-In Scenarios

Current core scenarios:

- `basic-chat`
- `read-file-context`
- `write-permission-reject`
- `edit-file-exact-once`
- `edit-file-ambiguous-rejected`
- `superpowers-brainstorming`
- `mcp-echo`
- `hook-block`
- `subagent-readonly`
- `context-url-disabled`
- `langfuse-disabled-noop`

These scenarios cover graph execution, context resolution, permissions, edit guardrails, plugin skills, hooks, MCP, subagents, and disabled observability.

Phase 8 adds plugin SDK scenarios:

- `plugin-static-command`
- `plugin-skill`
- `plugin-hook-context`
- `plugin-policy`
- `plugin-tool-static`
- `plugin-context-provider`
- `plugin-mcp-config`

They load `examples/plugins/example-plugin` and prove commands, skills, hooks, policies, tools, context providers, and MCP config contributions work without graph-code edits.

## Langfuse

Eval runs do not require Langfuse. The default eval config sets observability to disabled so reports are deterministic and offline.

Future work can add optional Langfuse scoring or trace metadata:

```text
eval_scenario_id
eval_run_id
eval_step_index
```

This should remain optional and must not require real keys in tests.

## Limitations

- Reports are local files, not a long-term dashboard.
- Assertions are scenario-level contract checks, not model quality grading.
- Evals run sequentially.
- The built-in fake provider is deterministic but limited to the current test command grammar.
- Eval reports should not be committed unless intentionally added as documentation artifacts.
