# dev-radar

GitHub trending repos, qualified against your workspace.

dev-radar scans GitHub trending on-demand and scores each repo against your local project context — your dependencies, your CLAUDE.md, your active work. Instead of 25 random trending repos, you get 4-6 ranked recommendations with specific, creative insights about how each one connects to what you're actually building.

## Install

```bash
git clone https://github.com/imraan/dev-radar.git ~/.claude/plugins/dev-radar
```

Then enable in Claude Code settings (or it auto-discovers from the plugins directory).

## Usage

```
/dev-radar:scan                          # Weekly trending, all languages
/dev-radar:scan --daily                  # Daily trending
/dev-radar:scan --languages=python,rust  # Filter by language
```

After the scan, ask "tell me more about [repo]" to get a deep-dive with concrete integration plans mapped to your codebase.

## Requirements

- Python 3.8+ (stdlib only — no pip install needed)
- Claude Code
- No API keys required

## How it works

1. **Fetches trending repos** — scrapes github.com/trending (falls back to GitHub Search API)
2. **Reads your workspace** — CLAUDE.md, package.json/requirements.txt, git history, memory
3. **Deep-reads shortlisted repos** — fetches and understands each README
4. **Scores creatively** — consulting-grade analysis of how each repo connects to your work
5. **Presents ranked results** — rich mini-briefings with specific integration ideas

Results are cached for 4 hours. Second scans are instant.

## Architecture

```
scripts/github_trending.py    # Scrapes trending → JSON (stdlib only)
scripts/lib/http.py            # HTTP client with retry
scripts/lib/cache.py           # 4-hour TTL file cache
skills/dev-radar/SKILL.md      # Core intelligence (scoring + presentation)
commands/scan.md               # /scan entry point
```

## License

MIT
