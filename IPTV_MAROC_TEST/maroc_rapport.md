# Rapport – Vérification IPTV Maroc

- Date du test : **2026-11-05T11:34:19Z** (UTC) – durée totale 11.3 s
- Outils : Python `requests`, FFmpeg (`/usr/bin/ffmpeg`), FFprobe (`/usr/bin/ffprobe`)
- Règle : un flux n'est **VALIDÉ** que si le manifeste est lu, un segment est téléchargé **et** FFmpeg décode réellement des images vidéo. Maximum 2 tentatives par flux.

> ⚠️ **Limite de l'environnement de test.** Ce passage a été exécuté dans un conteneur cloud dont la sortie réseau est filtrée par une liste blanche : seuls GitHub (raw/api/gist.github.com) étaient joignables. Les hôtes de diffusion (Akamai, CloudFront, EasyBroadcast, Infomaniak, medi1tv.com, snrtlive.ma, IP directes…) ont été refusés par le proxy (`host_not_allowed`) et le conteneur n'a pas de DNS direct. Ces flux sont donc classés **NON TESTÉ** – ce n'est **pas** un verdict sur le flux. Aucun flux n'est annoncé fonctionnel sans test vidéo réussi. Relancer `test_iptv_maroc.py` depuis une machine avec accès Internet (idéalement au Maroc, à cause du géoblocage) pour obtenir les verdicts.

## 1. Chiffres clés

| Indicateur | Valeur |
|---|---|
| Playlists analysées | 21 (21 téléchargées) |
| Entrées marocaines extraites (avant dédoublonnage) | 277 |
| URL uniques testées | 117 |
| Chaînes distinctes | 17 (dont 13/13 chaînes cibles) |
| Flux VALIDÉ | 0 |
| Flux ÉCHEC | 0 |
| Flux BLOQUÉ | 0 |
| Flux NON TESTÉ | 117 |
| Chaînes avec au moins un flux VALIDÉ | 0 |

## 2. Résultats par chaîne

| Chaîne | URL uniques | VALIDÉ | ÉCHEC | BLOQUÉ | NON TESTÉ | Sources officielles/CDN | Sources GitHub |
|---|---|---|---|---|---|---|---|
| Laayoune TV | 6 | 0 | 0 | 0 | 6 | 5 | 9 |
| Al Aoula | 11 | 0 | 0 | 0 | 11 | 9 | 9 |
| 2M Monde | 10 | 0 | 0 | 0 | 10 | 7 | 18 |
| 2M | 6 | 0 | 0 | 0 | 6 | 0 | 15 |
| Arryadia | 14 | 0 | 0 | 0 | 14 | 11 | 16 |
| Arrabiaa / Athaqafia | 7 | 0 | 0 | 0 | 7 | 6 | 9 |
| Assadissa | 7 | 0 | 0 | 0 | 7 | 5 | 11 |
| Tamazight | 8 | 0 | 0 | 0 | 8 | 6 | 11 |
| Al Maghribia | 9 | 0 | 0 | 0 | 9 | 5 | 18 |
| Aflam TV | 1 | 0 | 0 | 0 | 1 | 0 | 1 |
| Medi1 TV | 21 | 0 | 0 | 0 | 21 | 19 | 17 |
| Chada TV | 6 | 0 | 0 | 0 | 6 | 6 | 14 |
| M24 / MAP TV News | 6 | 0 | 0 | 0 | 6 | 2 | 5 |
| Autre : StoryChannel TV | 1 | 0 | 0 | 0 | 1 | 0 | 10 |
| Autre : Télé Maroc | 2 | 0 | 0 | 0 | 2 | 0 | 3 |
| Autre : Télé Maroc+ | 1 | 0 | 0 | 0 | 1 | 1 | 1 |
| Autre : Télé Maroc++ | 1 | 0 | 0 | 0 | 1 | 1 | 1 |

## 3. Chaînes manquantes

Toutes les chaînes cibles ont au moins une URL candidate dans les sources publiques.

Sans aucun flux VALIDÉ lors de ce test : **Laayoune TV, Al Aoula, 2M Monde, 2M, Arryadia, Arrabiaa / Athaqafia, Assadissa, Tamazight, Al Maghribia, Aflam TV, Medi1 TV, Chada TV, M24 / MAP TV News**.

## 4. Motifs d'échec / blocage

| Résultat | Motif | Nombre |
|---|---|---|
| NON TESTÉ | hôte refusé par la politique réseau de l'environnement de test (proxy) | 86 |
| NON TESTÉ | réseau sortant de l'environnement de test restreint (DNS/port non autorisé) – non testable ici | 31 |

## 5. Sources analysées

| Source | Statut | Entrées | Entrées marocaines | Remarque |
|---|---|---|---|---|
| AdeelWajid/iptv_validated_list:countries/ma.m3u | 200 | 10 | 10 |  |
| iptv-org/iptv:countries/ma.m3u | 200 | 14 | 14 | URL principale inaccessible (https://iptv-org.github.io/iptv/countries/ma.m3u -> ProxyError: HTTPSConnectionPool(host=') – repli : https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ma.m3u |
| THEROCKSSS/sorted-iptv:languages/arabic.m3u | 200 | 384 | 22 |  |
| gist:hassanalami/46bf18eb7d91cc50f7591cebd6124c55 | 200 | 4 | 4 | URL principale inaccessible (https://gist.githubusercontent.com/hassanalami/46bf18eb7d91cc50f7591cebd6124c55/raw/MAROC.) – repli : https://gist.github.com/hassanalami/46bf18eb7d91cc50f7591cebd6124c55 (extrait de la page HTML) |
| iprd-org/iprd:streams/ma/ma_snrt.m3u | 200 | 15 | 0 |  |
| kilirushi/iptv:ma.m3u | 200 | 14 | 14 |  |
| kilirushi/iptv:arabic.m3u | 200 | 1416 | 12 |  |
| spookyhost1/yarr-stremio:ma.m3u | 200 | 23 | 23 |  |
| shiheb/iptv-player:Arabe/Maroc.m3u | 200 | 40 | 37 |  |
| KarimHassanein2021/iptv:MORICO.m3u | 200 | 14 | 11 |  |
| nsm-lab/iptv:channels/ma.m3u | 200 | 23 | 22 |  |
| Romaxa55/world_ip_tv:output/ma.m3u | 200 | 10 | 9 |  |
| bugsfreeweb/LiveTVCollector:Arabic | 200 | 349 | 8 |  |
| AdeelWajid/iptv_validated_list:languages/ara.m3u | 200 | 299 | 9 |  |
| igorpetrenko3690/IGOR_IPTV:channels/ma.m3u | 200 | 20 | 19 |  |
| levi-45/iptvstream:ma.m3u | 200 | 14 | 14 |  |
| iliasse-sudo/tv:ma.m3u | 200 | 18 | 17 |  |
| chadisid/list-work:mar.m3u | 200 | 8 | 8 |  |
| ahmadmk2023/free-channel:ma.m3u | 200 | 18 | 17 |  |
| Free-TV/IPTV:playlist.m3u8 | 200 | 2059 | 0 |  |
| soso366/maroc-:maroc_simple.m3u | 200 | 7 | 7 |  |

## 6. Candidats prioritaires à tester (hébergeurs officiels / CDN des diffuseurs)

Classement indicatif, **non validé** : à confirmer par le test vidéo.

- **Laayoune TV**
  - `http://cdn-hls.globecast.tv/live/ramdisk/al_aoula_laayoune/hls_snrt/index.m3u8` — NON TESTÉ (4 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/al_aoula_laayoune/hls_snrt/al_aoula_laayoune-avc1_1500000=4-mp4a_130400_qad=1.m3u8` — NON TESTÉ (4 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/al_aoula_laayoune/hls_snrt/index.m3u8` — NON TESTÉ (3 source(s))
- **Al Aoula**
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/al_aoula_inter/hls_snrt/al_aoula_inter.m3u8` — NON TESTÉ (3 source(s))
  - `http://cdn-hls.globecast.tv/live/ramdisk/al_aoula_inter/hls_snrt/index.m3u8` — NON TESTÉ (2 source(s))
  - `http://cdn-hls.globecast.tv/live/ramdisk/al_aoula_inter/hls_snrt/al_aoula_inter-avc1_1000000=3-mp4a_130400_qad=1.m3u8` — NON TESTÉ (1 source(s))
- **2M Monde**
  - `https://cdn-globecast.akamaized.net/live/eds/2m_monde/hls_video_ts_tuhawxpiemz257adfc/2m_monde.m3u8` — NON TESTÉ (9 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/2m_monde/hls_video_ts/2m_monde.m3u8` — NON TESTÉ (3 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/2m_monde/hls_video_ts/2m_monde-avc1_1500000=4-mp4a_130400_qad=1.m3u8` — NON TESTÉ (1 source(s))
- **2M**
  - `http://185.9.2.18/chid_218/index.m3u8` — NON TESTÉ (8 source(s))
  - `http://livecdnh2.tvanywhere.ae/hls/2m_maroc/04.m3u8` — NON TESTÉ (4 source(s))
- **Arryadia**
  - `http://cdn-hls.globecast.tv/live/ramdisk/arriadia/hls_snrt/index.m3u8` — NON TESTÉ (5 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/arriadia/hls_snrt/index.m3u8` — NON TESTÉ (3 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/arriadia/hls_snrt/index.m3u8` — NON TESTÉ (2 source(s))
- **Arrabiaa / Athaqafia**
  - `http://cdn-hls.globecast.tv/live/ramdisk/arrabiaa/hls_snrt/index.m3u8` — NON TESTÉ (5 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/arrabiaa/hls_snrt/index.m3u8` — NON TESTÉ (3 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/arrabiaa/hls_snrt/index.m3u8?fluxustv.m3u8` — NON TESTÉ (3 source(s))
- **Assadissa**
  - `http://cdn-hls.globecast.tv/live/ramdisk/assadissa/hls_snrt/index.m3u8` — NON TESTÉ (5 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/assadissa/hls_snrt/index.m3u8` — NON TESTÉ (3 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/assadissa/hls_snrt/index.m3u8` — NON TESTÉ (2 source(s))
- **Tamazight**
  - `http://cdn-hls.globecast.tv/live/ramdisk/tamazight_tv8_snrt/hls_snrt/index.m3u8` — NON TESTÉ (4 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/tamazight_tv8_snrt/hls_snrt/index.m3u8` — NON TESTÉ (3 source(s))
  - `https://cdnamd-hls-globecast.akamaized.net/live/ramdisk/tamazight_tv8_snrt/hls_snrt/index.m3u8` — NON TESTÉ (2 source(s))
- **Al Maghribia**
  - `http://cdn-hls.globecast.tv/live/ramdisk/al_maghribia_snrt/hls_snrt/index.m3u8` — NON TESTÉ (4 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/al_maghribia_snrt/hls_snrt/index.m3u8` — NON TESTÉ (4 source(s))
  - `http://cdnamd-hls-globecast.akamaized.net/live/ramdisk/al_maghribia_snrt/hls_snrt/al_maghribia_snrt-avc1_1500000=4-mp4a_130400_qad=1.m3u8` — NON TESTÉ (2 source(s))
- **Aflam TV**
  - `https://fl1002.bozztv.com/ga-aflamtv7/index.m3u8` — NON TESTÉ (1 source(s))
- **Medi1 TV**
  - `https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-arabic_g90v4ec/playlist.m3u8` — NON TESTÉ (8 source(s))
  - `https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-maghreb_jnbspmg/playlist.m3u8` — NON TESTÉ (6 source(s))
  - `https://cdn.live.easybroadcast.io/abr_corp/83_medi1tv-afrique_tm7tu45/playlist.m3u8` — NON TESTÉ (5 source(s))
- **Chada TV**
  - `https://edge13.vedge.infomaniak.com/livecast/ik:chadatv/manifest.m3u8` — NON TESTÉ (8 source(s))
  - `https://chadatv.vedge.infomaniak.com/livecast/chadatv/playlist.m3u8` — NON TESTÉ (4 source(s))
  - `https://edge19.vedge.infomaniak.com/livecast/ik:chadatv/playlist.m3u8` — NON TESTÉ (4 source(s))
- **M24 / MAP TV News**
  - `https://www.m24tv.ma/live/smil:OutStream1.smil/chunklist.m3u8` — NON TESTÉ (2 source(s))
  - `https://www.m24tv.ma/live/smil:OutStream1.smil/playlist.m3u8` — NON TESTÉ (1 source(s))

## 7. Recommandations

1. **Relancer le test hors de ce conteneur** : `python3 test_iptv_maroc.py` (Python 3.9+, `requests`, FFmpeg). Les fichiers `maroc_valide.m3u`, `maroc_resultats.csv` et ce rapport sont régénérés.
2. **Tester depuis une IP marocaine** si possible : les flux SNRT (Globecast/EasyBroadcast) et certaines versions TNT sont souvent géobloqués hors du Maroc (403).
3. **Privilégier les CDN officiels** (Globecast/Akamai pour la SNRT et 2M Monde, EasyBroadcast, `streaming*.medi1tv.com`, `*.vedge.infomaniak.com` pour Chada, `m24tv.ma`) : ce sont les plus stables et compatibles ONYX/VLC.
4. **Éviter** les relais non officiels (`*.workers.dev`, `elahmad.com`, `tvanywhere.ae`, IP brutes, listes « KHALIL PRO ») : URL éphémères, souvent à jeton ou en violation des droits.
5. Préférer les **playlists maîtres** (`index.m3u8`, `playlist.m3u8`, `master.m3u8`) aux URL `chunklist_w123…` qui contiennent un identifiant de session et expirent.
6. Conserver les lignes `#EXTVLCOPT:http-referrer` / `http-user-agent` présentes dans les playlists : VLC les applique ; ONYX peut nécessiter de les saisir dans les réglages de la chaîne.
7. Aucun contournement de DRM, d'authentification ou de géoblocage n'a été effectué ; les flux concernés sont classés BLOQUÉ.
8. Les flux (`.mpd`) DASH sont moins bien supportés par ONYX ; privilégier la variante HLS.

## 8. Fichiers livrés

- `maroc_valide.m3u` — uniquement les flux VALIDÉS (vide si aucun flux n'a pu être validé).
- `maroc_resultats.csv` — chaîne, URL, source GitHub, statut HTTP, résultat, durée, motif d'échec.
- `maroc_candidats.m3u` — tous les flux dédoublonnés **non validés**, annotés de leur statut (à tester).
- `resultats.json` — résultats détaillés (étapes de test par flux).
- `test_iptv_maroc.py` / `generer_rapport.py` — scripts de test et de rapport, relançables.
