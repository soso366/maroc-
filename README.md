# maroc-

Site statique hors ligne (compatible GitHub Pages) avec cache navigateur via `cache.manifest`.

## Structure

- `index.html` : page d'accueil, reliée au manifeste (`manifest="cache.manifest"`).
- `cache.manifest` : liste des fichiers à mettre en cache (HTML, JS, CSS).
- `assets/style.css` : styles responsives (marge 16 px, mode sombre).
- `assets/app.js` : script ES5 (suivi en ligne/hors ligne et état du cache).
- `maroc_simple.m3u` : liste de lecture.

## Déploiement GitHub Pages

1. Dans Settings > Pages, choisir la branche source et le dossier racine (`/`).
2. Attendre la publication, puis ouvrir l'URL du site.

## Mise à jour du cache

Le navigateur ne retélécharge les fichiers que si le contenu de `cache.manifest` change.
Après toute modification d'un fichier listé, incrémentez le commentaire de version
(`# Version 1` → `# Version 2`). Si vous ajoutez un fichier, listez-le dans `CACHE:`.

## Limites à connaître

- Le cache ne couvre que les fichiers listés explicitement : un dossier entier ne se met pas en cache automatiquement.
- Le mécanisme AppCache est obsolète dans les navigateurs modernes. Il est pris en charge par les anciens navigateurs WebKit, mais les tests n'ont pas été effectués sur un appareil réel.
- GitHub Pages doit servir `cache.manifest` avec le type `text/cache-manifest`. Ce point n'est pas garanti ; vérifiez-le avec les outils de développement du navigateur.
- Les flux en direct du fichier `.m3u` nécessitent Internet et ne sont pas mis en cache.
