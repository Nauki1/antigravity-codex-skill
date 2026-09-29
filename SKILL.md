---
name: codex-loop
description: >-
  Autonomous Dual-Agent collaboration loop between Google Antigravity (Gemini) and OpenAI Codex CLI.
  Orchestrates Codex as the Lead Architect/Reviewer (using the latest reasoning models, e.g. gpt-6.1-sol / o3)
  and Antigravity as the Full-Stack Implementer, operating concurrently within a single unified workspace.
---

# Codex-Loop Dual-Agent Orchestration Skill

`codex-loop` is a continuous, evolvable skill and framework that coordinates **Google Antigravity (Gemini)** and the **OpenAI Codex CLI** inside a single shared repository.

It enforces a **Loosely Coupled, Shared-Workspace** architecture:
- **Lead Architect & Code Reviewer**: OpenAI Codex CLI (powered by `gpt-6.1-sol` with `xhigh` reasoning effort).
- **Full-Stack Implementer & Interactive Partner**: Google Antigravity (Gemini).
- **Shared Constitution**: `AGENTS.md` at workspace root.
- **Persistent Memory**: Session logs and architectural decisions saved under `.agents/sessions/`.

---

## Quick Reference Commands

Inspect current Codex environment and active models:
```bash
python scripts/codex_loop.py info
```

### 1. Step 1: Architectural Planning (Codex Plan)
Invoke Codex in non-interactive execution mode to analyze requirements and generate an architectural blueprint and checklist:
```bash
python scripts/codex_loop.py plan "<TASK_REQUIREMENT>" [--model "gpt-6.1-sol"] [--reasoning xhigh] [--out docs/architecture.md]
```

### 2. Step 2: Implementation (Antigravity Execute)
- Antigravity reads the specifications and checklist generated in Step 1.
- Writes or updates code in `src/` and tests in `tests/`.
- Runs local tests and linters via Antigravity's terminal tools.

### 3. Step 3: Heterogeneous Code Review (Codex Review)
Codex inspects the uncommitted changes in the repository to catch logical flaws, edge-case regressions, or architecture drift:
```bash
python scripts/codex_loop.py review [--model "gpt-6.1-sol"]
```
- Return code `0`: **APPROVED**. Proceed to commit/deliver.
- Return code `2`: **Issues detected**. Proceed to Step 4 (Fix).

### 4. Step 4: Remediation Loop (Antigravity Fix -> Re-review)
- Antigravity analyzes Codex's review output.
- Applies minimal-diff fixes to resolve feedback.
- Re-runs `python scripts/codex_loop.py review` until `APPROVED`.

### 5. Step 5: Session Archival (Sync Context)
Export the key decisions and conversation highlights into the project workspace:
```bash
python scripts/sync_session.py --title "<TASK_NAME>"
```

---

## Safety Guardrails (Preventing Overconfidence)

To prevent either model from hallucinating or damaging existing working systems:
1. **Heterogeneous Red Teaming**: Codex verifies Antigravity's diffs before work is declared complete.
2. **Minimal Blast Radius**: Strictly respect the minimal-diff principle defined in `AGENTS.md`.
3. **Evidence-Based Success**: No task is marked done without actual test logs demonstrating exit code `0`.
4. **Git Safeguard**: Work in dedicated feature branches with clean git worktrees.
