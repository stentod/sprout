// Service Worker for Sprout Budget - Advanced Cache Control
const CACHE_NAME = 'sprout-budget-v3.0';
const STATIC_CACHE = 'sprout-static-v3.0';

// Files to cache
const STATIC_FILES = [
  '/',
  '/auth.html',
  '/history.html',
  '/settings.html',
  '/reset-password.html',
  '/debug-api.html',
  '/style.css',
  '/main.js',
  '/auth.js',
  '/history.js',
  '/settings.js',
  '/reset-password.js',
  '/logo.svg'
];

// Install event - cache static files
self.addEventListener('install', function(event) {
  console.log('Service Worker installing...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function(cache) {
      console.log('Caching static files');
      return cache.addAll(STATIC_FILES);
    }).then(function() {
      console.log('Service Worker installed successfully');
      return self.skipWaiting();
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', function(event) {
  console.log('Service Worker activating...');
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.map(function(cacheName) {
          // Delete old caches
          if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(function() {
      console.log('Service Worker activated successfully');
      return self.clients.claim();
    })
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', function(event) {
  const url = new URL(event.request.url);
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Handle HTML files - always fetch fresh
  if (url.pathname.endsWith('.html') || url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then(function(response) {
          // Don't cache HTML files
          return response;
        })
        .catch(function() {
          // Fallback to cache if network fails
          return caches.match(event.request);
        })
    );
    return;
  }
  
  // Handle CSS and JS files - aggressive cache busting
  if (url.pathname.endsWith('.css') || url.pathname.endsWith('.js')) {
    event.respondWith(
      fetch(event.request, {
        cache: 'no-cache',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate'
        }
      })
      .then(function(response) {
        // Don't cache CSS/JS files
        return response;
      })
      .catch(function() {
        // Fallback to cache if network fails
        return caches.match(event.request);
      })
    );
    return;
  }
  
  // Handle API requests - never cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request, {
        cache: 'no-cache',
        credentials: 'include'
      })
    );
    return;
  }
  
  // Handle other static files
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        if (response) {
          // Return cached version
          return response;
        }
        
        // Fetch from network
        return fetch(event.request)
          .then(function(response) {
            // Don't cache anything by default
            return response;
          });
      })
  );
});

// Message event - handle cache clearing
self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'CLEAR_CACHE') {
    console.log('Clearing all caches...');
    event.waitUntil(
      caches.keys().then(function(cacheNames) {
        return Promise.all(
          cacheNames.map(function(cacheName) {
            return caches.delete(cacheName);
          })
        );
      })
    );
  }
});
