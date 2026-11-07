// Script ES5 volontairement simple, pour rester compatible avec les anciens navigateurs.
(function () {
  var statusEl = document.getElementById('status');
  var reloadBtn = document.getElementById('reload');

  function setStatus(text) {
    if (statusEl) {
      statusEl.innerHTML = '';
      statusEl.appendChild(document.createTextNode(text));
    }
  }

  function updateOnlineState() {
    if (navigator.onLine === false) {
      setStatus('Mode hors ligne : contenu local');
    } else {
      setStatus('En ligne');
    }
  }

  updateOnlineState();

  if (window.addEventListener) {
    window.addEventListener('online', updateOnlineState, false);
    window.addEventListener('offline', updateOnlineState, false);
  }

  // Suivi du cache AppCache (si le navigateur le gère)
  var cache = window.applicationCache;
  if (cache) {
    var onCacheEvent = function (label) {
      return function () { setStatus(label); };
    };
    if (cache.addEventListener) {
      cache.addEventListener('checking', onCacheEvent('Vérification du cache...'), false);
      cache.addEventListener('downloading', onCacheEvent('Téléchargement du cache...'), false);
      cache.addEventListener('cached', onCacheEvent('Prêt hors ligne'), false);
      cache.addEventListener('noupdate', onCacheEvent('Cache à jour'), false);
      cache.addEventListener('updateready', function () {
        setStatus('Mise à jour disponible : rechargez la page');
      }, false);
      cache.addEventListener('error', function () {
        updateOnlineState();
      }, false);
    }
  }

  if (reloadBtn) {
    reloadBtn.onclick = function () {
      window.location.reload();
    };
  }
})();
