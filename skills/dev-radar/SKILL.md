---
name: dev-radar
description: This skill should be used when the user wants to discover trending GitHub repositories and understand how they connect to their current projects. Relevant when the user asks about trending repos, what's new on GitHub, interesting open source tools, developer news, tech radar, new libraries or frameworks worth knowing about, what tools are gaining traction, or what's hot in open source.
user-invocable: false
---

# Dev Radar — GitHub Trending, Qualified Against Your World

Scan GitHub trending repos and score each one against the user's workspace,
projects, and trajectory. Present creative, consulting-grade recommendations —
not surface-level pattern matching.

---

## Step 1 — Build a picture of the user's world

Read as many of these as exist (skip what's missing, don't error):

1. **CLAUDE.md** in the current directory (and any `@import`-ed files) — reveals
   project goals, architecture decisions, connected services, broader context.
2. **Dependency files** — `package.json`, `requirements.txt`, `pyproject.toml`,
   `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`.
   Use `Glob` to find them: `{package.json,requirements.txt,pyproject.toml,Cargo.toml,go.mod,Gemfile,pom.xml,build.gradle}`
3. **Memory index** — `~/.claude/projects/*/memory/MEMORY.md` (if it exists).
   This is gold: active projects, businesses, clients, interests across ALL work.
4. **Recent git activity** — run `git log --oneline -10` to see what's actively changing.

Build a mental model of:
- What they build
- Who they build for
- What tools and languages they use
- What domains they work in
- What trajectory they're on (what are they growing toward?)

**Do NOT display this context to the user.** Just internalize it for scoring.

---

## Step 2 — Fetch trending repos

Run the scraper. Resolve the script path using `CLAUDE_PLUGIN_ROOT` if set,
otherwise fall back to the path relative to this skill file (`../../scripts/github_trending.py`):

```bash
SCRIPT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}/scripts/github_trending.py"
python3 "$SCRIPT" --since=weekly
```

If the user passed `--daily`, use `--since=daily`.
If the user passed `--monthly`, use `--since=monthly`.
If the user passed `--languages=X`, add `--languages=X`.
If the user passed `--no-cache`, add `--no-cache`.

Use a Bash timeout of 60000 ms (1 minute).

Parse the JSON output. Expect ~15-25 repos with name, description, language,
stars, and velocity (stars_today).

---

## Step 3 — First-pass triage

From the ~25 repos, pick the top ~8-10 that MIGHT have creative applications
for this user. Don't be too literal:
- A data pipeline tool might matter to a marketer
- An automation framework might matter to a fitness coach's CTO
- A new UI library might solve a dashboard problem in a property data project

Cast a wide net. Keep anything that sparks a "hmm, maybe..." thought.
Drop obvious irrelevance (e.g., a Minecraft mod for someone building SaaS).

---

## Step 4 — Deep-read shortlisted repos

For each of the ~8-10 shortlisted repos, use the WebFetch tool to fetch their README:

```
https://raw.githubusercontent.com/{owner}/{repo}/main/README.md
```

If `main` 404s, try `master`. If both fail, skip that repo.

Actually READ and understand each repo. Not just the tagline — the features,
use cases, architecture, the problem it solves. This step is what makes the
plugin valuable.

---

## Step 5 — Creative application analysis

For each shortlisted repo, think CREATIVELY about how it could apply to the
user's world. This is consulting-level insight, not pattern matching.

```
BAD (literal, lazy):
"You use PostgreSQL, so this PostgreSQL tool could be useful."

GOOD (creative, insightful):
"This repo implements real-time data sync between edge functions and a central DB.
Your dashboard currently does full page refreshes to get updated data — you could
use this pattern to make the dashboard feel instant, with records updating live as
your scraper finds new entries. The edge function approach also means you'd reduce
load on the main DB."

BAD (surface-level):
"This automation tool could help your workflows."

GOOD (specific application):
"This is a visual workflow builder with API connectors. Right now your content
pipeline is a linear script chain. If you wrapped each step as a node in this
framework, your client could see the pipeline visually, retry failed steps
themselves, and you could add a 'review before publishing' step without writing
new code. When you onboard your next client, you'd clone the workflow instead
of rebuilding the automation."
```

The insight should answer: **"What specifically could the user BUILD or CHANGE
using this? How does it connect to problems they're actually facing?"**

Think about non-obvious applications:
- A data analysis tool trending among data scientists → could it help a
  marketing startup analyze campaign performance?
- A new testing framework → could it solve flaky tests mentioned in CLAUDE.md?
- An AI agent framework → could it replace custom automation built manually?

**Drop anything where you can't come up with a genuinely useful application.**
Better to show 4 brilliant recs than 8 mediocre ones.

---

## Step 6 — Present rich recommendations

Format each recommendation as a mini-briefing:

```markdown
## Dev Radar — {today's date}

---

### {emoji} {owner/repo} · {stars_today} stars today

**What it is**: {2-3 sentences — what the repo actually does, based on the
README you read, not just the tagline}

**Why this matters to you**: {3-5 sentences — the creative, specific application.
Reference the user's actual projects, tools, clients, or trajectory. Explain
what they could BUILD or CHANGE. Be concrete — name their files, their services,
their workflows.}

**How you'd use it**: {1-2 sentences — the first concrete step to try it}

---
```

Use these emojis for variety: 🔥 📡 🧪 ⚡ 🛠️ 🧠 🎯 🚀

End with a summary line and invitation:

```markdown
---
{N} repos scanned → {N} deep-read → {N} recommended

"Tell me more about [repo]" → I'll cross-reference their code with yours
and show specific integration points.
```

---

## Step 7 — Deep-dive flow (when user says "tell me more about X")

When the user asks to go deeper on a specific repo:

1. **Re-read the README** if needed (it may have been compacted).
2. **Read the repo's key source files** via WebFetch on GitHub — look at
   `src/`, `lib/`, the main entry point to understand actual implementation.
3. **Read the user's LOCAL files** that are relevant to the integration
   (e.g., if suggesting a Supabase tool, read their edge functions).
4. **Produce a concrete integration plan**:
   - What files in the user's project would change
   - What the before/after looks like (conceptual, not full code)
   - Estimated effort (30-minute install or 2-day refactor?)
   - Risks and gotchas
   - Whether it replaces something existing or adds new capability

---

## Edge cases

- **No CLAUDE.md, no deps**: Still works. Use git log and directory structure.
  Recommendations will be less personalized but still insightful about the repos.
- **Empty directory**: Show the top trending repos with general insights about
  each — what kind of developer would benefit and why.
- **Cache hit**: The Python script handles caching (4h TTL). Second runs are instant.
- **Scrape failure**: The script automatically falls back to GitHub Search API.
  You'll see `"source": "api_fallback"` in the JSON.
