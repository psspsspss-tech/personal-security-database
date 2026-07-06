/**
 * sw.js — Security Dashboard Service Worker
 * 
 * Strategy: NETWORK FIRST with fallback to cache.
 * - Always tries to fetch fresh content from the server
 * - Falls back to cached version only if offline
 * - This means every restart of the server delivers fresh dashboard to all devices
 */

const CACHE_NAME = 'security-dashboard-v201';

// Files to pre-cache for offline fallback
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/style.css',
  '/app.js',
  '/blackjack.js',
  '/casino_engine.js',
  '/crash.js',
  '/gamba_plus.js',
  '/tetris.js',
  '/hangman.js',
  '/hackerman.js',
  '/offline_tv.js',
  '/offline_tv_games.js',
  '/radio_comm.js',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png'
];

// ── Install: cache core files ──
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting(); // Activate immediately, don't wait for old SW
});

// ── Activate: clean up old caches ──
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim(); // Take control of all open tabs immediately
});

// ── Fetch: Network First strategy ──
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls: always network, never cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Static assets: try network first, fall back to cache
  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        // Got fresh response — update the cache
        if (networkResponse && networkResponse.status === 200) {
          const cloned = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, cloned));
        }
        return networkResponse;
      })
      .catch(() => {
        // Network failed (offline) — serve from cache using ignoreSearch
        return caches.match(event.request, { ignoreSearch: true });
      })
  );
});

// ── Listen for "SKIP_WAITING" message (sent by app.js on update) ──
self.addEventListener('message', event => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});













