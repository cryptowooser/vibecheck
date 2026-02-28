import { expect, test } from '@playwright/test'

async function installVoiceLoopBrowserMocks(page) {
  await page.addInitScript(() => {
    let fakeNow = 1000
    Date.now = () => {
      fakeNow += 400
      return fakeNow
    }

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop: () => undefined }],
        }),
      },
    })

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
        const chunk = new Blob([new Uint8Array(4096)], { type: this.mimeType })
        if (this.ondataavailable) {
          this.ondataavailable({ data: chunk })
        }
        if (this.onstop) {
          this.onstop()
        }
      }
    }

    class MockAudio {
      constructor() {
        this.onended = null
        this.onerror = null
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

    URL.createObjectURL = () => 'blob:playwright-audio'
    URL.revokeObjectURL = () => undefined
    window.MediaRecorder = MockMediaRecorder
    window.Audio = MockAudio
  })
}

async function stubVoices(page) {
  await page.route('**/api/voices', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        voices: [
          { voice_id: 'voice-one', name: 'Voice One' },
          { voice_id: 'voice-two', name: 'Voice Two' },
        ],
      }),
    })
  })
}

test('mobile UI renders and state preview transitions work', async ({ page }) => {
  await stubVoices(page)

  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Voice Loop Prototype' })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Voice' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Record', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'State Preview' })).toBeVisible()

  const previewStates = ['idle', 'recording', 'transcribing', 'speaking', 'error']
  for (const state of previewStates) {
    await page.getByRole('button', { name: state, exact: true }).click()
    await expect(page.getByTestId('state-pill')).toHaveText(state)
  }

  await expect(page.getByRole('status')).toHaveText('Previewing error state')
})

test('mobile UI falls back to built-in voices when /api/voices fails', async ({ page }) => {
  await page.route('**/api/voices', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'unavailable' }),
    })
  })

  await page.goto('/')

  await expect(page.getByRole('combobox', { name: 'Voice' })).toBeVisible()
  await expect(page.locator('#voice-select option')).toHaveCount(6)
  await expect(page.locator('#voice-select option')).toHaveText([
    'George (EN)',
    'Bella (EN)',
    'Adam (EN)',
    'Kuon (JP)',
    'Hinata (JP)',
    'Otani (JP)',
  ])
})

test('mobile voice loop runs STT to TTS playback with selected voice', async ({ page }) => {
  await installVoiceLoopBrowserMocks(page)
  await stubVoices(page)

  let ttsPayload = null
  await page.route('**/api/stt', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text: 'mobile transcript', language: 'en' }),
    })
  })
  await page.route('**/api/tts', async (route) => {
    ttsPayload = route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: 'ID3',
    })
  })

  await page.goto('/')

  await page.getByRole('combobox', { name: 'Voice' }).selectOption('voice-two')
  await page.getByRole('button', { name: 'Record', exact: true }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()

  await expect(page.getByText('mobile transcript')).toBeVisible()
  await expect(page.getByTestId('status-message')).toHaveText('Playback complete')
  await expect(page.getByTestId('state-pill')).toHaveText('idle')
  expect(ttsPayload).toEqual({ text: 'mobile transcript', voice_id: 'voice-two' })
})

test('mobile voice loop surfaces TTS HTTP failure and recovers on retry', async ({ page }) => {
  await installVoiceLoopBrowserMocks(page)
  await stubVoices(page)

  let ttsAttempts = 0
  await page.route('**/api/stt', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text: 'mobile retry text', language: 'en' }),
    })
  })
  await page.route('**/api/tts', async (route) => {
    ttsAttempts += 1
    if (ttsAttempts === 1) {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'TTS upstream unavailable' }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: 'ID3',
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Record', exact: true }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()

  await expect(page.getByRole('heading', { name: 'Error' })).toBeVisible()
  await expect(page.getByText('TTS upstream unavailable')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry TTS' })).toBeVisible()

  await page.getByRole('button', { name: 'Retry TTS' }).click()

  await expect(page.getByTestId('status-message')).toHaveText('Playback complete')
  await expect(page.getByRole('heading', { name: 'Error' })).toHaveCount(0)
  expect(ttsAttempts).toBe(2)
})

test('mobile voice loop surfaces STT HTTP failure and recovers on retry', async ({ page }) => {
  await installVoiceLoopBrowserMocks(page)
  await stubVoices(page)

  let sttAttempts = 0
  await page.route('**/api/stt', async (route) => {
    sttAttempts += 1
    if (sttAttempts === 1) {
      await route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'STT upstream unavailable' }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text: 'stt retry transcript', language: 'en' }),
    })
  })
  await page.route('**/api/tts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: 'ID3',
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Record', exact: true }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()

  await expect(page.getByRole('heading', { name: 'Error' })).toBeVisible()
  await expect(page.getByText('STT upstream unavailable')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry STT' })).toBeVisible()

  await page.getByRole('button', { name: 'Retry STT' }).click()

  await expect(page.getByText('stt retry transcript')).toBeVisible()
  await expect(page.getByTestId('status-message')).toHaveText('Playback complete')
  await expect(page.getByRole('heading', { name: 'Error' })).toHaveCount(0)
  expect(sttAttempts).toBe(2)
})

test('mobile UI disables non-essential controls while transcription is in-flight', async ({ page }) => {
  await installVoiceLoopBrowserMocks(page)
  await stubVoices(page)

  let releaseSttRequest
  const sttRequestGate = new Promise((resolve) => {
    releaseSttRequest = resolve
  })

  await page.route('**/api/stt', async (route) => {
    await sttRequestGate
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text: 'locked controls transcript', language: 'en' }),
    })
  })
  await page.route('**/api/tts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: 'ID3',
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Record', exact: true }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()

  await expect(page.getByTestId('state-pill')).toHaveText('transcribing')
  await expect(page.getByRole('combobox', { name: 'Voice' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Record', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'idle', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'recording', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'transcribing', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'speaking', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'error', exact: true })).toBeDisabled()

  releaseSttRequest()

  await expect(page.getByTestId('state-pill')).toHaveText('idle')
})

test('mobile browser uses local proxy routes only and does not send provider auth headers', async ({ page }) => {
  await installVoiceLoopBrowserMocks(page)
  await stubVoices(page)

  const upstreamDirectCalls = []
  let sttHeaders = {}
  let ttsHeaders = {}

  page.on('request', (request) => {
    const url = request.url()
    if (url.includes('api.mistral.ai') || url.includes('api.elevenlabs.io')) {
      upstreamDirectCalls.push(url)
    }
  })

  await page.route('**/api/stt', async (route) => {
    sttHeaders = route.request().headers()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ text: 'proxy header transcript', language: 'en' }),
    })
  })
  await page.route('**/api/tts', async (route) => {
    ttsHeaders = route.request().headers()
    await route.fulfill({
      status: 200,
      contentType: 'audio/mpeg',
      body: 'ID3',
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Record', exact: true }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()

  await expect(page.getByText('proxy header transcript')).toBeVisible()
  await expect(page.getByTestId('status-message')).toHaveText('Playback complete')
  expect(upstreamDirectCalls).toEqual([])
  expect(sttHeaders.authorization).toBeUndefined()
  expect(sttHeaders['xi-api-key']).toBeUndefined()
  expect(ttsHeaders.authorization).toBeUndefined()
  expect(ttsHeaders['xi-api-key']).toBeUndefined()
})
