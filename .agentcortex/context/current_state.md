# Project Current State (vNext)

> This is the **Single Source of Truth (SSoT)** — global project state that auto-updates
> via `/ship`. You don't edit this manually; placeholders fill in as you complete work.

- **Project Intent**: Kitsu list provider bridge for AniBridge
- **Project Name**: anibridge-kitsu-provider
- **Core Guardrails**:
  - Correctness first: No claim of completion without evidence.
  - Small & reversible: Prioritize small, reversible changes; avoid unauthorized refactoring.
  - Document-first: Core logic or structural changes require a Spec/ADR first.
  - Handoff gate: Non-`tiny-fix` tasks must produce a traceable handoff summary.
- **System Map**:
  - Global SSoT: `.agentcortex/context/current_state.md`
  - Task Isolation: `.agentcortex/context/work/<worklog-key>.md`
  - Active Work Log Path: derive <worklog-key> from the raw branch name using filesystem-safe normalization before any gate checks.
  - Workflows & Policies: `.agent/workflows/*.md`, `.agent/rules/*.md`
- **Last Updated**: 2026-09-21
- **Last Verified**: 2026-09-21
- **Update Sequence**: 2
- **ADR Index**:
  - docs/adr/ADR-001-project-architecture-and-tech-stack.md
- **Active Backlog**: (none yet)
- **Spec Index** (project specs at `docs/specs/`):
  - docs/specs/kitsu-provider.md [status: shipped] [primary_domain: provider]
- **Canonical Commands**:
  - `/spec-intake`: Import external specs (from other LLMs, documents, or natural language). Handles large product specs via decomposition. Runs before `/bootstrap`.
  - `/bootstrap`: Task initialization & classification freeze.
  - `/plan`: Define target files, steps, risks, and rollback.
  - `/implement`: Execute implementation only when `IMPLEMENTABLE`.
  - `/review`: Check AC alignment & scope creep.
  - `/test`: Report test coverage via Test Skeleton.
  - `/handoff`: Output resumable state summary (mandatory for non-tiny-fix).
  - `/decide`: Record key decisions with reasoning to prevent cross-session re-derivation.
  - `/test-classify`: Auto-select test depth and evidence format based on task classification.
  - `/ship`: Consolidate evidence and update/archive state.
  - `ask-openrouter`: [OPTIONAL] External model delegation. See `.agent/workflows/ask-openrouter.md`.
  - `codex-cli`: [OPTIONAL] Codex CLI delegation. See `.agent/workflows/codex-cli.md`.
  - `claude-cli`: [OPTIONAL] Claude CLI delegation. See `.agent/workflows/claude-cli.md`.
  - `ask-local`: [OPTIONAL] Local-model (OpenAI-compatible endpoint) delegation. See `.agent/workflows/ask-local.md`.
- **References**:
  - `AGENTS.md`
  - `.agent/rules/engineering_guardrails.md`
  - `.agent/rules/state_machine.md`
  - `.agentcortex/docs/CODEX_PLATFORM_GUIDE.md`
  - `.agentcortex/docs/guides/token-governance.md` *(manual-only)*
  - `.agentcortex/docs/guides/context-budget.md` *(manual-only)*

> [!NOTE]
> This file is the Single Source of Truth for global project context only.
> Do not store per-task progress here; write progress to `.agentcortex/context/work/<worklog-key>.md`.

## Global Lessons (AI Error Pattern Registry)
>
> Structured format:
> `- [Category: <tag>][Severity: <HIGH|MEDIUM|LOW>][Trigger: <normalized-trigger>] <lesson>`
>
> `/implement` reviews active HIGH-severity lessons before code changes. `/retro` may append new structured entries via guarded write.

(none yet)

## Ship History

### Ship-main-2026-09-21
- Feature shipped: Implement Kitsu list provider bridge for kitsu.app with anibridge-list-base
- Tests: Pass (70 passed, 94% coverage)
- Commit: 5e9a29cc7aa3f5f8b16b52bbe8b4c6cb4fc6c472
