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
  if (event.request.url.endsWith('/accounts/logout/')
      || (event.request.url.endsWith('/accounts/login/')
          && event.request.method == 'POST')) {
    event.respondWith(
      fetch(event.request).then(
        response => caches.open(CACHE_NAME).then(
          cache => cache.addAll([
            '/',
            '/ledger/ui/'
          ])
        ).then(() => response)
      )
    );
  } else {
    event.respondWith(
      caches.match(event.request).then(function(response) {
        if (response) {
          fetch(event.request).then(function(response) {
            if (response.ok) {
              return caches.open(CACHE_NAME).then(function(cache) {
                cache.put(event.request, response.clone());
                return response;
              });
            } else {
              return response;
            }
          });
          return response;
        } else {
          return fetch(event.request);
        }
      })
    );
  }
});
