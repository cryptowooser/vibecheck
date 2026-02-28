# Mistral Vibe Analysis

> Mistral Vibe v2.2.1 — Apache-2.0 licensed CLI coding agent by Mistral AI
> Source: `reference/mistral-vibe/`

## Architecture Overview

```
vibe/
├── cli/
│   ├── entrypoint.py          # CLI entry (argparse, setup, main loop)
│   ├── commands.py             # Slash command registry (/help, /config, /clear, etc.)
│   └── textual_ui/            # TUI layer (Rich + Textual)
├── acp/
│   └── entrypoint.py          # Agent Client Protocol entry (IDE integration)
├── core/
│   ├── agent_loop.py          # Main agent execution loop
│   ├── config.py              # Pydantic Settings + TOML config
│   ├── system_prompt.py       # System prompt assembly
│   ├── trusted_folders.py     # Trust system for project dirs
│   ├── agents/
│   │   ├── manager.py         # Agent discovery + lifecycle
│   │   └── models.py          # Agent config models
│   ├── tools/
│   │   ├── base.py            # BaseTool ABC
│   │   ├── manager.py         # Tool discovery + MCP integration
│   │   ├── mcp.py             # MCP client (HTTP, Streamable-HTTP, Stdio)
│   │   └── builtins/          # 8 built-in tools
│   │       ├── bash.py
│   │       ├── read_file.py
│   │       ├── write_file.py
│   │       ├── search_replace.py
│   │       ├── grep.py
│   │       ├── todo.py
│   │       ├── task.py         # Subagent delegation
│   │       ├── ask_user_question.py
│   │       └── prompts/       # Per-tool prompt fragments
│   ├── skills/
│   │   ├── manager.py         # Skill discovery + filtering
│   │   ├── models.py          # SkillMetadata / SkillInfo
│   │   └── parser.py          # YAML frontmatter parser
│   ├── prompts/
│   │   ├── cli.md             # Default system prompt
│   │   ├── compact.md         # Compact conversation prompt
│   │   ├── explore.md         # Read-only exploration prompt
│   │   ├── project_context.md # Project context template
│   │   └── dangerous_directory.md
│   └── paths/
│       ├── config_paths.py    # .vibe/ local paths
│       └── global_paths.py    # ~/.vibe/ global paths
└── pyproject.toml             # Python 3.12+, uv-managed
```

### Execution Flow

```
User input
  → CLI entrypoint (argparse)
  → VibeConfig.load() (TOML + env)
  → ToolManager (builtins + custom + MCP discovery)
  → SkillManager (skill discovery from 4 paths)
  → AgentManager (built-in + custom agents)
  → get_universal_system_prompt() assembles:
      base prompt (cli.md or custom)
      + commit signature
      + model info
      + OS/platform info
      + tool prompts
      + available skills section
      + available subagents section
      + project context (tree + git status)
      + AGENTS.md content
  → agent_loop.py (conversation loop with Mistral API)
```

---

## Q1: Does It Read AGENTS.md?

**Yes.** Full support.

### Supported Filenames (priority order)

| Filename    | Source |
|-------------|--------|
| `AGENTS.md` | Primary |
| `VIBE.md`   | Alternative |
| `.vibe.md`  | Alternative |

### How It Works

`vibe/core/trusted_folders.py` defines:
```python
AGENTS_MD_FILENAMES = ["AGENTS.md", "VIBE.md", ".vibe.md"]
```

`vibe/core/system_prompt.py:24-33` loads the first match:
```python
def _load_project_doc(workdir: Path, max_bytes: int) -> str:
    if not trusted_folders_manager.is_trusted(workdir):
        return ""
    for name in AGENTS_MD_FILENAMES:
        path = workdir / name
        try:
            return path.read_text("utf-8", errors="ignore")[:max_bytes]
        except (FileNotFoundError, OSError):
            continue
    return ""
```

The content is appended to the system prompt in `get_universal_system_prompt()` (line 460-464):
```python
project_doc = _load_project_doc(Path.cwd(), config.project_context.max_doc_bytes)
if project_doc.strip():
    sections.append(project_doc)
```

### Constraints

- **Trust required**: Directory must be trusted (has `.vibe/` dir, `.agents/` dir, or one of the AGENTS.md files, OR is in `~/.vibe/trusted_folders.toml`)
- **Max size**: `config.project_context.max_doc_bytes` — default **32 KB**
- **Placement**: Raw content appended to end of system prompt (no special parsing)

### Hackathon Implication

Put your project instructions in `AGENTS.md` at the project root. Vibe reads it verbatim into the system prompt. Same file works with Claude Code (which reads it as `CLAUDE.md` equivalent). For cross-tool compatibility, use `AGENTS.md` as the canonical name.

---

## Q2: How to Add Web Fetch via MCP

Vibe has **no built-in web fetch tool**. Its 8 built-in tools are: `bash`, `read_file`, `write_file`, `search_replace`, `grep`, `todo`, `task`, `ask_user_question`.

### Solution: MCP Server

Add to `~/.vibe/config.toml` (or `.vibe/config.toml` in project root):

#### Option A: mcp-server-fetch (stdio — recommended)

```toml
[[mcp_servers]]
name = "fetch"
transport = "stdio"
command = "uvx"
args = ["mcp-server-fetch"]
startup_timeout_sec = 10.0
tool_timeout_sec = 60.0
```

This auto-discovers and exposes the fetch tools as `fetch_fetch` (naming: `{server_name}_{tool_name}`).

Pre-install for faster startup:
```bash
uv tool install mcp-server-fetch
```

#### Option B: Any HTTP-based MCP server

```toml
[[mcp_servers]]
name = "webtools"
transport = "streamable-http"
url = "http://localhost:8000"
headers = { "Authorization" = "Bearer your_token" }
startup_timeout_sec = 15.0
tool_timeout_sec = 120.0
```

#### Auto-approve the fetch tool (optional)

```toml
[tools.fetch_fetch]
permission = "always"
```

### How MCP Integration Works

`vibe/core/tools/manager.py` calls `_integrate_mcp()` at startup:
1. Iterates `config.mcp_servers`
2. For each server, lists available remote tools via the MCP protocol
3. Creates dynamic proxy tool classes (`MCPHttpProxyTool` or `MCPStdioProxyTool`)
4. Registers them with naming pattern `{server_name}_{tool_name}`
5. Tools appear in the tool registry alongside builtins

`vibe/core/tools/mcp.py` implements three transports:
- `http` / `streamable-http` → `streamablehttp_client` from `mcp` SDK
- `stdio` → `stdio_client` with subprocess management + stderr capture

### Other Useful MCP Servers

| Server | Install | Config name | What it adds |
|--------|---------|-------------|-------------|
| `mcp-server-fetch` | `uvx mcp-server-fetch` | `fetch` | Web page fetching |
| `mcp-server-filesystem` | `uvx mcp-server-filesystem` | `fs` | Extended file ops |
| `mcp-server-github` | `uvx mcp-server-github` | `github` | GitHub API |
| `mcp-server-sqlite` | `uvx mcp-server-sqlite` | `sqlite` | SQLite queries |
| `mcp-server-brave-search` | `uvx mcp-server-brave-search` | `search` | Web search |

---

## Q3: Does It Support Skills?

**Yes.** Full skill system following the [Agent Skills specification](https://agentskills.io/specification).

### Skill Structure

Each skill is a directory containing `SKILL.md` with YAML frontmatter:

```
my-skill/
└── SKILL.md
```

```markdown
---
name: my-skill
description: What this skill does and when to use it
license: MIT
compatibility: Python 3.12+
user-invocable: true
allowed-tools:
  - read_file
  - grep
  - bash
---

# Skill Name

Instructions, context, and behavior definitions go here.
The full markdown body is loaded when the skill is invoked.
```

### Skill Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Lowercase, hyphens only (`^[a-z0-9]+(-[a-z0-9]+)*$`), max 64 chars |
| `description` | string | Yes | What it does / when to use it, max 1024 chars |
| `user-invocable` | bool | No | Default `true` — appears as `/skill-name` slash command |
| `allowed-tools` | list | No | Pre-approved tools (experimental) |
| `license` | string | No | License identifier |
| `compatibility` | string | No | Environment requirements |
| `metadata` | dict | No | Arbitrary key-value pairs |

### Skill Discovery Paths (priority order)

1. **Custom paths**: `skill_paths` in `config.toml`
2. **Agent Skills standard**: `.agents/skills/` (project root, trusted only)
3. **Local project**: `.vibe/skills/` (project root, trusted only)
4. **Global**: `~/.vibe/skills/`

First match wins (by name). Higher-priority paths shadow lower ones.

### Skill Filtering

```toml
# Enable only specific skills
enabled_skills = ["code-review", "test-*"]

# Or disable specific ones
disabled_skills = ["experimental-*"]
```

Supports exact names, glob patterns, and regex with `re:` prefix.

### How Skills Work at Runtime

1. `SkillManager` discovers all `SKILL.md` files at startup
2. Skills with `user-invocable: true` appear in slash command autocomplete (`/skill-name`)
3. Available skills are listed in the system prompt under `# Available Skills` with name, description, and path
4. When invoked, the agent reads the full `SKILL.md` content via `read_file` tool
5. The agent follows the skill's instructions

### Example: Creating a Hackathon Skill

```
~/.vibe/skills/hackathon-helper/SKILL.md
```

```markdown
---
name: hackathon-helper
description: Hackathon project scaffolding and submission checklist
user-invocable: true
allowed-tools:
  - bash
  - write_file
  - read_file
---

# Hackathon Helper

When invoked, help the user with:
1. Project scaffolding for the Mistral hackathon
2. Submission checklist verification
3. Demo preparation
```

---

## Comparison: Vibe vs Claude Code

| Capability | Mistral Vibe | Claude Code |
|-----------|-------------|-------------|
| **Project instructions** | `AGENTS.md` / `VIBE.md` / `.vibe.md` | `CLAUDE.md` |
| **Config format** | TOML (`~/.vibe/config.toml`) | JSON (`.claude/settings.json`) |
| **MCP support** | Yes (HTTP, Streamable-HTTP, Stdio) | Yes (similar) |
| **Skills/plugins** | Yes (SKILL.md, Agent Skills spec) | Yes (plugins with skills, hooks, agents) |
| **Custom tools** | Yes (Python BaseTool subclass) | Yes (MCP servers) |
| **Custom agents** | Yes (TOML agent configs) | Yes (plugin agents) |
| **Subagents** | Yes (`task` tool) | Yes (`Task` tool) |
| **Built-in tools** | 8 tools | ~15 tools (Read, Edit, Write, Glob, Grep, Bash, etc.) |
| **Web fetch** | No (add via MCP) | Yes (WebFetch built-in) |
| **Model** | Devstral-2 (default), configurable | Claude family |
| **Session resume** | `--continue` / `--resume` | `--continue` / `--resume` |
| **Trust system** | `trusted_folders.toml` | Permissions per project |
| **IDE integration** | ACP (Agent Client Protocol) | VS Code extension |
| **Package manager** | uv (Python 3.12+) | npm |

---

## Configuration Reference

### File Locations

| Path | Purpose |
|------|---------|
| `~/.vibe/config.toml` | Global config |
| `.vibe/config.toml` | Project-local config (takes precedence) |
| `~/.vibe/.env` | API keys |
| `~/.vibe/agents/` | Custom agent TOML files |
| `~/.vibe/prompts/` | Custom system prompts |
| `~/.vibe/tools/` | Custom tool Python files |
| `~/.vibe/skills/` | Global skills |
| `.vibe/skills/` | Project-local skills |
| `.agents/skills/` | Agent Skills standard path |
| `~/.vibe/trusted_folders.toml` | Trusted directories |
| `~/.vibe/logs/` | Session logs |

### Key Config Options

```toml
# Model selection
active_model = "devstral-2"  # or "devstral-small", "local"

# Behavior
auto_approve = false
auto_compact_threshold = 200_000
system_prompt_id = "cli"  # or custom prompt name
include_commit_signature = true
include_project_context = true

# Project context limits
[project_context]
max_doc_bytes = 32768  # AGENTS.md size limit
max_depth = 3
max_files = 1000
max_chars = 40000

# Tool permissions
[tools.bash]
permission = "always"  # "always" | "ask" | "never"

# Tool filtering
enabled_tools = []   # if set, only these tools are active
disabled_tools = []  # ignored if enabled_tools is set

# MCP servers
[[mcp_servers]]
name = "fetch"
transport = "stdio"
command = "uvx"
args = ["mcp-server-fetch"]

# Skills
skill_paths = []
enabled_skills = []
disabled_skills = []

# Session
[session_logging]
enabled = true

# Providers (custom LLM endpoints)
[[providers]]
name = "custom"
api_base = "http://localhost:8080/v1"
api_key_env_var = ""
backend = "generic"

[[models]]
name = "my-model"
provider = "custom"
alias = "local"
```

### Built-in Agents

| Agent | Behavior |
|-------|----------|
| `default` | Requires approval for all tool executions |
| `plan` | Read-only, auto-approves safe tools (grep, read_file) |
| `accept-edits` | Auto-approves file edits (write_file, search_replace) |
| `auto-approve` | Auto-approves everything |
| `explore` | Subagent for codebase exploration (read-only) |

### Default System Prompt Philosophy

The `cli.md` prompt (`vibe/core/prompts/cli.md`) enforces:
- **Orient → Plan → Execute** workflow
- No noise: no greetings, hedging, or puffery
- Structure first (code, diagrams, tables before prose)
- Read before edit, verify after edit
- Break loops after 2 failed attempts
- Minimal responses (<200 words default)

---

## Quick Start for Hackathon

```bash
# Install
uv tool install mistral-vibe

# Add web fetch MCP
mkdir -p ~/.vibe && cat >> ~/.vibe/config.toml << 'EOF'

[[mcp_servers]]
name = "fetch"
transport = "stdio"
command = "uvx"
args = ["mcp-server-fetch"]

[tools.fetch_fetch]
permission = "always"
EOF

# Create project AGENTS.md (read by both Vibe and other Agent Skills tools)
cat > AGENTS.md << 'EOF'
# Project Instructions

## Overview
[Your hackathon project description]

## Tech Stack
[Languages, frameworks, APIs]

## Conventions
[Code style, naming, structure rules]
EOF

# Run
vibe
```
