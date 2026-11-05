#!/usr/bin/env python3
"""Génère maroc_rapport.md à partir de resultats.json (produit par test_iptv_maroc.py)."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

STATUTS = ["VALIDÉ", "ÉCHEC", "BLOQUÉ", "NON TESTÉ"]

# Hébergeurs officiels ou CDN des diffuseurs (à privilégier pour ONYX / VLC)
OFFICIELS = {
    "akamaized.net": "CDN Globecast/Akamai utilisé par la SNRT et 2M",
    "globecast.tv": "CDN Globecast (SNRT)",
    "easybroadcast.io": "CDN EasyBroadcast (SNRT / Medi1 TV)",
    "medi1tv.com": "serveurs officiels Medi1 TV",
    "snrtlive.ma": "plateforme officielle SNRT Live",
    "m24tv.ma": "serveur officiel M24 (MAP)",
    "infomaniak.com": "CDN Infomaniak utilisé par Chada TV",
    "livemediama.com": "CDN marocain (Live Media)",
}
NON_OFFICIELS = ("workers.dev", "elahmad.com", "tvanywhere.ae", "onlybest.tv", "bozztv.com")


def host_kind(url: str) -> str:
    h = urlparse(url).hostname or ""
    for k, v in OFFICIELS.items():
        if h.endswith(k):
            return "officiel"
    if any(h.endswith(k) for k in NON_OFFICIELS) or h.replace(".", "").isdigit():
        return "relais"
    return "tiers"


def main(out_dir: str) -> None:
    data = json.load(open(os.path.join(out_dir, "resultats.json"), encoding="utf-8"))
    res = data["resultats"]
    targets = data["targets"]
    by_ch = defaultdict(list)
    for r in res:
        by_ch[r["channel"]].append(r)
    cnt = Counter(r["result"] for r in res)
    ch_valid = sorted({r["channel"] for r in res if r["result"] == "VALIDÉ"})
    missing_no_source = [t for t in targets if t not in by_ch]
    missing_no_valid = [t for t in targets if t in by_ch and t not in ch_valid]
    n_entries = sum(s["entrees_maroc"] for s in data["sources"])
    restricted = any("environnement de test" in (r["reason"] or "") for r in res)

    L = []
    w = L.append
    w("# Rapport – Vérification IPTV Maroc\n")
    w(f"- Date du test : **{data['date_utc']}** (UTC) – durée totale {data['duree_totale_s']} s")
    w(f"- Outils : Python `requests`, FFmpeg (`{data['ffmpeg'] or 'absent'}`), FFprobe (`{data['ffprobe'] or 'absent'}`)")
    w("- Règle : un flux n'est **VALIDÉ** que si le manifeste est lu, un segment est téléchargé **et** "
      "FFmpeg décode réellement des images vidéo. Maximum 2 tentatives par flux.\n")

    if restricted:
        w("> ⚠️ **Limite de l'environnement de test.** Ce passage a été exécuté dans un conteneur cloud dont la "
          "sortie réseau est filtrée par une liste blanche : seuls GitHub (raw/api/gist.github.com) étaient "
          "joignables. Les hôtes de diffusion (Akamai, CloudFront, EasyBroadcast, Infomaniak, medi1tv.com, "
          "snrtlive.ma, IP directes…) ont été refusés par le proxy (`host_not_allowed`) et le conteneur n'a pas de "
          "DNS direct. Ces flux sont donc classés **NON TESTÉ** – ce n'est **pas** un verdict sur le flux. "
          "Aucun flux n'est annoncé fonctionnel sans test vidéo réussi. Relancer `test_iptv_maroc.py` depuis une "
          "machine avec accès Internet (idéalement au Maroc, à cause du géoblocage) pour obtenir les verdicts.\n")

    w("## 1. Chiffres clés\n")
    w("| Indicateur | Valeur |\n|---|---|")
    w(f"| Playlists analysées | {len(data['sources'])} ({sum(1 for s in data['sources'] if s['utilisee'])} téléchargées) |")
    w(f"| Entrées marocaines extraites (avant dédoublonnage) | {n_entries} |")
    w(f"| URL uniques testées | {len(res)} |")
    w(f"| Chaînes distinctes | {len(by_ch)} (dont {sum(1 for t in targets if t in by_ch)}/{len(targets)} chaînes cibles) |")
    for s in STATUTS:
        w(f"| Flux {s} | {cnt.get(s, 0)} |")
    w(f"| Chaînes avec au moins un flux VALIDÉ | {len(ch_valid)} |\n")

    w("## 2. Résultats par chaîne\n")
    w("| Chaîne | URL uniques | VALIDÉ | ÉCHEC | BLOQUÉ | NON TESTÉ | Sources officielles/CDN | Sources GitHub |")
    w("|---|---|---|---|---|---|---|---|")
    order = targets + sorted(k for k in by_ch if k not in targets)
    for ch in order:
        rows = by_ch.get(ch, [])
        c = Counter(r["result"] for r in rows)
        offi = sum(1 for r in rows if host_kind(r["url"]) == "officiel")
        srcs = len({s for r in rows for s in r["sources"]})
        w(f"| {ch} | {len(rows)} | {c.get('VALIDÉ', 0)} | {c.get('ÉCHEC', 0)} | {c.get('BLOQUÉ', 0)} | "
          f"{c.get('NON TESTÉ', 0)} | {offi} | {srcs} |")
    w("")

    w("## 3. Chaînes manquantes\n")
    if missing_no_source:
        w("Aucune source trouvée : " + ", ".join(missing_no_source) + ".\n")
    else:
        w("Toutes les chaînes cibles ont au moins une URL candidate dans les sources publiques.\n")
    if missing_no_valid:
        w("Sans aucun flux VALIDÉ lors de ce test : **" + ", ".join(missing_no_valid) + "**.\n")

    w("## 4. Motifs d'échec / blocage\n")
    w("| Résultat | Motif | Nombre |\n|---|---|---|")
    for (st, why), n in Counter((r["result"], (r["reason"] or "").split(" | ")[0][:110])
                                for r in res if r["result"] != "VALIDÉ").most_common():
        w(f"| {st} | {why} | {n} |")
    w("")

    w("## 5. Sources analysées\n")
    w("| Source | Statut | Entrées | Entrées marocaines | Remarque |\n|---|---|---|---|---|")
    for s in data["sources"]:
        rem = ""
        if s["utilisee"] and s["utilisee"] != s["url"]:
            rem = f"URL principale inaccessible ({s['erreur'][:90]}) – repli : {s['utilisee']}"
        elif not s["utilisee"]:
            rem = s["erreur"][:150]
        w(f"| {s['source']} | {s['statut']} | {s['entrees']} | {s['entrees_maroc']} | {rem} |")
    w("")

    w("## 6. Candidats prioritaires à tester (hébergeurs officiels / CDN des diffuseurs)\n")
    w("Classement indicatif, **non validé** : à confirmer par le test vidéo.\n")
    for ch in targets:
        rows = sorted(by_ch.get(ch, []), key=lambda r: (host_kind(r["url"]) != "officiel",
                                                         -len(r["sources"]), r["url"]))
        top = [r for r in rows if host_kind(r["url"]) == "officiel"][:3] or rows[:2]
        if not top:
            continue
        w(f"- **{ch}**")
        for r in top:
            w(f"  - `{r['url']}` — {r['result']} ({len(r['sources'])} source(s))")
    w("")

    w("## 7. Recommandations\n")
    w("1. **Relancer le test hors de ce conteneur** : `python3 test_iptv_maroc.py` (Python 3.9+, `requests`, "
      "FFmpeg). Les fichiers `maroc_valide.m3u`, `maroc_resultats.csv` et ce rapport sont régénérés.")
    w("2. **Tester depuis une IP marocaine** si possible : les flux SNRT (Globecast/EasyBroadcast) et certaines "
      "versions TNT sont souvent géobloqués hors du Maroc (403).")
    w("3. **Privilégier les CDN officiels** (Globecast/Akamai pour la SNRT et 2M Monde, EasyBroadcast, "
      "`streaming*.medi1tv.com`, `*.vedge.infomaniak.com` pour Chada, `m24tv.ma`) : ce sont les plus stables "
      "et compatibles ONYX/VLC.")
    w("4. **Éviter** les relais non officiels (`*.workers.dev`, `elahmad.com`, `tvanywhere.ae`, IP brutes, "
      "listes « KHALIL PRO ») : URL éphémères, souvent à jeton ou en violation des droits.")
    w("5. Préférer les **playlists maîtres** (`index.m3u8`, `playlist.m3u8`, `master.m3u8`) aux URL "
      "`chunklist_w123…` qui contiennent un identifiant de session et expirent.")
    w("6. Conserver les lignes `#EXTVLCOPT:http-referrer` / `http-user-agent` présentes dans les playlists : "
      "VLC les applique ; ONYX peut nécessiter de les saisir dans les réglages de la chaîne.")
    w("7. Aucun contournement de DRM, d'authentification ou de géoblocage n'a été effectué ; les flux concernés "
      "sont classés BLOQUÉ.")
    w("8. Les flux (`.mpd`) DASH sont moins bien supportés par ONYX ; privilégier la variante HLS.\n")

    w("## 8. Fichiers livrés\n")
    w("- `maroc_valide.m3u` — uniquement les flux VALIDÉS (vide si aucun flux n'a pu être validé).")
    w("- `maroc_resultats.csv` — chaîne, URL, source GitHub, statut HTTP, résultat, durée, motif d'échec.")
    w("- `maroc_candidats.m3u` — tous les flux dédoublonnés **non validés**, annotés de leur statut (à tester).")
    w("- `resultats.json` — résultats détaillés (étapes de test par flux).")
    w("- `test_iptv_maroc.py` / `generer_rapport.py` — scripts de test et de rapport, relançables.\n")

    with open(os.path.join(out_dir, "maroc_rapport.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print("rapport écrit :", os.path.join(out_dir, "maroc_rapport.md"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__)))
