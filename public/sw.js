// Service Worker del Panel Café Real
// Versión mínima: solo existe para que el navegador considere la app "instalable".
// A propósito NO cachea nada todavía, para que mientras sigas desarrollando
// y subiendo cambios a Vercel, el panel siempre muestre la última versión.
//
// Cuando el proyecto esté más estable y quieran que el panel funcione
// offline, aquí se agrega una estrategia de caché (cache-first / network-first)
// con un número de versión para invalidar cachés viejas.

self.addEventListener("install", (event) => {
  // Activa este SW de inmediato, sin esperar a que se cierren las pestañas viejas.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  // Toma control de las páginas abiertas de inmediato.
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Por ahora dejamos pasar todas las peticiones normales a la red,
  // tal cual como si no hubiera service worker. Esto es intencional:
  // evita cualquier riesgo de romper el panel mientras lo siguen desarrollando.
  return;
});