<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **WeatherBot** (3756 symbols, 5797 relationships, 177 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/WeatherBot/context` | Codebase overview, check index freshness |
| `gitnexus://repo/WeatherBot/clusters` | All functional areas |
| `gitnexus://repo/WeatherBot/processes` | All execution flows |
| `gitnexus://repo/WeatherBot/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

---

# Token Optimization (Caveman Style)

## Output Strategy: Terse & Direct
- **No fluff.** Skip intro sentences, explanations, context. Jump to the answer.
- **One-liners where possible.** Commands, results, next steps. No elaboration.
- **Code first.** Show the fix, then explain *only* if non-obvious.
- **Abbreviate.** Use short forms: `fn` → function, `msg` → message, `init` → initialize.
- **Lists over prose.** Use bullets, tables, code blocks. No long paragraphs.
- **No pleasantries.** No "Here's what I did...", "Let me...", "I'll help you...". Just do it.
- **Result first.** Error? Show it. Success? Show proof. Then context if needed.

## Command Output Filtering
Use `./.claude/compress-output.sh` or manual filters in Bash commands:

**Automatic compression** (after piping):
```bash
command | ./.claude/compress-output.sh test   # pytest output: failures only
command | ./.claude/compress-output.sh git    # git: changed files only
command | ./.claude/compress-output.sh npm    # npm: errors + status
command | ./.claude/compress-output.sh cargo  # cargo: warnings/errors + summary
command | ./.claude/compress-output.sh logs   # logs: errors + exceptions
```

**Manual filtering** (inline):
- Test output: `pytest -q --tb=line` or `pytest --tb=short`
- Git: `git log --oneline` or `git diff --stat`
- Logs: `grep -E "error|fail|exception"`
- Build: `2>&1 | grep -E "error|warn|failed"`

**Future**: Install `rtk` for ~60-98% automatic compression:
```bash
cargo install rtk  # Requires system permission resolution
```

## When Editing Code
Always consider impact. Use GitNexus:
1. `gitnexus_impact({target: "symbolName", direction: "upstream"})` — who calls this?
2. `gitnexus_detect_changes()` — before committing, what changed?
3. If HIGH/CRITICAL: pause and report with full context

## Memory & Observations
Track insights via claude-mem tools (available in server-beta):
- Root causes for bugs discovered and fixed
- Architecture decisions and tradeoffs  
- Integration points and API contracts
- Performance characteristics and bottlenecks
