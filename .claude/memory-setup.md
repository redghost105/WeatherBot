# Claude Code Memory Setup — Polymarket Project

Persistent memory integration for Polymarket trading bot using claude-mem observation tools and Obsidian vault.

## Obsidian Vault Structure

Store knowledge in `~/Polymarket-Memory/` (Obsidian vault):

```
~/Polymarket-Memory/
├── Architecture/
│   ├── Trading Engine.md
│   ├── Market Scanning.md
│   └── Signal Validation.md
├── Bugs & Fixes/
│   ├── Market Window Bug (Fixed).md
│   └── Signal Deduplication.md
├── Operations/
│   ├── Telegram Commands.md
│   ├── Production Deployment.md
│   └── SSH Configuration.md
├── Performance/
│   ├── Token Optimization.md
│   └── Market Query Latency.md
└── Templates/
    ├── Bug Report.md
    ├── Feature Implementation.md
    └── Performance Analysis.md
```

## Server-Beta Memory API Usage

### Recording Observations (Bug Fixes, Decisions, Features)

```bash
# Log a bug fix
observation_add {
  "content": "Fixed market scanning window bug where system outputs '0 markets in 18-30 hour window'. Root cause: time filter logic used static offsets instead of dynamic today/tomorrow dates. Solution: implemented dynamic date calculation with timezone awareness.",
  "kind": "bugfix",
  "metadata": {
    "title": "Market Scanning Window Bug Fix",
    "component": "market_scanning.py",
    "severity": "medium",
    "status": "deployed"
  }
}

# Log a feature implementation
observation_add {
  "content": "Implemented signal deduplication in trading engine validation pipeline. Deduplication key: (market_id, event_type). Reduces false signals by ~67% (24 signals → 8 trades in test run). Integration point: validate_trades() method.",
  "kind": "feature",
  "metadata": {
    "title": "Signal Deduplication",
    "component": "trading_engine.py",
    "impact": "high",
    "deployment_date": "2026-05-27"
  }
}

# Log an architectural decision
observation_add {
  "content": "Decision: Use Telegram notifications over email for market events. Rationale: (1) Real-time delivery, (2) Interactive commands (/stats, /trades), (3) Lower latency for trading signals. Implementation: telegram_bot.py with polling and blocking invocation pattern.",
  "kind": "decision",
  "metadata": {
    "title": "Telegram Notification Architecture",
    "decision_date": "2026-05-27",
    "alternatives": ["Email", "Slack", "Discord"]
  }
}
```

### Searching Memory

```bash
# Search for past insights
observation_search {
  "query": "market scanning window implementation",
  "limit": 10
}

# Get contextual observations
observation_context {
  "query": "signal deduplication strategy",
  "limit": 5
}
```

### Building Knowledge Corpora

```bash
# Create a searchable corpus for trading engine architecture
build_corpus {
  "name": "trading-engine-architecture",
  "description": "Trading engine design, signal flow, and market validation logic",
  "types": "feature,discovery,refactor",
  "concepts": "signal,market,validation,trading",
  "limit": 100
}

# Query the corpus
prime_corpus { "name": "trading-engine-architecture" }
query_corpus {
  "name": "trading-engine-architecture",
  "question": "How does signal validation work and what are the deduplication rules?"
}
```

## Integration with Claude Code

### Session Initialization

At session start, prime relevant memory corpora:
```bash
prime_corpus { "name": "trading-engine-architecture" }
prime_corpus { "name": "deployment-history" }
```

### During Development

Record insights as you work:
```bash
# Before committing a fix
observation_add {
  "content": "Fixed [component]: [issue]. Root cause: [analysis]. Solution: [implementation].",
  "kind": "bugfix",
  "metadata": { "component": "module_name", "pr": "#123" }
}

# Before starting a refactor
observation_add {
  "content": "Refactoring [component] to [goal]. Current design has [limitation]. New design: [approach].",
  "kind": "refactor",
  "metadata": { "component": "module_name", "impact": "medium" }
}
```

### Knowledge Queries

Use memory during debugging or architecture questions:
```bash
# Find similar past issues
observation_search { "query": "timeout in market scanning" }

# Get implementation patterns
observation_context {
  "query": "how is error handling implemented in market scanning",
  "limit": 3
}
```

## Project-Specific Observations (Initial Load)

Key past decisions and fixes to record:

1. **Signal Deduplication** (May 27, 2026)
   - Problem: 24 signals → many duplicate trades on same market
   - Solution: Deduplication key (market_id, event_type)
   - Result: 24 signals → 8 trades (67% reduction)

2. **Market Scanning Window Bug** (May 27, 2026)
   - Problem: Output "0 markets in 18-30 hour window"
   - Root Cause: Static time offsets instead of dynamic dates
   - Fix: Dynamic today/tomorrow calculation with timezone
   - Status: Deployed to production

3. **Telegram Notifications** (May 27, 2026)
   - Decision: Real-time Telegram over email/Slack
   - Interactive commands: /stats, /trades, /position
   - Polling integration: 5-second market event polling

4. **SSH Configuration** (May 27, 2026)
   - DigitalOcean droplet: 165.227.94.30
   - Key: Ed25519 at ~/.ssh/id_ed25519
   - Use case: Remote deployment and live monitoring

## Command Quick Reference

| Task | Command |
|------|---------|
| Record bug fix | `observation_add { "content": "...", "kind": "bugfix" }` |
| Search memory | `observation_search { "query": "...", "limit": 10 }` |
| Create corpus | `build_corpus { "name": "...", "description": "..." }` |
| Search corpus | `prime_corpus { "name": "..." }` + `query_corpus { "name": "...", "question": "..." }` |
| Show stats | `observation_search { "query": "*" }` |

---

**Next Steps:**
1. Create initial memory observations for past work
2. Set up Obsidian vault with markdown notes
3. Test observation_search and observation_context queries
4. Prime trading-engine-architecture corpus for next session
