const CACHE_NAME = "plantai-shell-v3";
const APP_SHELL = [
  "/",
  "/index.html",
  "/manifest.json",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  self.skipWaiting(); // n'attend pas la fermeture des anciens onglets pour prendre le relais
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    Promise.all([
      caches.keys().then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      ),
      self.clients.claim(), // prend le contrôle des onglets déjà ouverts, sans attendre un rechargement
    ])
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  // Navigation (chargement de la page) : réseau en priorité pour toujours servir
  // la dernière version — le cache ne sert que de secours hors-ligne.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/index.html"))
    );
    return;
  }

  // Le backend (API PlantAI, ESP32-CAM, etc.) tourne sur une autre origine
  // (autre port) que le frontend qui sert ce Service Worker. Ces requêtes ne
  // doivent JAMAIS passer par le cache applicatif — capteurs, historique,
  // images capturées, etc. doivent toujours refléter l'état réel du serveur.
  // On laisse le navigateur les gérer nativement, sans interception.
  if (new URL(event.request.url).origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(
      (cached) => cached || fetch(event.request).catch(() => cached)
    )
  );
});
