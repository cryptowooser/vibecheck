<script>
  import { onMount } from 'svelte'

  const STATE_IDLE = 'idle'
  const STATE_RECORDING = 'recording'
  const STATE_TRANSCRIBING = 'transcribing'
  const STATE_SPEAKING = 'speaking'
  const STATE_ERROR = 'error'
  const PREVIEW_STATES = [
    STATE_IDLE,
    STATE_RECORDING,
    STATE_TRANSCRIBING,
    STATE_SPEAKING,
    STATE_ERROR,
  ]
  const STATE_STATUS = {
    [STATE_IDLE]: 'Ready',
    [STATE_RECORDING]: 'Recording preview active',
    [STATE_TRANSCRIBING]: 'Transcribing preview...',
    [STATE_SPEAKING]: 'Speaking preview...',
    [STATE_ERROR]: 'Previewing error state',
  }

  const MIN_RECORDING_MS = 350
  const MIN_AUDIO_BYTES = 1024
  const FALLBACK_VOICES = [
    { voice_id: 'JBFqnCBsd6RMkjVDRZzb', name: 'George' },
    { voice_id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella' },
    { voice_id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam' },
  ]

  let uiState = STATE_IDLE
  let statusMessage = 'Ready'
  let transcript = ''
  let errorMessage = ''
  let lastFailedStage = ''

  let voices = []
  let selectedVoiceId = ''

  let mediaRecorder = null
  let mediaStream = null
  let dropNextRecording = false
  let chunks = []
  let recordingStartedAt = 0
  let lastRecordingBlob = null
  let lastTtsText = ''

  let currentAudio = null
  let currentAudioUrl = ''

  const stateLabel = {
    [STATE_IDLE]: 'idle',
    [STATE_RECORDING]: 'recording',
    [STATE_TRANSCRIBING]: 'transcribing',
    [STATE_SPEAKING]: 'speaking',
    [STATE_ERROR]: 'error',
  }

  const isRecording = () => uiState === STATE_RECORDING
  const isBusy = () => uiState === STATE_TRANSCRIBING || uiState === STATE_SPEAKING

  onMount(() => {
    void loadVoices()
    return () => {
      stopTracks()
      stopAudio()
    }
  })

  function stopTracks() {
    if (!mediaStream) {
      return
    }
    for (const track of mediaStream.getTracks()) {
      track.stop()
    }
    mediaStream = null
  }

  function stopAudio() {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio = null
    }
    if (currentAudioUrl) {
      URL.revokeObjectURL(currentAudioUrl)
      currentAudioUrl = ''
    }
  }

  function setError(stage, message) {
    uiState = STATE_ERROR
    errorMessage = message
    lastFailedStage = stage
    statusMessage = stage === 'stt' ? 'Transcription failed' : 'Playback failed'
  }

  function clearError() {
    errorMessage = ''
    lastFailedStage = ''
  }

  function previewState(state) {
    if (!PREVIEW_STATES.includes(state)) {
      return
    }

    if (mediaRecorder?.state === 'recording') {
      dropNextRecording = true
      mediaRecorder.stop()
    }

    if (state !== STATE_SPEAKING) {
      stopAudio()
    }

    uiState = state
    statusMessage = STATE_STATUS[state]

    if (state === STATE_ERROR) {
      errorMessage = 'Example error message for layout checks.'
      lastFailedStage = 'stt'
      return
    }

    clearError()
  }

  function getRecorderMimeType() {
    const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
    for (const type of preferred) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }
    return ''
  }

  async function loadVoices() {
    try {
      const response = await fetch('/api/voices')
      if (!response.ok) {
        throw new Error('failed to load voice list')
      }
      const payload = await response.json()
      voices = payload.voices ?? FALLBACK_VOICES
    } catch {
      voices = FALLBACK_VOICES
    }

    if (!selectedVoiceId && voices.length > 0) {
      selectedVoiceId = voices[0].voice_id
    }
  }

  async function startRecording() {
    if (isBusy() || isRecording()) {
      return
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('stt', 'This browser does not support recording.')
      return
    }

    clearError()
    statusMessage = 'Requesting microphone access...'

    try {
      stopAudio()
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
    } catch {
      setError('stt', 'Microphone permission denied. Allow access and try again.')
      return
    }

    chunks = []
    recordingStartedAt = Date.now()
    const options = {}
    const mimeType = getRecorderMimeType()
    if (mimeType) {
      options.mimeType = mimeType
    }

    mediaRecorder = new MediaRecorder(mediaStream, options)
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    }
    mediaRecorder.onerror = () => {
      stopTracks()
      mediaRecorder = null
      setError('stt', 'Recording failed. Please try again.')
    }
    mediaRecorder.onstop = () => {
      const recordedMimeType = mediaRecorder?.mimeType || 'audio/webm'
      stopTracks()
      mediaRecorder = null

      if (dropNextRecording) {
        dropNextRecording = false
        chunks = []
        return
      }

      const blob = new Blob(chunks, { type: recordedMimeType })
      void processRecording(blob)
    }

    mediaRecorder.start(200)
    uiState = STATE_RECORDING
    statusMessage = 'Recording... tap Stop when finished'
  }

  function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state !== 'recording') {
      return
    }
    uiState = STATE_TRANSCRIBING
    statusMessage = 'Transcribing...'
    mediaRecorder.stop()
  }

  async function processRecording(blob) {
    const elapsed = Date.now() - recordingStartedAt
    if (elapsed < MIN_RECORDING_MS || blob.size < MIN_AUDIO_BYTES) {
      setError('stt', 'Recording is too short. Hold record a bit longer.')
      return
    }

    lastRecordingBlob = blob

    try {
      uiState = STATE_TRANSCRIBING
      statusMessage = 'Transcribing...'
      transcript = await sendToStt(blob)
      lastTtsText = transcript
    } catch (error) {
      setError('stt', error.message)
      return
    }

    try {
      await runTtsPlayback(lastTtsText)
      uiState = STATE_IDLE
      statusMessage = 'Playback complete'
      clearError()
    } catch (error) {
      setError('tts', error.message)
    }
  }

  async function sendToStt(blob) {
    const formData = new FormData()
    formData.append('audio', blob, `recording-${Date.now()}.webm`)
    formData.append('language', 'en')

    const response = await fetch('/api/stt', { method: 'POST', body: formData })
    if (!response.ok) {
      const detail = await readErrorDetail(response, 'STT request failed')
      throw new Error(detail)
    }

    const payload = await response.json()
    const text = (payload.text ?? '').trim()
    if (!text) {
      throw new Error('Transcription came back empty')
    }
    return text
  }

  async function runTtsPlayback(text) {
    uiState = STATE_SPEAKING
    statusMessage = 'Generating speech...'

    const response = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice_id: selectedVoiceId }),
    })

    if (!response.ok) {
      const detail = await readErrorDetail(response, 'TTS request failed')
      throw new Error(detail)
    }

    const audioBlob = await response.blob()
    if (audioBlob.size === 0) {
      throw new Error('TTS returned empty audio')
    }

    await playAudioBlob(audioBlob)
  }

  async function playAudioBlob(audioBlob) {
    stopAudio()
    currentAudioUrl = URL.createObjectURL(audioBlob)
    currentAudio = new Audio(currentAudioUrl)
    currentAudio.preload = 'auto'

    await new Promise((resolve, reject) => {
      if (!currentAudio) {
        reject(new Error('Audio player unavailable'))
        return
      }

      currentAudio.onended = () => {
        stopAudio()
        resolve()
      }
      currentAudio.onerror = () => {
        stopAudio()
        reject(new Error('Audio playback failed'))
      }
      const playPromise = currentAudio.play()
      if (playPromise) {
        playPromise.catch(() => {
          stopAudio()
          reject(new Error('Playback blocked. Tap retry to play audio.'))
        })
      }
    })
  }

  async function retryStt() {
    if (!lastRecordingBlob) {
      return
    }
    clearError()
    await processRecording(lastRecordingBlob)
  }

  async function retryTts() {
    const text = (lastTtsText || transcript).trim()
    if (!text) {
      return
    }
    clearError()
    try {
      await runTtsPlayback(text)
      uiState = STATE_IDLE
      statusMessage = 'Playback complete'
    } catch (error) {
      setError('tts', error.message)
    }
  }

  async function readErrorDetail(response, fallback) {
    try {
      const payload = await response.json()
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        return payload.detail
      }
    } catch {
      // Ignore JSON parse failures and use fallback below.
    }
    return `${fallback} (HTTP ${response.status})`
  }
</script>

<main class="shell">
  <header class="card">
    <h1>Voice Loop Prototype</h1>
    <p>Record speech, transcribe, then synthesize playback.</p>
  </header>

  <section class={`card controls state-surface state-${uiState}`}>
    <label for="voice-select">Voice</label>
    <select id="voice-select" bind:value={selectedVoiceId} disabled={isRecording() || isBusy()}>
      {#each voices as voice}
        <option value={voice.voice_id}>{voice.name}</option>
      {/each}
    </select>

    {#if isRecording()}
      <button class="action action-stop" on:click={stopRecording}>Stop</button>
    {:else}
      <button class="action action-record" on:click={startRecording} disabled={isBusy()}>
        Record
      </button>
    {/if}

    <p class={`state-pill state-${uiState}`} data-testid="state-pill">{stateLabel[uiState]}</p>
    <p class="status" role="status" aria-live="polite" data-testid="status-message">{statusMessage}</p>
  </section>

  <section class="card state-preview">
    <h2>State Preview</h2>
    <p class="preview-copy">Use these buttons to preview all UI states without API calls.</p>
    <div class="preview-grid">
      {#each PREVIEW_STATES as state}
        <button
          class={`preview-button preview-${state} ${uiState === state ? 'is-active' : ''}`}
          on:click={() => previewState(state)}
        >
          {state}
        </button>
      {/each}
    </div>
  </section>

  <section class="card transcript">
    <h2>Transcript</h2>
    {#if transcript}
      <p>{transcript}</p>
    {:else}
      <p class="placeholder">Your transcript will appear here.</p>
    {/if}
  </section>

  {#if errorMessage}
    <section class="card error">
      <h2>Error</h2>
      <p>{errorMessage}</p>
      <div class="retry-row">
        {#if lastFailedStage === 'stt' && lastRecordingBlob}
          <button class="secondary" on:click={retryStt}>Retry STT</button>
        {/if}
        {#if transcript}
          <button class="secondary" on:click={retryTts}>Retry TTS</button>
        {/if}
      </div>
    </section>
  {/if}
</main>
