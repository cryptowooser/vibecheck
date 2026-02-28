import { fireEvent, render, screen } from '@testing-library/svelte'
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
      await Promise.resolve()

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
      return jsonResponse({ detail: 'Not found' }, 404)
    })
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('records, uploads to /api/stt, and renders transcript text', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })

    const nowValues = [1000, 1800, 2000]
    vi.spyOn(Date, 'now').mockImplementation(() => nowValues.shift() ?? 2200)

    try {
      render(App)

      await fireEvent.click(screen.getByRole('button', { name: 'Record' }))
      await fireEvent.click(screen.getByRole('button', { name: 'Stop' }))

      expect(await screen.findByText('transcribed text')).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledWith('/api/stt', expect.objectContaining({ method: 'POST' }))
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

  it('rejects very short recordings and does not call /api/stt', async () => {
    const restoreMediaDevices = installMediaDevices(vi.fn().mockResolvedValue({ getTracks: () => [] }))
    installRecorderMock({ chunkBytes: 4096 })

    const nowValues = [1000, 1150]
    vi.spyOn(Date, 'now').mockImplementation(() => nowValues.shift() ?? 1200)

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
    const nowValues = [1000, 1800, 2200]
    vi.spyOn(Date, 'now').mockImplementation(() => nowValues.shift() ?? 2400)

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
