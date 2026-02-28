<script>
  const connectionState = 'Disconnected'
</script>

<div class="app-shell">
  <header class="top-bar">
    <h1>vibecheck</h1>
    <span class="status-pill">{connectionState}</span>
  </header>

  <main class="message-area">
    <section class="placeholder-card">
      <p class="label">Live Session Stream</p>
      <p class="body">
        Assistant messages, tool calls, approvals, and bridge status updates will render here once the
        backend session channel is connected.
      </p>
    </section>
  </main>

  <footer class="input-bar">
    <button class="touch-target" type="button">Mic</button>
    <input aria-label="Message input" disabled placeholder="Message input coming in Phase 3" />
    <button class="touch-target" type="button">Send</button>
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
    grid-template-rows: auto 1fr auto;
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

  .message-area {
    overflow-y: auto;
  }

  .placeholder-card {
    border: 1px solid var(--line);
    border-radius: 14px;
    background: linear-gradient(165deg, var(--bg-panel-soft), var(--bg-panel));
    padding: 1rem;
  }

  .label {
    margin: 0;
    color: #ffe4ca;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .body {
    margin: 0.65rem 0 0;
    color: var(--text-muted);
    line-height: 1.45;
    font-size: 0.95rem;
  }

  .input-bar {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 0.5rem;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--bg-panel);
    padding: 0.5rem;
  }

  .touch-target {
    min-width: 44px;
    min-height: 44px;
    border: 1px solid var(--accent-muted);
    border-radius: 10px;
    background: #25150a;
    color: #ffd9bb;
    font-weight: 600;
  }

  input {
    min-height: 44px;
    border: 1px solid var(--line);
    border-radius: 10px;
    background: #0f1421;
    color: var(--text-muted);
    padding: 0 0.75rem;
  }
</style>
