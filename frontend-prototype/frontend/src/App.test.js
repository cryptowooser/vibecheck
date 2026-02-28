import { fireEvent, render, screen } from '@testing-library/svelte'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.svelte'

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
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
  })
})
