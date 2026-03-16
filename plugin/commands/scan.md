---
description: Scan GitHub trending repos and find what's relevant to your current workspace
argument-hint: "[--daily] [--languages=python,typescript]"
allowed-tools: ["Bash", "Read", "Glob", "WebFetch"]
---

# /scan — GitHub Trending Radar

You have been asked to scan GitHub trending repos and qualify them against the user's workspace.

**Pass through the user's arguments** (e.g. `--daily`, `--languages=python,typescript`).

Now execute the `dev-radar` skill at `${CLAUDE_PLUGIN_ROOT}/skills/dev-radar/SKILL.md`.

Follow the skill instructions exactly. The skill handles:
1. Building workspace context
2. Fetching trending repos via the Python script
3. Deep-reading shortlisted repos
4. Creative application analysis
5. Rich presentation

Arguments received: $ARGUMENTS
