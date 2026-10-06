# Subagents

Spawn subagents (Agent tool) to isolate context, parallelize independent work, or offload bulk mechanical tasks. Don't spawn when the parent needs the reasoning, when synthesis requires holding things together, or when spawn overhead dominates.

**Avoid sprawl.** Each spawn may surface an approval prompt depending on the permission settings. Batch related work into one subagent rather than fanning out into many.

**Subagent context is fresh.** No parent conversation, no parent tool results. Pack what matters into the prompt string. Project CLAUDE.md is loaded automatically.

**Pack the strategic why, not just the task.** Tell the subagent what the parent is trying to decide, not only what to fetch. A subagent that knows "we're choosing between A and B" can flag a third option or surface that the question itself is wrong. A subagent told only "research A and B" can't. The fresh context cuts both ways: without the strategic frame, the child can't recognize a curveball, can't flag a pivot, can't separate signal from noise mid-research.

**The brief is the entire reality.** A subagent given a research task returns what it was asked to find — data, summaries, lists. It doesn't verify the underlying claims you'll build on unless you ask it to. If the synthesis depends on a specific claim being true (e.g. "none of them shipped feature X"), put that in the brief and ask the subagent to confirm or refute against primary sources (announcement pages, docs, changelogs). Treat absence claims as extraordinary — verify load-bearing claims before drafting, not after pushback. Surface artifacts ≠ underlying reality. Different question, different fetch.

## Routing

Pick the cheapest model that can do the subtask well:

- **Haiku**: bulk mechanical work, no judgment (file renames, csv parsing, log scans, relay steps)
- **Sonnet**: scoped research, code/file exploration, in-scope synthesis, drafting groundwork
- **Opus**: the workhorse for multi-step subtasks that need real reasoning but not final taste
- **Fable**: judgment bottlenecks only (architecture calls, final review, taste). Escalation runs upward too: a cheaper parent spawns ONE Fable subagent for the single judgment-heavy step instead of paying Fable rates end to end.

**Effort rides the tier.** Defaults: Haiku low, Sonnet medium, Opus xhigh, Fable medium — Fable goes xhigh only for the hardest calls (deep architecture, security, cross-file reasoning). Skip high: on normal work, effort is a pure cost lever; it only moves the outcome on the hardest tasks.

**Set `model:` explicitly on EVERY spawn — omitting it inherits the parent's model.** A Fable parent that spawns a doc lookup or mechanical agent without `model:` silently pays Fable rates for Sonnet-tier work. "Inherit" is never a routing decision; it's the absence of one.

## Consult-up pattern (executing a plan)

When an Opus or Sonnet parent runs a multi-step plan, don't settle the judgment-heavy steps alone. For each one (architecture, design tradeoff, final review, taste), spawn ONE Fable child (`model: fable`, xhigh for the hardest) and treat its answer as the ruling on that step. Consulting up IS the escalation — the parent stays cheap, the judgment gets the top tier. The child starts blank (see "Subagent context is fresh" above): pack the full context, the *why*, and the specific decision to make, never just the task.

If a subagent realizes the task needs more reasoning than its tier provides, it should return to the parent rather than burning tokens trying. The parent re-runs that step one tier up.

## Why delegation is the default (economics)

Subscription tokens are far cheaper than API tokens for the same work, and subagents inherit the subscription. Parent context is the scarce resource: spend it on judgment, push mechanics down.

## Long-running audit subagents: verify against current state

Architecture and bug-hunt audits run for minutes against a working-tree snapshot, and the working tree may change underneath them. To stop audits from shipping claims invalidated by concurrent commits:

- **At audit start:** record `git rev-parse HEAD` + `git status --short` in the audit's working notes.
- **Before final delivery:** rerun both. Note any state change.
- **For any finding about a deleted/moved/renamed file:** verify the claim against current HEAD before including it in the report.
- The audit prompt should instruct the subagent to do this — not the parent. Pack it into the brief.

Mandatory for architecture/bug-hunt subagents. Optional for narrower scoped research where staleness doesn't affect the deliverable.

---

Parent owns final output and cross-spawn synthesis. User instructions override.
