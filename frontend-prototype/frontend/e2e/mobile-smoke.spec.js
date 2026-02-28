import { expect, test } from '@playwright/test'

test('mobile UI renders and state preview transitions work', async ({ page }) => {
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
