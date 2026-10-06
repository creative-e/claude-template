## Strategic context, about me

Google Docs is a browser-based collaborative document editor, autosaved to Drive and shared by link. We serve knowledge workers in SMBs and enterprises on Google Workspace, education users, and individuals on free Google accounts. The value proposition: frictionless real-time collaboration with zero install, deep Workspace integration, and built-in AI assistance.

See [docs/strategy.md](docs/strategy.md) for the full version.

## Communication and style

- Short and direct rather than lengthy explanations.
- When you notice a recurring friction, a missing workflow, or a better way to organize how we work — say so. Don't wait to be asked.
- No hedging language: "I think maybe" → state it or don't.
- Default to acting. Ask when a question is cheap and useful — before big token spends, irreversible moves, or non-obvious choices between approaches. A short question beats the wrong direction.

<!-- Add more style notes here as patterns emerge. -->

## Quality

- **Never trade quality for tokens.** Don't delegate judgment-heavy work to cheaper models. Don't cut corners to save context.
- **Finish the work.** No half-done implementations, no placeholders left dangling, no "I'll come back to it." If a step is in scope, complete it.
- **Fix, don't describe.** When the fix is within reach, do it. Don't write up a "here's what I found" report as a substitute for solving the problem. Reports are for things you can't solve or shouldn't solve without input.

## Subagents

Bulk mechanical work, scoped research, and parallel investigations should spawn a subagent, not run in the parent. This keeps the parent's context clean and the prompt cache warm.

**Effort + consult-up (plan execution).** Route by tier with effort defaults Haiku low / Sonnet medium / Opus xhigh / Fable medium (xhigh only for the hardest calls); skip high. When a non-Fable parent executes a multi-step plan, spawn a Fable child for each judgment-heavy step (architecture, final review, taste) and treat its answer as the ruling. Delegating always means passing the *why* and context, never just the task — subagents start with a fresh context and do not inherit the parent's. Details: SUBAGENTS.md § Consult-up pattern.

**Pass `model:` explicitly on EVERY Agent spawn — omitting it inherits the parent's model.** A Fable parent that spawns a lookup/mechanical agent without `model:` silently pays Fable rates for Sonnet-tier work. Doc lookups, data pulls, scoped research → `model: sonnet` (or haiku for pure mechanics); "inherit" is never a routing decision. This rule lives here because the failure happens before SUBAGENTS.md gets read.

See [SUBAGENTS.md](SUBAGENTS.md) for the full routing rules. Check it before defaulting to in-parent execution.

## Skills

Project skills live in `.claude/skills/` — that copy is canonical. A PostToolUse hook (see `.claude/settings.json`) runs `tools/sync_skills.py` to mirror them into `.agents/skills/` so other agent runtimes (e.g. Codex) see the same skills. Never edit `.agents/skills/` by hand — it gets clobbered on the next sync. Run `python tools/sync_skills.py` for a manual full sync.

## Preferred Tools

### Data Fetching

1. **WebFetch**: free, text-only, works on public pages that don't block bots.
2. **agent-browser CLI**: free, local Rust CLI + Chrome via CDP. For dynamic pages or auth walls that WebFetch can't handle. Returns the accessibility tree with element refs (`@e1`, `@e2`). ~82% fewer tokens than screenshot-based tools. Install: `npm i -g agent-browser && agent-browser install`. Use `snapshot` for AI-friendly DOM state, element refs for interaction.
3. **Notice recurring fetch patterns and propose wrapping them as dedicated tools.** When the same fetch/parse logic comes up more than once, suggest wrapping it as a named tool (e.g. a skill file or a `.py` script that calls `agent-browser` with the snapshot and extraction steps baked in for that source). Add the entry to `## Dedicated Tools` below and reference it by name on future calls.

### PDF Files

Use `pdftotext`, not the `Read` tool. Use `Read` only when the user directly asks to analyze images or charts inside the document (`Read` loads PDFs as images).

## Dedicated Tools

- **reddit_api_example** — Reddit API utility for fetching top/hot posts from subreddits, or a single post by URL/ID
