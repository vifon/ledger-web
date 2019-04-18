"use strict";

const CACHE_NAME = 'v1';

self.addEventListener('install', function(event) {
  console.log('[Service Worker] Service Worker installed');
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      cache.addAll([
        '/',
        '/ledger/ui/',
        '/static/style.css'
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});
