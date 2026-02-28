self.addEventListener('push', (event) => {
  let payload = { title: 'Vibe Check', body: 'Notification arrived.', type: 'approval' }
  if (event.data) {
    try {
      payload = event.data.json()
    } catch (error) {
      payload = { title: 'Vibe Check', body: event.data.text(), type: 'approval' }
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: '/icons/vibe-192.png',
      actions: [
        { action: 'approve', title: 'Approve' },
        { action: 'deny', title: 'Deny' },
      ],
      data: payload,
      tag: 'vibecheck-push',
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  const action = event.action || 'open'
  event.notification.close()

  event.waitUntil(
    (async () => {
      const allClients = await clients.matchAll({ type: 'window', includeUncontrolled: true })
      for (const client of allClients) {
        client.postMessage({ type: 'notification-click', action })
        if ('focus' in client) {
          await client.focus()
          return
        }
      }
      await clients.openWindow(`/?action=${encodeURIComponent(action)}`)
    })(),
  )
})
