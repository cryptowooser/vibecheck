import { fireEvent, render, screen, waitFor } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.svelte'

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function installMediaDevices(getUserMedia) {
  const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia },
  })

  return () => {
    if (originalMediaDevices) {
      Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices)
      return
    }
    Reflect.deleteProperty(navigator, 'mediaDevices')
  }
}

function installRecorderMock({ chunkBytes = 4096 } = {}) {
  class MockMediaRecorder {
    static isTypeSupported() {
      return true
    }

    constructor() {
      this.state = 'inactive'
      this.mimeType = 'audio/webm'
      this.ondataavailable = null
      this.onerror = null
      this.onstop = null
    }

    start() {
      this.state = 'recording'
    }

    stop() {
      this.state = 'inactive'
      if (chunkBytes > 0 && this.ondataavailable) {
        const data = new Blob([new Uint8Array(chunkBytes)], { type: this.mimeType })
        this.ondataavailable({ data })
      }
      if (this.onstop) {
        this.onstop()
      }
    }
  }

  vi.stubGlobal('MediaRecorder', MockMediaRecorder)
  window.MediaRecorder = MockMediaRecorder
}

function installPlaybackMocks() {
  const originalCreateObjectURL = URL.createObjectURL
  const originalRevokeObjectURL = URL.revokeObjectURL

  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: vi.fn(() => 'blob:mock-audio'),
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: vi.fn(),
  })

  class MockAudio {
    constructor() {
      this.onended = null
      this.onerror = null
      this.preload = 'auto'
    }

    pause() {
      return undefined
    }

    play() {
      queueMicrotask(() => {
        if (this.onended) {
          this.onended()
        }
      })
      return Promise.resolve()
    }
  }

  vi.stubGlobal('Audio', MockAudio)
  window.Audio = MockAudio

  return () => {
    if (originalCreateObjectURL) {
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        value: originalCreateObjectURL,
      })
    } else {
      Reflect.deleteProperty(URL, 'createObjectURL')
    }

    if (originalRevokeObjectURL) {
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        value: originalRevokeObjectURL,
      })
    } else {
      Reflect.deleteProperty(URL, 'revokeObjectURL')
    }
  }
}

function installDateNowIncrementMock(step = 400, start = 1000) {
  let current = start
  return vi.spyOn(Date, 'now').mockImplementation(() => {
    current += step
    return current
  })
}

function createDeferred() {
  let resolve
  let reject
  const promise = new Promise((promiseResolve, promiseReject) => {
    resolve = promiseResolve
    reject = promiseReject
  })
  return { promise, resolve, reject }
}

describe('App milestone 2 state preview', () => {
  let fetchMock

  beforeEach(() => {
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [
            { voice_id: 'voice-one', name: 'Voice One' },
            { voice_id: 'voice-two', name: 'Voice Two' },
          ],
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders a state preview panel with all five states', async () => {
    render(App)

    expect(screen.getByRole('heading', { name: 'State Preview' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('Ready')
    expect(screen.getByRole('button', { name: 'idle' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'recording' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'transcribing' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'speaking' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'error' })).toBeInTheDocument()
    expect(await screen.findByText('Voice One')).toBeInTheDocument()
  })

  it('switches to error state preview without API calls', async () => {
    render(App)

    await fireEvent.click(screen.getByRole('button', { name: 'error' }))
    expect(screen.getByTestId('state-pill')).toHaveTextContent('error')
    expect(screen.getByTestId('status-message')).toHaveTextContent('Previewing error state')
    expect(screen.getByRole('heading', { name: 'Error' })).toBeInTheDocument()
  })

  it('updates the state pill and surface class for each preview state', async () => {
    const { container } = render(App)

    const expectedStates = ['idle', 'recording', 'transcribing', 'speaking', 'error']

    for (const state of expectedStates) {
      await fireEvent.click(screen.getByRole('button', { name: state }))
      expect(screen.getByTestId('state-pill')).toHaveTextContent(state)
      expect(container.querySelector('.state-surface')).toHaveClass(`state-${state}`)
    }
  })

  it('stops active recording when preview state is changed', async () => {
    const stopTrack = vi.fn()
    const mockStream = { getTracks: () => [{ stop: stopTrack }] }
    const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')

    class MockMediaRecorder {
      static stopCalls = 0
      static isTypeSupported() {
        return true
      }

      constructor() {
        this.state = 'inactive'
        this.mimeType = 'audio/webm'
        this.ondataavailable = null
        this.onerror = null
        this.onstop = null
      }

      start() {
        this.state = 'recording'
      }

      stop() {
        MockMediaRecorder.stopCalls += 1
        this.state = 'inactive'
        if (this.onstop) {
          this.onstop()
        }
      }
    }

    try {
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: { getUserMedia: vi.fn().mockResolvedValue(mockStream) },
      })
      vi.stubGlobal('MediaRecorder', MockMediaRecorder)
      window.MediaRecorder = MockMediaRecorder

      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()

      await fireEvent.click(screen.getByRole('button', { name: 'idle' }))

      expect(MockMediaRecorder.stopCalls).toBe(1)
      expect(stopTrack).toHaveBeenCalledTimes(1)
      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
    } finally {
      if (originalMediaDevices) {
        Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices)
      } else {
        Reflect.deleteProperty(navigator, 'mediaDevices')
      }
    }
  })

  it('does not stop a new recording when a previous preview-canceled recorder finishes', async () => {
    const stopTrackOne = vi.fn()
    const stopTrackTwo = vi.fn()
    const streamOne = { getTracks: () => [{ stop: stopTrackOne }] }
    const streamTwo = { getTracks: () => [{ stop: stopTrackTwo }] }
    const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')

    class AsyncStopMediaRecorder {
      static stopQueue = []

      static isTypeSupported() {
        return true
      }

      static flushOneStop() {
        const callback = AsyncStopMediaRecorder.stopQueue.shift()
        if (callback) {
          callback()
        }
      }

      constructor() {
        this.state = 'inactive'
        this.mimeType = 'audio/webm'
        this.ondataavailable = null
        this.onerror = null
        this.onstop = null
      }

      start() {
        this.state = 'recording'
      }

      stop() {
        this.state = 'inactive'
        AsyncStopMediaRecorder.stopQueue.push(() => {
          if (this.onstop) {
            this.onstop()
          }
        })
      }
    }

    try {
      const getUserMedia = vi.fn().mockResolvedValueOnce(streamOne).mockResolvedValueOnce(streamTwo)
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: { getUserMedia },
      })
      vi.stubGlobal('MediaRecorder', AsyncStopMediaRecorder)
      window.MediaRecorder = AsyncStopMediaRecorder

      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'idle' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
      AsyncStopMediaRecorder.flushOneStop()

      expect(stopTrackOne).toHaveBeenCalledTimes(1)
      expect(stopTrackTwo).not.toHaveBeenCalled()
      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
    } finally {
      if (originalMediaDevices) {
        Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices)
      } else {
        Reflect.deleteProperty(navigator, 'mediaDevices')
      }
    }
  })

  it('ignores stale recorder errors from a previous session', async () => {
    const stopTrackOne = vi.fn()
    const stopTrackTwo = vi.fn()
    const streamOne = { getTracks: () => [{ stop: stopTrackOne }] }
    const streamTwo = { getTracks: () => [{ stop: stopTrackTwo }] }
    const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')

    class RecorderWithManualError {
      static instances = []

      static isTypeSupported() {
        return true
      }

      static emitError(index) {
        const instance = RecorderWithManualError.instances[index]
        if (instance?.onerror) {
          instance.onerror()
        }
      }

      constructor() {
        this.state = 'inactive'
        this.mimeType = 'audio/webm'
        this.ondataavailable = null
        this.onerror = null
        this.onstop = null
        RecorderWithManualError.instances.push(this)
      }

      start() {
        this.state = 'recording'
      }

      stop() {
        this.state = 'inactive'
        if (this.onstop) {
          this.onstop()
        }
      }
    }

    try {
      const getUserMedia = vi.fn().mockResolvedValueOnce(streamOne).mockResolvedValueOnce(streamTwo)
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: { getUserMedia },
      })
      vi.stubGlobal('MediaRecorder', RecorderWithManualError)
      window.MediaRecorder = RecorderWithManualError

      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'idle' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()

      RecorderWithManualError.emitError(0)

      expect(screen.queryByRole('heading', { name: 'Error' })).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
      expect(stopTrackOne).toHaveBeenCalled()
      expect(stopTrackTwo).not.toHaveBeenCalled()
    } finally {
      if (originalMediaDevices) {
        Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices)
      } else {
        Reflect.deleteProperty(navigator, 'mediaDevices')
      }
    }
  })

  it('does not process dropped recording when stale error arrives before delayed stop', async () => {
    const stopTrackOne = vi.fn()
    const stopTrackTwo = vi.fn()
    const streamOne = { getTracks: () => [{ stop: stopTrackOne }] }
    const streamTwo = { getTracks: () => [{ stop: stopTrackTwo }] }
    const originalMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')

    class DelayedStopRecorder {
      static instances = []
      static stopQueue = []

      static isTypeSupported() {
        return true
      }

      static emitError(index) {
        const instance = DelayedStopRecorder.instances[index]
        if (instance?.onerror) {
          instance.onerror()
        }
      }

      static flushOneStop() {
        const callback = DelayedStopRecorder.stopQueue.shift()
        if (callback) {
          callback()
        }
      }

      constructor() {
        this.state = 'inactive'
        this.mimeType = 'audio/webm'
        this.ondataavailable = null
        this.onerror = null
        this.onstop = null
        DelayedStopRecorder.instances.push(this)
      }

      start() {
        this.state = 'recording'
      }

      stop() {
        this.state = 'inactive'
        DelayedStopRecorder.stopQueue.push(() => {
          if (this.onstop) {
            this.onstop()
          }
        })
      }
    }

    try {
      const getUserMedia = vi.fn().mockResolvedValueOnce(streamOne).mockResolvedValueOnce(streamTwo)
      Object.defineProperty(navigator, 'mediaDevices', {
        configurable: true,
        value: { getUserMedia },
      })
      vi.stubGlobal('MediaRecorder', DelayedStopRecorder)
      window.MediaRecorder = DelayedStopRecorder

      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'idle' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      DelayedStopRecorder.emitError(0)
      DelayedStopRecorder.flushOneStop()
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
      })

      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
      expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument()
      expect(stopTrackOne).toHaveBeenCalled()
      expect(stopTrackTwo).not.toHaveBeenCalled()
    } finally {
      if (originalMediaDevices) {
        Object.defineProperty(navigator, 'mediaDevices', originalMediaDevices)
      } else {
        Reflect.deleteProperty(navigator, 'mediaDevices')
      }
    }
  })
})

describe('App milestone 3 STT integration', () => {
  let fetchMock
  let restorePlaybackMocks

  beforeEach(() => {
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: 'transcribed text', language: 'en' })
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
    restorePlaybackMocks = installPlaybackMocks()
  })

  afterEach(() => {
    if (restorePlaybackMocks) {
      restorePlaybackMocks()
      restorePlaybackMocks = null
    }
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('records, uploads to /api/stt, and completes clean playback path', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByText('transcribed text')).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledWith('/api/stt', expect.objectContaining({ method: 'POST' }))
      expect(fetchMock).toHaveBeenCalledWith('/api/tts', expect.objectContaining({ method: 'POST' }))
      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })
      expect(screen.queryByRole('heading', { name: 'Error' })).not.toBeInTheDocument()
      expect(screen.getByTestId('status-message')).toHaveTextContent('Playback complete')
    } finally {
      restoreMediaDevices()
    }
  })

  it('posts expected FormData fields to /api/stt', async () => {
    let sttRequestBody
    fetchMock = vi.fn(async (resource, options = {}) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        sttRequestBody = options.body
        return jsonResponse({ text: 'shape check', language: 'en' })
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      await screen.findByText('shape check')
      expect(sttRequestBody).toBeInstanceOf(FormData)
      expect(sttRequestBody.get('language')).toBe('en')

      const audioField = sttRequestBody.get('audio')
      expect(audioField).toBeInstanceOf(Blob)
      expect(audioField.size).toBeGreaterThan(0)
    } finally {
      restoreMediaDevices()
    }
  })

  it('shows actionable error when microphone permission is denied', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockRejectedValue(new Error('denied')))
    installRecorderMock()

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByText(/microphone permission denied/i)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
    } finally {
      restoreMediaDevices()
    }
  })

  it('shows unsupported-browser error when MediaRecorder is unavailable', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    const originalWindowMediaRecorder = window.MediaRecorder

    try {
      window.MediaRecorder = undefined

      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByText(/does not support recording/i)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
    } finally {
      window.MediaRecorder = originalWindowMediaRecorder
      restoreMediaDevices()
    }
  })

  it('rejects very short recordings and does not call /api/stt', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(100)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByText(/recording is too short/i)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
    } finally {
      restoreMediaDevices()
    }
  })

  it('rejects recordings smaller than the byte-size floor and does not call /api/stt', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 1500 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByText(/recording is too short/i)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith('/api/stt', expect.anything())
    } finally {
      restoreMediaDevices()
    }
  })

  it('shows explicit error when STT response text is empty', async () => {
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: '   ', language: 'en' })
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByText(/transcription came back empty/i)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith('/api/tts', expect.anything())
    } finally {
      restoreMediaDevices()
    }
  })

  it('offers Retry STT and re-attempts transcription after a failed STT request', async () => {
    let sttAttempts = 0
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        sttAttempts += 1
        return jsonResponse({ detail: 'upstream unavailable' }, 502)
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      const retryButton = await screen.findByRole('button', { name: 'Retry STT' })
      expect(retryButton).toBeInTheDocument()
      expect(sttAttempts).toBe(1)

      await fireEvent.click(retryButton)
      await screen.findByRole('heading', { name: 'Error' })
      expect(sttAttempts).toBe(2)
    } finally {
      restoreMediaDevices()
    }
  })
})

describe('App milestone 4 TTS integration and playback', () => {
  let fetchMock
  let restorePlaybackMocks

  beforeEach(() => {
    restorePlaybackMocks = installPlaybackMocks()
  })

  afterEach(() => {
    if (restorePlaybackMocks) {
      restorePlaybackMocks()
      restorePlaybackMocks = null
    }
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('posts selected voice to /api/tts and shows speaking state during playback', async () => {
    let ttsPayload = null
    fetchMock = vi.fn(async (resource, options = {}) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [
            { voice_id: 'voice-one', name: 'Voice One' },
            { voice_id: 'voice-two', name: 'Voice Two' },
          ],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: 'speak this back', language: 'en' })
      }
      if (resource === '/api/tts') {
        ttsPayload = JSON.parse(options.body)
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    class ControlledAudio {
      static instances = []

      constructor() {
        this.onended = null
        this.onerror = null
        this.preload = 'auto'
        ControlledAudio.instances.push(this)
      }

      pause() {
        return undefined
      }

      play() {
        return Promise.resolve()
      }
    }

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)
    vi.stubGlobal('Audio', ControlledAudio)
    window.Audio = ControlledAudio

    try {
      render(App)

      await screen.findByRole('option', { name: 'Voice Two' })
      await fireEvent.change(screen.getByRole('combobox', { name: 'Voice' }), {
        target: { value: 'voice-two' },
      })

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('speaking')
        expect(screen.getByTestId('status-message')).toHaveTextContent('Speaking...')
      })
      expect(ttsPayload).toEqual({ text: 'speak this back', voice_id: 'voice-two' })

      const activeAudio = ControlledAudio.instances.at(-1)
      expect(activeAudio).toBeDefined()
      activeAudio.onended()

      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })
      expect(screen.getByTestId('status-message')).toHaveTextContent('Playback complete')
    } finally {
      restoreMediaDevices()
    }
  })

  it('surfaces TTS HTTP error details and offers Retry TTS', async () => {
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: 'retry playback', language: 'en' })
      }
      if (resource === '/api/tts') {
        return jsonResponse({ detail: 'TTS upstream unavailable' }, 502)
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByText('TTS upstream unavailable')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry TTS' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Retry STT' })).not.toBeInTheDocument()
    } finally {
      restoreMediaDevices()
    }
  })

  it('surfaces an explicit error when /api/tts returns empty audio', async () => {
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: 'retry playback', language: 'en' })
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array(), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByText('TTS returned empty audio')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry TTS' })).toBeInTheDocument()
    } finally {
      restoreMediaDevices()
    }
  })

  it('surfaces playback errors and allows Retry TTS to recover', async () => {
    let ttsAttempts = 0
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return jsonResponse({ text: 'retry playback', language: 'en' })
      }
      if (resource === '/api/tts') {
        ttsAttempts += 1
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    class FlakyAudio {
      static playCalls = 0

      constructor() {
        this.onended = null
        this.onerror = null
        this.preload = 'auto'
      }

      pause() {
        return undefined
      }

      play() {
        FlakyAudio.playCalls += 1
        if (FlakyAudio.playCalls === 1) {
          return Promise.reject(new Error('blocked by browser'))
        }
        queueMicrotask(() => {
          if (this.onended) {
            this.onended()
          }
        })
        return Promise.resolve()
      }
    }

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)
    vi.stubGlobal('Audio', FlakyAudio)
    window.Audio = FlakyAudio

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByText(/playback blocked\. tap retry to play audio\./i)).toBeInTheDocument()
      expect(ttsAttempts).toBe(1)

      await fireEvent.click(screen.getByRole('button', { name: 'Retry TTS' }))

      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })
      expect(screen.getByTestId('status-message')).toHaveTextContent('Playback complete')
      expect(screen.queryByRole('heading', { name: 'Error' })).not.toBeInTheDocument()
      expect(ttsAttempts).toBe(2)
    } finally {
      restoreMediaDevices()
    }
  })

  it('hides Retry TTS after a later STT failure to avoid replaying stale transcript', async () => {
    let sttAttempts = 0
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        sttAttempts += 1
        if (sttAttempts === 1) {
          return jsonResponse({ text: 'first transcript', language: 'en' })
        }
        return jsonResponse({ detail: 'upstream unavailable' }, 502)
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })
      expect(screen.getByText('first transcript')).toBeInTheDocument()

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByRole('heading', { name: 'Error' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry STT' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Retry TTS' })).not.toBeInTheDocument()
    } finally {
      restoreMediaDevices()
    }
  })
})

describe('App milestone 5 hardening and stability', () => {
  let fetchMock
  let restorePlaybackMocks

  beforeEach(() => {
    restorePlaybackMocks = installPlaybackMocks()
  })

  afterEach(() => {
    if (restorePlaybackMocks) {
      restorePlaybackMocks()
      restorePlaybackMocks = null
    }
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('clears stale transcript state when a new recording starts', async () => {
    let sttAttempts = 0
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        sttAttempts += 1
        if (sttAttempts === 1) {
          return jsonResponse({ text: 'first transcript', language: 'en' })
        }
        return jsonResponse({ text: 'second transcript', language: 'en' })
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      await screen.findByText('first transcript')
      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))

      expect(screen.queryByText('first transcript')).not.toBeInTheDocument()
      expect(screen.getByText('Your transcript will appear here.')).toBeInTheDocument()
    } finally {
      restoreMediaDevices()
    }
  })

  it('disables non-essential controls while transcription request is in flight', async () => {
    const sttDeferred = createDeferred()
    fetchMock = vi.fn(async (resource) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        return sttDeferred.promise
      }
      if (resource === '/api/tts') {
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('transcribing')
      })
      expect(screen.getByRole('combobox', { name: 'Voice' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'Record' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'idle' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'recording' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'transcribing' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'speaking' })).toBeDisabled()
      expect(screen.getByRole('button', { name: 'error' })).toBeDisabled()

      sttDeferred.resolve(jsonResponse({ text: 'deferred transcript', language: 'en' }))
      await waitFor(() => {
        expect(screen.getByTestId('state-pill')).toHaveTextContent('idle')
      })
    } finally {
      restoreMediaDevices()
    }
  })

  it('sends browser requests only to proxy endpoints without provider API auth headers', async () => {
    let sttHeaders = null
    let ttsHeaders = null

    fetchMock = vi.fn(async (resource, options = {}) => {
      if (resource === '/api/voices') {
        return jsonResponse({
          voices: [{ voice_id: 'voice-one', name: 'Voice One' }],
        })
      }
      if (resource === '/api/stt') {
        sttHeaders = options.headers ?? {}
        return jsonResponse({ text: 'header check', language: 'en' })
      }
      if (resource === '/api/tts') {
        ttsHeaders = options.headers ?? {}
        return new Response(new Uint8Array([73, 68, 51]), {
          status: 200,
          headers: { 'Content-Type': 'audio/mpeg' },
        })
      }
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)

    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })
    installDateNowIncrementMock(400)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))
      await screen.findByText('header check')

      const calledUrls = fetchMock.mock.calls.map(([resource]) => resource)
      expect(calledUrls).toContain('/api/voices')
      expect(calledUrls).toContain('/api/stt')
      expect(calledUrls).toContain('/api/tts')
      expect(calledUrls.every((resource) => typeof resource === 'string' && resource.startsWith('/api/'))).toBe(
        true,
      )

      expect(Object.keys(sttHeaders)).toEqual([])
      expect(ttsHeaders).toEqual({ 'Content-Type': 'application/json' })
      expect(ttsHeaders.authorization ?? ttsHeaders.Authorization).toBeUndefined()
      expect(ttsHeaders['xi-api-key']).toBeUndefined()
    } finally {
      restoreMediaDevices()
    }
  })
})
