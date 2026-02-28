<script>
  import { onDestroy, onMount } from 'svelte'

  const searchParams = new URLSearchParams(window.location.search)
  const debugQuery = (searchParams.get('debug') || '').toLowerCase()
  const debugEnabled = ['1', 'true', 'yes', 'on'].includes(debugQuery)

  const initialSid =
    searchParams.get('sid') ||
    searchParams.get('session_id') ||
    localStorage.getItem('vibecheck_sid') ||
    ''
  const initialPsk = searchParams.get('psk') || localStorage.getItem('vibecheck_psk') || ''

  let psk = initialPsk
  let sessionId = initialSid
  let connectionState = 'Disconnected'
  let stateLabel = 'unknown'
  let attachMode = 'unknown'
  let controllable = false
  let pendingApproval = null
  let pendingInput = null
  let sessions = []
  let logs = []
  let answerText = ''
  let messageText = ''
  let ws = null
  let lastWsError = ''
  let wsOpen = false
  let refreshTimer = null

  const hostBase = `${window.location.protocol}//${window.location.host}`

  function wsUrlFor(sid) {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    return `${protocol}://${window.location.host}/ws/events/${encodeURIComponent(sid)}?psk=${encodeURIComponent(psk)}`
  }

  function debugUrlFor(sid) {
    return `${hostBase}/?debug=1&sid=${encodeURIComponent(sid)}`
  }

  function addLog(kind, text) {
    const line = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
      kind,
      text,
      time: new Date().toLocaleTimeString(),
    }
    logs = [...logs.slice(-80), line]
  }

  function persistLocalPrefs() {
    localStorage.setItem('vibecheck_psk', psk)
    localStorage.setItem('vibecheck_sid', sessionId)
  }

  function applyStatePayload(payload) {
    stateLabel = payload.state || stateLabel
    attachMode = payload.attach_mode || attachMode
    controllable = Boolean(payload.controllable)
    pendingApproval = payload.pending_approval || null
    pendingInput = payload.pending_input || null
  }

  async function fetchJson(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(psk ? { 'X-PSK': psk } : {}),
      },
    })

    if (!response.ok) {
      const body = await response.text()
      throw new Error(`${response.status} ${response.statusText}: ${body}`)
    }

    return response.json()
  }

  async function refreshSessions() {
    if (!psk) {
      sessions = []
      return
    }
    try {
      const payload = await fetchJson('/api/sessions')
      sessions = Array.isArray(payload) ? payload : []

      if (!sessionId && sessions.length > 0) {
        const preferred =
          sessions.find((item) => item.attach_mode === 'live' && item.controllable) ||
          sessions.find((item) => item.controllable) ||
          sessions[0]
        sessionId = preferred.id
      }
    } catch (error) {
      addLog('error', `sessions refresh failed: ${String(error)}`)
    }
  }

  async function refreshState() {
    if (!psk || !sessionId) {
      return
    }
    try {
      const payload = await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/state`)
      applyStatePayload(payload)
    } catch (error) {
      addLog('error', `state refresh failed: ${String(error)}`)
    }
  }

  function disconnectWs() {
    if (!ws) {
      wsOpen = false
      connectionState = 'Disconnected'
      return
    }

    ws.onopen = null
    ws.onmessage = null
    ws.onerror = null
    ws.onclose = null
    ws.close()
    ws = null
    wsOpen = false
    connectionState = 'Disconnected'
  }

  function handleEvent(event) {
    switch (event.type) {
      case 'connected':
        addLog('system', `connected to ${event.session_id}`)
        break
      case 'state':
        stateLabel = event.state || stateLabel
        attachMode = event.attach_mode || attachMode
        controllable = Boolean(event.controllable)
        break
      case 'approval_request':
        pendingApproval = {
          call_id: event.call_id,
          tool_name: event.tool_name,
          args: event.args,
        }
        addLog('approval', `approval requested: ${event.tool_name} (${event.call_id})`)
        break
      case 'approval_resolution':
        if (pendingApproval && pendingApproval.call_id === event.call_id) {
          pendingApproval = null
        }
        addLog('approval', `approval resolved: ${event.call_id} -> ${event.approved ? 'approved' : 'rejected'}`)
        break
      case 'input_request':
        pendingInput = {
          request_id: event.request_id,
          question: event.question,
          options: event.options || [],
        }
        addLog('input', `input requested: ${event.request_id}`)
        break
      case 'input_resolution':
        if (pendingInput && pendingInput.request_id === event.request_id) {
          pendingInput = null
        }
        addLog('input', `input resolved: ${event.request_id}`)
        break
      case 'assistant':
        addLog('assistant', event.content || '')
        break
      case 'user_message':
        addLog('user', event.content || '')
        break
      case 'tool_call':
        addLog('tool', `tool call: ${event.tool_name} (${event.call_id})`)
        break
      case 'tool_result':
        addLog('tool', `tool result: ${event.call_id} (${event.is_error ? 'error' : 'ok'})`)
        break
      case 'heartbeat':
        break
      default:
        addLog('system', `event: ${event.type || 'unknown'}`)
        break
    }
  }

  async function connectWs() {
    if (!psk || !sessionId) {
      connectionState = 'Missing PSK or Session ID'
      return
    }

    persistLocalPrefs()
    await refreshState()
    disconnectWs()
    lastWsError = ''
    connectionState = 'Connecting...'

    const url = wsUrlFor(sessionId)
    ws = new WebSocket(url)
    ws.onopen = () => {
      wsOpen = true
      connectionState = 'Connected'
      addLog('system', `ws open (${sessionId})`)
    }
    ws.onmessage = (raw) => {
      try {
        const event = JSON.parse(raw.data)
        handleEvent(event)
      } catch (error) {
        addLog('error', `invalid ws payload: ${String(error)}`)
      }
    }
    ws.onerror = () => {
      lastWsError = 'WebSocket error'
      connectionState = 'Error'
      wsOpen = false
    }
    ws.onclose = (event) => {
      wsOpen = false
      connectionState = `Disconnected (${event.code})`
    }
  }

  async function approve(approved) {
    if (!pendingApproval || !sessionId) {
      return
    }
    try {
      await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          call_id: pendingApproval.call_id,
          approved,
        }),
      })
      addLog('approval', `${approved ? 'approved' : 'rejected'} ${pendingApproval.call_id}`)
      pendingApproval = null
      await refreshState()
    } catch (error) {
      addLog('error', `approve failed: ${String(error)}`)
    }
  }

  async function submitAnswer() {
    if (!pendingInput || !sessionId) {
      return
    }
    const response = answerText.trim()
    if (!response) {
      return
    }
    try {
      await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          request_id: pendingInput.request_id,
          response,
        }),
      })
      addLog('input', `answered ${pendingInput.request_id}`)
      answerText = ''
      pendingInput = null
      await refreshState()
    } catch (error) {
      addLog('error', `answer failed: ${String(error)}`)
    }
  }

  async function sendMessage() {
    const content = messageText.trim()
    if (!content || !sessionId) {
      return
    }
    try {
      await fetchJson(`/api/sessions/${encodeURIComponent(sessionId)}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      addLog('user', content)
      messageText = ''
    } catch (error) {
      addLog('error', `message send failed: ${String(error)}`)
    }
  }

  function handleSessionChange(event) {
    sessionId = event.target.value
    persistLocalPrefs()
    connectWs()
  }

  onMount(async () => {
    await refreshSessions()
    await refreshState()
    if (psk && sessionId) {
      connectWs()
    }
    refreshTimer = setInterval(async () => {
      await refreshSessions()
      await refreshState()
    }, 4000)
  })

  onDestroy(() => {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
    disconnectWs()
  })
</script>

<div class="app-shell">
  <header class="top-bar">
    <h1>vibecheck</h1>
    <span class="status-pill {wsOpen ? 'ok' : 'bad'}">{connectionState}</span>
  </header>

  <section class="control-card">
    <p class="label">Session Controls</p>

    <label class="field-label" for="psk">PSK</label>
    <input id="psk" bind:value={psk} placeholder="Enter PSK" />

    <label class="field-label" for="sid">Session ID</label>
    <input id="sid" bind:value={sessionId} placeholder="Enter session ID" />

    {#if sessions.length > 0}
      <label class="field-label" for="sid-select">Known sessions</label>
      <select id="sid-select" value={sessionId} on:change={handleSessionChange}>
        {#each sessions as item}
          <option value={item.id}>
            {item.id} ({item.attach_mode || 'unknown'}, {item.status || 'unknown'})
          </option>
        {/each}
      </select>
    {/if}

    <div class="button-row">
      <button class="touch-target" type="button" on:click={connectWs}>Connect</button>
      <button class="touch-target muted" type="button" on:click={disconnectWs}>Disconnect</button>
      <button class="touch-target muted" type="button" on:click={refreshState}>Refresh</button>
    </div>

    <p class="meta">state={stateLabel} mode={attachMode} controllable={String(controllable)}</p>
    {#if debugEnabled}
      <p class="meta">debug_url={debugUrlFor(sessionId)}</p>
      <p class="meta">ws_url={sessionId ? wsUrlFor(sessionId) : 'n/a'}</p>
      {#if lastWsError}
        <p class="meta warn">{lastWsError}</p>
      {/if}
    {/if}
  </section>

  <main class="message-area">
    {#if pendingApproval}
      <section class="pending-card approval">
        <p class="label">Approval Needed</p>
        <p class="body"><strong>tool:</strong> {pendingApproval.tool_name}</p>
        <p class="body"><strong>call:</strong> {pendingApproval.call_id}</p>
        <pre>{JSON.stringify(pendingApproval.args, null, 2)}</pre>
        <div class="button-row">
          <button class="touch-target approve" type="button" on:click={() => approve(true)}>Approve</button>
          <button class="touch-target reject" type="button" on:click={() => approve(false)}>Reject</button>
        </div>
      </section>
    {/if}

    {#if pendingInput}
      <section class="pending-card input">
        <p class="label">Input Needed</p>
        <p class="body">{pendingInput.question}</p>
        {#if pendingInput.options && pendingInput.options.length > 0}
          <p class="body">Options: {pendingInput.options.join(' / ')}</p>
        {/if}
        <div class="input-row">
          <input bind:value={answerText} placeholder="Type answer" />
          <button class="touch-target approve" type="button" on:click={submitAnswer}>Send</button>
        </div>
      </section>
    {/if}

    <section class="placeholder-card">
      <p class="label">Live Session Stream</p>
      {#if logs.length === 0}
        <p class="body">No events yet. Connect, then trigger a tool call from TUI.</p>
      {:else}
        <div class="log-list">
          {#each logs as line}
            <p class="log-item"><span class="time">{line.time}</span> <span class="kind">{line.kind}</span> {line.text}</p>
          {/each}
        </div>
      {/if}
    </section>
  </main>

  <footer class="input-bar">
    <input
      aria-label="Message input"
      bind:value={messageText}
      placeholder={sessionId ? 'Send message to current session' : 'Select session first'}
      on:keydown={(event) => event.key === 'Enter' && sendMessage()}
    />
    <button class="touch-target" type="button" on:click={sendMessage}>Send</button>
  </footer>
</div>

<style>
  :global(:root) {
    --bg-canvas: #0e1118;
    --bg-panel: #191f2d;
    --bg-panel-soft: #222a3b;
    --text-primary: #f2f5ff;
    --text-muted: #a8b1c7;
    --accent: #ff7000;
    --accent-muted: #ad4d00;
    --line: #33405c;
    --good: #1bbf74;
    --bad: #d65d5d;
  }

  :global(html),
  :global(body) {
    margin: 0;
    min-height: 100%;
    background:
      radial-gradient(circle at 20% 15%, #1c2439 0, transparent 38%),
      radial-gradient(circle at 85% 0%, #2e1828 0, transparent 34%),
      var(--bg-canvas);
    color: var(--text-primary);
    font-family: 'Space Grotesk', 'Avenir Next', 'Segoe UI', sans-serif;
  }

  .app-shell {
    box-sizing: border-box;
    display: grid;
    grid-template-rows: auto auto 1fr auto;
    gap: 0.75rem;
    min-height: 100dvh;
    margin: 0 auto;
    width: min(100%, 428px);
    padding:
      calc(0.75rem + env(safe-area-inset-top))
      calc(0.75rem + env(safe-area-inset-right))
      calc(0.75rem + env(safe-area-inset-bottom))
      calc(0.75rem + env(safe-area-inset-left));
  }

  .top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--bg-panel);
    padding: 0.75rem;
  }

  .top-bar h1 {
    margin: 0;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    text-transform: lowercase;
  }

  .status-pill {
    border: 1px solid var(--accent-muted);
    border-radius: 999px;
    padding: 0.35rem 0.65rem;
    color: #ffd6b0;
    font-size: 0.8rem;
    font-weight: 600;
  }

  .status-pill.ok {
    border-color: #1f7f55;
    color: #b5f8d9;
    background: #0f2e23;
  }

  .status-pill.bad {
    border-color: #7a3737;
    color: #ffcece;
    background: #311616;
  }

  .control-card,
  .placeholder-card,
  .pending-card {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: linear-gradient(165deg, var(--bg-panel-soft), var(--bg-panel));
    padding: 0.8rem;
  }

  .message-area {
    display: grid;
    gap: 0.6rem;
    overflow-y: auto;
  }

  .pending-card.approval {
    border-color: #8f5829;
    background: linear-gradient(165deg, #2c2116, #1f1a15);
  }

  .pending-card.input {
    border-color: #2e5e85;
    background: linear-gradient(165deg, #182636, #141e2a);
  }

  .label {
    margin: 0;
    color: #ffe4ca;
    font-size: 0.76rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .body {
    margin: 0.5rem 0 0;
    color: var(--text-muted);
    line-height: 1.35;
    font-size: 0.9rem;
  }

  .field-label {
    display: block;
    margin-top: 0.5rem;
    margin-bottom: 0.2rem;
    color: #d6dcef;
    font-size: 0.8rem;
  }

  .meta {
    margin: 0.45rem 0 0;
    color: #bfc8df;
    font-size: 0.74rem;
    line-height: 1.35;
    word-break: break-all;
  }

  .meta.warn {
    color: #ffbdbd;
  }

  .button-row,
  .input-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.45rem;
    margin-top: 0.6rem;
  }

  .input-row {
    grid-template-columns: 1fr auto;
  }

  .touch-target {
    min-width: 44px;
    min-height: 40px;
    border: 1px solid var(--accent-muted);
    border-radius: 10px;
    background: #25150a;
    color: #ffd9bb;
    font-weight: 600;
  }

  .touch-target.muted {
    border-color: #4f617f;
    background: #1a2233;
    color: #d3def5;
  }

  .touch-target.approve {
    border-color: #2e8e5d;
    background: #133324;
    color: #b9f9d9;
  }

  .touch-target.reject {
    border-color: #9b4949;
    background: #3a1919;
    color: #ffd1d1;
  }

  .log-list {
    margin-top: 0.5rem;
    display: grid;
    gap: 0.35rem;
  }

  .log-item {
    margin: 0;
    color: #d1daf0;
    font-size: 0.82rem;
    line-height: 1.3;
    word-break: break-word;
  }

  .time {
    color: #8ea0c5;
    margin-right: 0.2rem;
  }

  .kind {
    color: #ffc68f;
    margin-right: 0.2rem;
  }

  .input-bar {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 0.5rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--bg-panel);
    padding: 0.5rem;
  }

  input,
  select,
  pre {
    min-height: 40px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: #0f1421;
    color: var(--text-muted);
    padding: 0 0.75rem;
    box-sizing: border-box;
    width: 100%;
  }

  pre {
    margin: 0.5rem 0 0;
    min-height: 0;
    max-height: 160px;
    padding: 0.6rem 0.75rem;
    overflow: auto;
    font-size: 0.78rem;
    line-height: 1.25;
    white-space: pre-wrap;
  }
</style>
