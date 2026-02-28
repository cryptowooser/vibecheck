# Remoting UI: Mobile-to-Agentic-Coding TUI Bridges

> **Last updated:** 2026-02-28

## Overview

This document analyzes open source tools that bridge agentic coding TUIs (Claude Code, Codex CLI, etc.) to mobile devices and remote browsers. The core problem: **controlling a terminal-based AI coding agent from your phone without exposing it to the public internet.**

---

## Table of Contents

- [Architecture #1: Claude-Conduit (Daemon + WebSocket + iOS)](#architecture-1-claude-conduit-daemon--websocket--ios)
- [Architecture #2: Tailscale + FastAPI + Voice Control](#architecture-2-tailscale--fastapi--voice-control)
- [Architecture #3: Flask + PWA + Terminal Emulation](#architecture-3-flask--pwa--terminal-emulation)
- [Architecture #4: WebSocket + MCP + Multi-Environment](#architecture-4-websocket--mcp--multi-environment)
- [Comparative Architecture Table](#comparative-architecture-table)
- [Networking & Tunnel Approaches](#networking--tunnel-approaches)
- [tmux/PTY Management Patterns](#tmuxpty-management-patterns)
- [Key Architectural Insights](#key-architectural-insights)
- [Recommendations](#recommendations)
- [Cross-Device Options Catalog](#cross-device-options-catalog)

---

## Architecture #1: Claude-Conduit (Daemon + WebSocket + iOS)

**Repository:** [A-Somniatore/claude-conduit](https://github.com/A-Somniatore/claude-conduit)
**Stack:** Node.js + Fastify + node-pty + tmux + WebSocket
**Stars:** ⭐ 19 | **License:** MIT

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DAEMON (macOS)                                  │
│                          Port 7860 (Fastify)                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐         ┌────────────────────────────────────┐  │
│  │  Session Discovery      │         │  Tmux Manager                      │  │
│  ├─────────────────────────┤         ├────────────────────────────────────┤  │
│  │ • Watches ~/.claude/    │         │ • Per-session mutex (SessionLock)  │  │
│  │   projects/ JSONL files │         │ • Conflict detection               │  │
│  │ • Chokidar file watcher │         │ • Creates/attaches tmux sessions   │  │
│  │ • 120s periodic rescan  │         │ • Caches tmux state (10s TTL)      │  │
│  │ • 5s debounced save     │         │ • Max 5 concurrent sessions        │  │
│  │ • Extracts: projectPath,│         │ • Session naming: claude-<uuid>    │  │
│  │   lastMessage, timestamp│         │ • Resolves {{claude --resume id}}  │  │
│  └─────────────────────────┘         └────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │                        Terminal Bridge (WebSocket)                       ││
│  ├──────────────────────────────────────────────────────────────────────────┤│
│  │ • node-pty spawns: tmux attach-session -t <name>                        ││
│  │ • PTY → WS: Binary frames, batched every 16ms (~60fps)                  ││
│  │ • WS → PTY: Binary (terminal input), Text-JSON (resize control)         ││
│  │ • Backpressure: 64KB threshold, 1MB output buffer with FIFO eviction    ││
│  │ • Heartbeat: Ping/Pong every 30s, close if 3+ pongs missed             ││
│  │ • Orphan reaper: 60s interval cleanup of dead WS connections            ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  REST API Routes (all require PSK auth except /api/status):                  │
│  ├─ GET  /api/status                    (health check, no auth)              │
│  ├─ GET  /api/sessions                  (list + discovery state)             │
│  ├─ POST /api/sessions/:id/attach       (create attach token + tmux session) │
│  ├─ POST /api/sessions/:id/kill         (SIGTERM then SIGKILL escalation)    │
│  ├─ GET  /api/sessions/stream           (SSE real-time updates)              │
│  ├─ POST /api/sessions/new              (spawn claude in new directory)      │
│  ├─ GET  /api/directories               (list project dirs for new sessions) │
│  └─ WS   /terminal/:sessionId?token=... (WebSocket terminal bridge)          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ HTTP + WebSocket
                                      │ Authorization: Bearer <PSK>
                                      │
                                ┌─────┴──────┐
                                │   iPhone   │
                                │  (Mobile   │
                                │   App)     │
                                └────────────┘
```

### What the Daemon Does

The daemon is a Node.js + Fastify HTTP/WebSocket server running as a **macOS LaunchAgent** service that:

- **Discovers** Claude Code sessions by watching `~/.claude/projects/` JSONL files
- **Manages** persistent tmux sessions (one per discovered/created Claude session)
- **Bridges** PTY I/O from tmux to WebSocket clients (mobile app)
- **Enforces** conflict detection (prevents running Claude twice on same session)
- **Proxies** REST API calls for session management and creation
- **Handles** graceful lifecycle management with SIGTERM→SIGKILL escalation

### WebSocket Terminal Bridging

The terminal bridge is the heart of the mobile experience:

#### Connection Flow

```
Mobile App                 Daemon                          macOS
   │                          │                              │
   ├─ POST /attach ─────────→ │                              │
   │                          ├─ Check conflicts             │
   │                          ├─ Lock session (mutex)        │
   │                          ├─ Verify no Claude running    │
   │                          ├─ Generate attach token       │
   │                          ├─ Return: token + wsUrl       │
   │ ←────── token + wsUrl ──┤                              │
   │                          │                              │
   ├─ WS /terminal?token= ──→ │                              │
   │                          ├─ Validate token (60s TTL)    │
   │                          ├─ Consume token (one-use)     │
   │                          ├─ node-pty spawn tmux attach→ │ tmux session
   │                          │                              │ created
   │  ◄─── terminal frames ─── ┤ ←─ PTY data (batched) ───── │
   │                          │                              │
   │ ─ terminal input (bin) ─→ │ ─ write to PTY ────────────→│
   │ ─ resize (JSON) ────────→ │ ─ resize PTY ──────────────→│
   │                          │                              │
   │ ─ close / error ────────→ │ ─ kill PTY ────────────────→│
   │                          │ ─ cleanup orphans ──────────→│
```

#### Key PTY Features

| Feature | Implementation | Purpose |
|---------|----------------|---------|
| **Name** | `xterm-256color` | Full ANSI color support |
| **Cols/Rows** | 120×40 default (configurable) | Match terminal dimensions |
| **Status Bar** | Disabled (`tmux set-option status off`) | Avoid rendering conflicts |
| **Initial Flush** | 500ms suppress + resize | Clean redraw at phone dimensions |
| **Backpressure** | 64KB threshold, 1MB buffer | Prevent memory leak from fast output |
| **Batching** | ~60fps (16ms intervals) | Efficient frame sending |
| **Heartbeat** | 30s ping/pong, 3 missed pongs → close | Detect stale connections |
| **Orphan Reaper** | 60s interval cleanup | Kill dangling PTYs from crashes |

#### Binary Protocol

- **PTY → WS (binary frames)**: Raw terminal output (stdout/stderr from tmux)
- **WS → PTY (binary frames)**: Terminal input (user keystrokes)
- **WS → PTY (text frames)**: Control messages in JSON:
  ```json
  { "type": "resize", "cols": 100, "rows": 30 }
  ```

### Authentication Model (3 Layers)

#### Layer 1: Pre-Shared Key (PSK) for REST API

```yaml
# Config: ~/.config/claude-conduit/config.yaml
auth:
  psk: "<auto-generated-key>"  # 256-bit random on first run
```

- All REST endpoints (except `/api/status`) require: `Authorization: Bearer <psk>`
- **Timing-safe comparison** to prevent timing attacks
- Configuration file stored with `0o600` permissions (owner read/write only)

#### Layer 2: Attach Tokens for WebSocket

```typescript
class AttachTokens {
  generate(sessionId: string): string  // 192-bit random base64url
  consume(token: string): string | null  // Single-use, 60s TTL
}
```

**Why two-step?** Prevents bypassing session conflict checks by connecting directly to WebSocket.

#### Layer 3: Debug PSK for WebSocket (development only)

Allows debugging WebSocket with `wscat` or curl, but only in debug mode.

### Session Conflict Detection

The daemon enforces **mutual exclusion** via the `SessionLock` (per-session mutex):

```typescript
// Attach validation checks (in order):
1. isConnected(sessionId)        // Bridge has active WS? → SESSION_ATTACHED
2. isClaudeRunning(sessionId)    // pgrep "claude --resume <id>"? → SESSION_CONFLICT
3. activeSessions.length         // Exceed maxSessions (default 5)? → MAX_SESSIONS
4. hasSession(tmuxName)          // Reattach existing tmux? → existed: true
5. createSession(sessionId)      // Create new tmux session
```

### Session Discovery

The daemon scans `~/.claude/projects/` for JSONL files:

```
~/.claude/projects/
  <project-hash>/
    <session-id>.jsonl
```

**Monitoring:**
- **Chokidar watcher** (depth: 2) for real-time `add`/`change`/`unlink` events
- **Debounced notifications** (2s) to coalesce rapid changes
- **Periodic full rescan** (120s) as safety net
- **Session cache** (`~/.config/claude-conduit/session-cache.json`) for fast startup
- **SSE Stream** (`/api/sessions/stream`): Pushes full session list to mobile clients on change

### Configuration

```yaml
# ~/.config/claude-conduit/config.yaml
port: 7860
host: "0.0.0.0"              # 127.0.0.1 for VPN-only security
auth:
  psk: "<auto-generated>"     # 256-bit random base64url
tmux:
  defaultCols: 120
  defaultRows: 40
  scrollbackLines: 10000
claude:
  binary: "claude"
  maxSessions: 5
rateLimit:
  attachPerSession: "1/5s"
  wsHeartbeat: 30
  wsMaxMissedPongs: 3
projectDirs:
  - "~/projects"
```

### Security Posture

| Layer | Mechanism | Notes |
|-------|-----------|-------|
| **Network** | PSK in Authorization header | No TLS in-app, assumes LAN or VPN |
| **Endpoint Auth** | Bearer token (timing-safe) | Prevents timing attacks |
| **Attach Token** | Single-use, 60s TTL, cryptographically random | Prevents direct WS bypass |
| **Session Conflict** | Per-session mutex + pgrep check | Prevents Claude double-run |
| **File Permissions** | `0o600` on config/cache | Owner read/write only |
| **Process Isolation** | node-pty + tmux + user shell | Claude runs in user context |

**For remote access**: Users should tunnel via Tailscale, WireGuard, SSH, or reverse proxy rather than exposing daemon on public IP.

---

## Architecture #2: Tailscale + FastAPI + Voice Control

**Repository:** [nbramia/claude-bridge](https://github.com/nbramia/claude-bridge)
**Stack:** Python (FastAPI) + tmux + Tailscale + iOS Shortcuts

### Architecture Diagram

```
┌─────────────┐
│   iPhone    │
│  (iOS 17+)  │
└──────┬──────┘
       │ Voice dictation
       │ iOS Shortcut
       ▼
┌──────────────────────┐
│  Tailscale VPN       │
│ (End-to-end crypto)  │
└──────┬───────────────┘
       │ wss://your-mac.your-tailnet.ts.net
       ▼
┌──────────────────────────────────────┐
│  Mac (FastAPI Server on :8008)       │
│  ┌────────────────────────────────┐  │
│  │ Routes:                        │  │
│  │ POST /send      (text inject)  │  │
│  │ GET /jobs/{id}/tail (capture)  │  │
│  │ GET /jobs/{id}/live (HTML UI)  │  │
│  │ GET /healthz    (status check) │  │
│  └────────────────────────────────┘  │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  tmux Session "claude"         │  │
│  │  └─ Claude Code CLI running    │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Key Implementation Details

**Message Flow:**
```python
# POST /send endpoint (FastAPI)
def send(req: SendReq):
    req_id = hashlib.sha1((req.text + _now_iso()).encode()).hexdigest()[:12]
    _tmux_send(req.text)        # Send literal text
    _tmux_send("C-m")           # Send Enter key
    time.sleep(2000/1000.0)     # Wait for Claude response
    pane = _tmux_capture(1000)  # Last 1000 lines
    (STATE_DIR / f"{req_id}.txt").write_text(pane)
    return {"id": req_id, "status": "accepted", "preview": pane[-2000:]}
```

**tmux Integration:**
```python
def _tmux_send(keys):
    subprocess.run(["tmux", "send-keys", "-t", TMUX_SESSION, keys],
                   check=True, capture_output=True)

def _tmux_capture(max_lines: int = 1000) -> str:
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", TMUX_SESSION, "-p", "-S", f"-{max_lines}"],
        check=True, capture_output=True, text=True)
    return result.stdout
```

**Setup:**
```bash
mkdir -p ~/.claude-bridge/{logs,state}
openssl rand -hex 32 > ~/.claude-bridge/token.txt
uv venv ~/.venvs/claude-bridge
uv pip install fastapi uvicorn pydantic python-dotenv
launchctl load ~/Library/LaunchAgents/com.user.claude-bridge.plist
tailscale serve --https=443 --bg localhost:8008
```

**Advantages:** ✅ No public internet exposure ✅ Voice-first workflow ✅ Ultra-simple ✅ ~200 lines of code
**Limitations:** ❌ macOS-only ❌ Manual polling ❌ Voice input only ❌ Requires Tailscale

---

## Architecture #3: Flask + PWA + Terminal Emulation

**Repository:** [markbdean01/claude-terminal-bridge](https://github.com/markbdean01/claude-terminal-bridge)
**Stack:** Python (Flask) + tmux + ANSI parser + PWA

### Architecture Diagram

```
┌─────────────────────────────────────┐
│  iPhone / Any Browser               │
│  ┌─────────────────────────────────┐│
│  │ PWA (Offline-capable)           ││
│  │ ┌─────────────────────────────┐ ││
│  │ │ Terminal Output (xterm-like) │ ││
│  │ │ - 256-color ANSI parsing    │ ││
│  │ │ - Smart typing detection    │ ││
│  │ │ - Momentum scrolling        │ ││
│  │ │ - Touch-optimized (14px)    │ ││
│  │ │                             │ ││
│  │ │ └─ Input: [message] [ESC]  │ ││
│  │ └─────────────────────────────┘ ││
│  │ Polling: 500ms (smart pause)    ││
│  └─────────────────────────────────┘│
└──────────┬──────────────────────────┘
           │ HTTP/HTTPS
           │ fetch() → JSON API
           ▼
┌──────────────────────────────────────┐
│  Flask Server (:5000)                │
│  ┌──────────────────────────────────┐│
│  │ /api/terminal/claude/send (POST) ││
│  │   → tmux send-keys -l "text"    ││
│  │   → tmux send-keys C-m          ││
│  │                                  ││
│  │ /api/terminal/claude/output (GET)││
│  │   → tmux capture-pane -p -e     ││
│  │   → Return last 5000 lines      ││
│  │   → Preserve ANSI codes         ││
│  └──────────────────────────────────┘│
│  ┌──────────────────────────────────┐│
│  │ tmux Session (claude-session)    ││
│  │ with 50K history                 ││
│  │ └─ Claude Code CLI running       ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

### Key Implementation Details

**Backend API:**
```python
@claude_terminal_bp.route("/api/terminal/claude/send", methods=["POST"])
def claude_terminal_send():
    data = request.get_json()
    subprocess.run(["tmux", "send-keys", "-t", TMUX_SESSION_NAME, "-l", data["command"]])
    subprocess.run(["tmux", "send-keys", "-t", TMUX_SESSION_NAME, "C-m"])

@claude_terminal_bp.route("/api/terminal/claude/output", methods=["GET"])
def claude_terminal_output():
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", TMUX_SESSION_NAME, "-p", "-e",
         "-S", f"-{TMUX_CAPTURE_LINES}"],
        capture_output=True, text=True)
    return jsonify({"status": "success", "output": result.stdout, "timestamp": time.time()})
```

**Frontend: Typing Detection:**
```javascript
class ClaudeTerminal {
    setupPolling() {
        setInterval(() => {
            if (this.isTyping) {
                this.typingTimer = setTimeout(() => {
                    this.isTyping = false;
                    this.resumePolling();
                }, CONFIG.typingTimeout);  // 1500ms
                return;
            }
            this.pollTerminal();
        }, CONFIG.pollInterval);  // 500ms
    }
}
```

**ANSI Parser:** Full 256-color support (basic 16 + 216-color cube + grayscale ramp).

**PWA Config:**
```json
{
    "name": "Claude Terminal Bridge",
    "short_name": "Claude Terminal",
    "display": "standalone",
    "orientation": "portrait-primary"
}
```

**Advantages:** ✅ Full ANSI terminal emulation ✅ Works on any browser ✅ PWA = offline-capable, installable ✅ Smart typing detection ✅ Touch-optimized
**Limitations:** ❌ 500ms polling can feel sluggish ❌ No persistent WebSocket ❌ Requires network security hardening

---

## Architecture #4: WebSocket + MCP + Multi-Environment

**Repository:** [willjackson/claude-code-bridge](https://github.com/willjackson/claude-code-bridge)
**Stack:** Node.js (TypeScript) + WebSocket + MCP + TLS

### Architecture Diagram

```
┌──────────────────────────┐
│  Local Machine (Host)    │
│  ┌────────────────────┐  │
│  │ Claude Code CLI    │  │
│  │ + MCP Support      │  │
│  └──────────┬─────────┘  │
│             │            │
│  ┌──────────▼─────────┐  │
│  │ Claude Bridge Host │  │
│  │ (:8765)            │  │
│  │ - WebSocket Server │  │
│  │ - TLS support      │  │
│  │ - Token auth       │  │
│  └──────────┬─────────┘  │
└─────────────┼────────────┘
              │ wss://localhost:8765
              │ (persistent connection)
              ▼
┌──────────────────────────┐
│  Remote Machine(s)       │
│  ┌────────────────────┐  │
│  │ Claude Bridge CLI  │  │
│  │ --with-handlers    │  │
│  │ --connect wss://.. │  │
│  │                    │  │
│  │ Exposes:           │  │
│  │ - bridge_read_file │  │
│  │ - bridge_write_file│  │
│  │ - bridge_delete    │  │
│  │ - bridge_list_dir  │  │
│  │ - bridge_delegate  │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

### Key Implementation Details

**WebSocket Transport Layer:**
```typescript
export class WebSocketTransport implements Transport {
    private ws: WebSocket | null = null;
    private messageQueue: BridgeMessage[] = [];

    async connect(config: ConnectionConfig): Promise<void> {
        this.ws = new WebSocket(url, wsOptions);
        this.ws.on('close', (code, reason) => {
            if (!this.intentionalDisconnect && this.shouldReconnect()) {
                this.scheduleReconnect();  // Exponential backoff
            }
        });
        this.ws.on('open', () => {
            this.startHeartbeat();      // 30s interval
            this.flushMessageQueue();   // Deliver queued messages
        });
    }
}
```

**Connection Configuration:**
```typescript
interface ConnectionConfig {
    url?: string;                   // ws:// or wss://
    reconnect?: boolean;
    maxReconnectAttempts?: number;
    auth?: AuthConfig;              // Token, password, or IP-based
    tls?: TLSConfig;               // Certificate paths
}
```

**MCP Tool Handlers (exposed to Claude Code):**
```typescript
bridge_read_file({path: string}) → {content: string}
bridge_write_file({path: string, content: string}) → {success: boolean}
bridge_delete_file({path: string}) → {success: boolean}
bridge_list_directory({path: string}) → {files: string[]}
bridge_delegate_task({task: any}) → {result: any}
```

**Setup:**
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Start host with TLS + token auth
claude-bridge start --cert cert.pem --key key.pem --auth-token mysecret123

# Connect remote client
claude-bridge start --with-handlers --connect wss://HOST_IP:8765 \
  --ca cert.pem --auth-token mysecret123
```

**Advantages:** ✅ Persistent bidirectional WebSocket ✅ Native MCP integration ✅ Multi-machine support ✅ Production-ready TLS + auth ✅ Auto-reconnection + message queuing ✅ Cross-platform
**Limitations:** ❌ Requires Node.js 20+ ❌ More complex setup ❌ Higher-level abstraction (not a terminal bridge)

---

## Comparative Architecture Table

| Feature | Claude-Conduit | FastAPI (nbramia) | Flask PWA (markbdean01) | WebSocket MCP (willjackson) |
|---------|----------------|-------------------|------------------------|------------------------------|
| **Transport** | WebSocket (binary) | HTTP + Tailscale VPN | HTTP polling | Persistent WebSocket |
| **Language** | TypeScript (Node.js) | Python (FastAPI) | Python (Flask) | TypeScript (Node.js) |
| **Mobile UI** | Native iOS (xterm.js WebView) | HTML live view | Full PWA terminal | Browser (via MCP) |
| **Terminal Emulation** | Full (node-pty + xterm.js) | Plain text capture | 256-color ANSI | N/A (delegates to Claude) |
| **Networking** | LAN/VPN (0.0.0.0) | Private (Tailscale) | Standard HTTP/HTTPS | Standard WebSocket |
| **Input Method** | Touch keyboard | Voice (iOS Shortcuts) | Text + touch | Text (Claude Code native) |
| **Latency** | <50ms (WebSocket) | ~1.5s (polling) | ~0.5s (polling) | <100ms (WebSocket) |
| **Auth** | PSK + attach tokens (3-layer) | Bearer token | Flask session | Token + IP + TLS |
| **Offline Support** | None | None | PWA cache | Message queue |
| **Session Discovery** | Auto (watches ~/.claude/) | Manual | Manual | Manual |
| **Multi-device** | Single Mac + N phones | Single Mac | Any browser | 1 host + N remotes |
| **Conflict Detection** | Yes (mutex + pgrep) | No | No | No |
| **Use Case** | Mobile-first session control | Hands-free voice | Mobile-first dev | Cross-environment file ops |

---

## Networking & Tunnel Approaches

### Without Tailscale (Using Your Own Server)

| Method | Setup | Latency | Security | Complexity |
|--------|-------|---------|----------|------------|
| **SSH reverse tunnel** | `ssh -R 8080:localhost:7860 your-server` | Low | SSH encryption | ⭐ Simplest |
| **Cloudflare Tunnel** | `cloudflared tunnel --url localhost:7860` | Low | HTTPS + Cloudflare | ⭐⭐ |
| **Caddy reverse proxy** | On server: `reverse_proxy` + auto HTTPS | Low | HTTPS + basic auth | ⭐⭐ |
| **WireGuard** | Self-hosted VPN on server | Lowest | Full VPN | ⭐⭐⭐ |

#### SSH Reverse Tunnel (Zero-Install Winner)

```bash
# On your dev machine (where Claude Code runs):
ssh -R 8080:localhost:7860 your-server.com

# Phone browser hits:
https://your-server.com:8080
```

Add Caddy on the server for proper HTTPS:

```caddyfile
your-server.com {
    reverse_proxy localhost:8080
}
```

#### Cloudflare Tunnel (No Server Config)

```bash
# Install cloudflared, then:
cloudflared tunnel --url localhost:7860
# Gives you a free *.trycloudflare.com subdomain with HTTPS
```

### With VPN Services

| Method | Setup | Notes |
|--------|-------|-------|
| **Tailscale** | `tailscale serve --https=443 --bg localhost:7860` | Zero-trust, Magic DNS |
| **WireGuard** | Self-hosted VPN, phone connects | Full tunnel, lowest latency |
| **ZeroTier** | Similar to Tailscale, self-hostable | Open source option |

### Key Point

Claude-conduit's PSK auth + attach tokens are already designed for remote access — it listens on `0.0.0.0:7860`. You just need to tunnel that port through your server. No Tailscale required.

---

## tmux/PTY Management Patterns

### Pattern A: node-pty + WebSocket (Claude-Conduit)

```typescript
// Spawn a PTY attached to tmux session
const pty = spawn('tmux', ['attach-session', '-t', sessionName], {
    name: 'xterm-256color',
    cols: 120,
    rows: 40
});

// PTY → WebSocket (batched at ~60fps)
pty.onData(data => ws.send(data, { binary: true }));

// WebSocket → PTY
ws.on('message', (msg, isBinary) => {
    if (isBinary) pty.write(msg);
    else {
        const ctrl = JSON.parse(msg);
        if (ctrl.type === 'resize') pty.resize(ctrl.cols, ctrl.rows);
    }
});
```

**Pros:** Real-time, full terminal fidelity, resize support
**Cons:** Requires node-pty native module

### Pattern B: Direct send-keys + capture-pane (FastAPI / Flask)

```bash
# Send input
tmux send-keys -t claude -l "user message here"
tmux send-keys -t claude C-m   # Enter

# Capture output
tmux capture-pane -t claude -p            # Plain text
tmux capture-pane -t claude -p -e         # Preserve ANSI codes
tmux capture-pane -t claude -p -S -1000   # Last 1000 lines
```

**Pros:** Simple, no special libraries, works with any CLI tool
**Cons:** Polling-based, race conditions on send+capture timing, no resize

### Pattern C: MCP Delegation (WebSocket MCP)

- Remote client receives abstract tasks (`read_file`, `write_file`)
- Executes locally, streams results back via WebSocket
- Higher-level abstraction, not a terminal bridge

---

## Key Architectural Insights

### 1. Polling vs. WebSocket Tradeoff

| | HTTP Polling | WebSocket |
|--|--------------|-----------|
| **Latency** | 500-1500ms (polling interval) | <100ms frame delivery |
| **Overhead** | New HTTP request per poll | Single persistent connection |
| **Complexity** | Simple, stateless | Stateful, needs heartbeat/reconnect |
| **Proxy-friendly** | Yes | Needs upgrade header support |

### 2. Authentication Patterns

| Pattern | Used By | Notes |
|---------|---------|-------|
| Simple Bearer Token | nbramia, willjackson | `Authorization: Bearer <token>` |
| PSK + Attach Token (2-step) | claude-conduit | Prevents direct WS bypass |
| Flask Session Cookie | markbdean01 | Standard web session |
| Token + IP + TLS | willjackson (production) | Defense in depth |

### 3. Mobile Optimization Strategies

- **Voice-first** (nbramia): Minimize typing friction on phone
- **PWA-first** (markbdean01): Offline-capable, installable, no app store
- **Native-ish** (claude-conduit): xterm.js in WebView, real terminal feel
- **Transparent Bridge** (willjackson): Claude Code handles UI natively

### 4. Resilience Patterns

| Pattern | Implementation | Used By |
|---------|----------------|---------|
| **VPN auto-reconnect** | Tailscale mesh networking | nbramia |
| **Message queue** | Buffer offline messages, flush on reconnect | willjackson |
| **Heartbeat monitoring** | Ping/pong, detect dead connections | claude-conduit, willjackson |
| **Exponential backoff** | 1s → 2s → 4s... reconnection delays | willjackson |
| **Orphan reaper** | 60s cleanup of dangling PTYs | claude-conduit |
| **Session cache** | Fast startup from disk cache | claude-conduit |

---

## Recommendations

| If you prioritize... | Choose | Why |
|---------------------|--------|-----|
| **Simplicity** | nbramia (FastAPI) | ~200 lines, single machine |
| **Mobile UX** | claude-conduit | Real-time WebSocket, native feel |
| **Browser UX** | markbdean01 (PWA) | Full terminal emulation, offline |
| **Voice-First** | nbramia (Tailscale) | iOS Shortcuts integration |
| **Real-time Low Latency** | claude-conduit or willjackson | <100ms updates |
| **Multi-Machine** | willjackson (MCP) | 1 host + N remote clients |
| **No Tailscale** | Any + SSH reverse tunnel | One command, zero install |

---

## Cross-Device Options Catalog

Full catalog from [AI-CODING-FOLLOWUPS.md](./AI-CODING-FOLLOWUPS.md):

| Tool | Approach | Cost | OSS Stats |
|------|----------|------|-----------|
| [Amp](https://ampcode.com) | Session persistence across devices built-in | Free tier | Proprietary |
| [CloudCLI / Claude Code UI](https://github.com/siteboon/claudecodeui) | Web/mobile GUI for Claude Code, Cursor CLI & Codex; file explorer, git, chat, session mgmt | Free | ⭐ 6.2k, GPL-3.0 |
| [Claude Conduit](https://github.com/A-Somniatore/claude-conduit) | Mobile remote session manager; daemon + WebSocket to iPhone/iPad | Free | ⭐ 19, MIT |
| [Codex CLI Farm](https://github.com/waskosky/codex-cli-farm) | tmux session manager w/ centralized logging, snapshot/restore | Free | ⭐ 19, MIT |
| [claude-bridge (ssv445)](https://github.com/ssv445/claude-bridge) | tmux + Next.js/xterm.js + Tailscale; desktop/browser/PWA/phone | Free | ⭐ 0, MIT |
| [claude-tmux (cameroncatch)](https://github.com/cameroncatch/claude-tmux) | tmux-native session manager; fzf, live status, Tailscale remote | Free | ⭐ 0, Shell |
| [tmux-agents (super-agent-ai)](https://github.com/super-agent-ai/tmux-agents) | VS Code control plane for 10-50 parallel AI agents; Kanban, auto-pilot | Free | ⭐ 1, MIT |
| [freshell (danshapiro)](https://github.com/danshapiro/freshell) | Browser-based multi-tab terminal; detach/reattach, session search | Free | — |
| [Termius](https://termius.com) | SSH client, sync across devices | Freemium | Proprietary |
| [Tailscale](https://tailscale.com) | VPN mesh, SSH to home servers | Free tier | Proprietary (client OSS) |
| byobu/tmux + SSH | Just connect from anywhere | Free | N/A |

---

*See also: [AI-CODING-FOLLOWUPS.md](./AI-CODING-FOLLOWUPS.md) for the full research tracker.*
