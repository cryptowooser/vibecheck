const CACHE_NAME = 'pwa-install-proto-v1'

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(['/', '/index.html'])),
  )
})

self.addEventListener('fetch', (event) => {
  if (event.request.mode !== 'navigate') return

  event.respondWith(
    fetch(event.request).catch(async () => {
      const cache = await caches.open(CACHE_NAME)
      return cache.match('/index.html')
    }),
  )
})
