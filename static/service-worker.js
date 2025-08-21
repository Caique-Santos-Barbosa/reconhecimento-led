const CACHE_NAME = 'facial-hdt-v1';
const urlsToCache = [
  '/',
  '/user_mode',
  '/admin_mode',
  '/static/logo.png',
  '/static/manifest.json',
  '/static/service-worker.js',
  'https://fonts.googleapis.com/css?family=Roboto:400,700&display=swap'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(function(cache) {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request)
      .then(function(response) {
        return response || fetch(event.request);
      })
  );
}); 