# Architecture Decision Records (ADRs)

briefer.news's **decision log** — the *why* behind the project, versioned with the
code. Git history shows *what* changed; these ADRs capture *why* we chose it, so a
future reader (human or Claude) can recover the reasoning without re-deriving it.

ADRs are the **PAST / "why"** layer of the project's context graph. Its siblings
(the *present* and *future* layers) live in Memex and are auto-updated daily:
- **Present** — `Projects/Briefer/Status.md` (pipeline + data snapshot)
- **Future** — `Projects/Briefer/Goals.md` (goals + progress)
- **Spend** — `Projects/Briefer/Spend.md` (daily cost)

ADRs live **here, in the repo** on purpose — they're code-connected and travel with
the commits they explain. (See ADR-0006 for the whole context-graph design.)

## Writing one
1. Copy `0000-template.md` to `NNNN-short-title.md` (next number).
2. Fill in **Context / Decision / Consequences**. Keep it to a screen or less.
3. Reference the commit(s) that implement it.
4. Status: `Proposed` → `Accepted` → later `Superseded by NNNN` / `Deprecated`.
5. ADRs are immutable once Accepted — don't rewrite history; supersede with a new one.

## When to write one
Any decision a future reader would ask "why did we do it this way?" about —
architecture, editorial rules, tooling, cost/ops trade-offs. Not routine bugfixes.

## Index
- [0001](0001-government-primary-sources-only.md) — Government primary sources only
- [0002](0002-claude-code-headless-synth-engine.md) — Claude Code (headless) as the synth engine
- [0003](0003-deploy-from-home-mac-mini.md) — Deploy from the home M4 mini (residential IP)
- [0004](0004-multi-edition-framework.md) — Multi-edition framework (US + China)
- [0005](0005-editorial-self-critique-loop.md) — Editorial self-critique loop
- [0006](0006-memex-context-graph.md) — Adopt ADRs + a Memex context graph
