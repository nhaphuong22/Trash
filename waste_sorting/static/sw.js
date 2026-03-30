// Service Worker — Trash Rewards PWA
const CACHE = 'trash-rewards-v1';
const ASSETS = ['/user', '/static/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // API calls: network only (không cache)
  if (e.request.url.includes('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }
  // Video feed: network only
  if (e.request.url.includes('/video_feed')) {
    e.respondWith(fetch(e.request));
    return;
  }
  // Các asset khác: cache first
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
