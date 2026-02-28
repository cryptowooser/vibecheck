# Using Vibe for vibecheck Development

Setup guide to make Mistral Vibe maximally useful for coding this project.

---

## 1. Superpowers Skills

[obra/superpowers](https://github.com/obra/superpowers) provides structured development workflows: brainstorming, TDD, systematic debugging, planning, code review, etc. The skills use the standard `SKILL.md` format that Vibe supports natively.

**Install for Vibe:**

```bash
# Clone into Vibe's global skills directory
git clone https://github.com/obra/superpowers.git /tmp/superpowers

# Copy skills into Vibe's skill search path
cp -r /tmp/superpowers/skills/* ~/.vibe/skills/

# Or symlink (easier to update)
ln -s /tmp/superpowers/skills/* ~/.vibe/skills/
```

Vibe discovers skills from `~/.vibe/skills/` automatically. Each skill has a `SKILL.md` with YAML frontmatter that Vibe parses on startup.

**Key skills for this project:**

| Skill | When to use |
|-------|-------------|
| `brainstorming` | Before implementing any feature — refine requirements first |
| `writing-plans` | Break features into 2-5 min tasks with specs |
| `test-driven-development` | RED-GREEN-REFACTOR cycle for all code |
| `systematic-debugging` | Root cause investigation before fixing |
| `verification-before-completion` | Evidence-based validation before claiming done |
| `requesting-code-review` | After completing a feature layer |

**Verify skills are loaded:**

```bash
# In Vibe, type /skills or check startup output for discovered skills
vibe
```

---

## 2. Browser Automation (Playwright CLI)

[microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) — token-efficient CLI for browser automation. Vibe invokes it via bash commands instead of MCP, avoiding large tool schemas and verbose accessibility trees in context.

**Installed as a skill** at `~/.vibe/skills/playwright-cli/` — invoke with `/playwright-cli` in Vibe.

```bash
# Verify installation
playwright-cli --version

# Quick test
playwright-cli open https://example.com
playwright-cli snapshot
playwright-cli close
```

**Use for:** Testing the PWA in a real browser, verifying responsive layouts, E2E testing, form filling.

> **Why CLI over MCP?** The Playwright MCP server registers ~20 tools with full schemas in the system prompt and returns verbose accessibility trees. The CLI approach uses bash commands — more token-efficient, and the agent only reads page state when it explicitly runs `playwright-cli snapshot`.

---

## 3. MCP Servers

Configured in `.vibe/config.toml`. Two MCP servers are active:

### Fetch (Web Content → Markdown)

[mcp-server-fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) — official MCP reference server. Fetches URLs and converts to markdown.

```bash
# Ensure uv/uvx is available (already installed for this project)
uvx mcp-server-fetch --help
```

**Use for:** Reading API docs, checking deployment URLs, fetching reference material.

### Tavily (Web Search)

[Tavily MCP](https://mcp.tavily.com) — web search optimized for AI agents. Free tier: 1,000 queries/month. Uses Streamable HTTP transport with API key embedded in the URL.

```bash
# Sign up at tavily.com → get MCP URL with embedded key
# Already configured in ~/.vibe/config.toml (streamable-http transport)
```

**Use for:** Looking up Mistral API docs, finding code examples, researching libraries.

---

## 4. Project Instructions (AGENTS.md)

`AGENTS.md` at the project root is loaded into Vibe's system prompt automatically. It contains:
- Architecture overview
- Tech stack
- Coding standards (Python 3.12+, Pydantic v2, uv)
- Key file locations

Vibe will follow these instructions for all coding tasks in this project.

---

## 5. Quick Start

```bash
# 1. Install skills (one-time) — DONE on EC2
git clone https://github.com/obra/superpowers.git /tmp/superpowers
cp -r /tmp/superpowers/skills/* ~/.vibe/skills/

# 2. Install Playwright CLI + skill — DONE on EC2
npm install -g @playwright/cli@latest
playwright-cli install --skills
cp -r .claude/skills/playwright-cli ~/.vibe/skills/playwright-cli
# Edit ~/.vibe/skills/playwright-cli/SKILL.md: change allowed-tools to Vibe format

# 3. Pre-install MCP server binaries — DONE on EC2
uv tool install mcp-server-fetch

# 4. Set up Brave API key (if using search)
export BRAVE_API_KEY=your_key_here

# 5. Run Vibe in the project
cd ~/vibecheck
vibe

# 6. Verify: check startup output for MCP servers + skills
# 7. Try: /playwright-cli, then "open https://example.com"
# 8. Try: "fetch https://docs.mistral.ai/capabilities/vibe/"
```

---

## 6. Troubleshooting

| Issue | Fix |
|-------|-----|
| Skills not appearing | Check `~/.vibe/skills/` has SKILL.md files, restart Vibe |
| Playwright CLI fails | Run `playwright-cli --version` to verify install, check `~/.cache/ms-playwright/` for browser binaries |
| Tavily search errors | Check MCP URL in `~/.vibe/config.toml`, verify key is valid at tavily.com |
| Fetch times out | Check network, try `uvx mcp-server-fetch` manually |
| AGENTS.md not loaded | Ensure project dir is trusted (`~/.vibe/trusted_folders.toml`) |
