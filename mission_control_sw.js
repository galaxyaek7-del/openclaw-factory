// OpenClaw Mission Control — service worker (Phase 8).
// Minimal, real PWA installability: cache-first for the app shell
// (static files, so the page still opens offline/on a flaky connection),
// network-only for every /api/ call (Mission Control's whole point is
// live real data — caching API responses would silently show stale
// business numbers, which this factory's zero-fabrication policy does
// not allow).

const CACHE_NAME = 'mission-control-shell-v1';
const SHELL_FILES = [
  '/mission_control.html',
  '/mission_control_login.html',
  '/mission_control.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/api/')) {
    return; // never intercept live data calls — always hit the network
  }

  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const network = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
