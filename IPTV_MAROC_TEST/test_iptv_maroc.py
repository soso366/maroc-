#!/usr/bin/env python3
"""
Vérification IPTV Maroc
=======================

1. Télécharge les playlists sources (GitHub / gist / iptv-org).
2. Extrait les chaînes marocaines (y compris depuis les playlists arabes).
3. Dédoublonne les URL et les regroupe par chaîne.
4. Teste chaque flux (au maximum 2 tentatives) :
   - HLS : code HTTP, manifeste .m3u8, variantes, téléchargement d'un segment,
           puis décodage vidéo réel avec FFmpeg ;
   - autres formats : décodage vidéo réel avec FFmpeg.
5. Écrit maroc_valide.m3u, maroc_resultats.csv, maroc_candidats.m3u et
   resultats.json (utilisé pour générer le rapport).

Aucune protection n'est contournée : les flux DRM (SAMPLE-AES, Widevine,
PlayReady, FairPlay, ContentProtection DASH), les 401/403/451 et les jetons
expirés sont simplement classés BLOQUÉ. Seuls les en-têtes Referer /
User-Agent déclarés publiquement dans les playlists (#EXTVLCOPT) sont repris,
exactement comme le ferait VLC.

Usage :
    python3 test_iptv_maroc.py [--out DOSSIER] [--cache DOSSIER] [--workers 12]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("Le module 'requests' est requis : pip install requests")

# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
# (libellé, url principale, [urls de repli]) ; le libellé est la "source GitHub"
SOURCES = [
    ("AdeelWajid/iptv_validated_list:countries/ma.m3u",
     "https://raw.githubusercontent.com/AdeelWajid/iptv_validated_list/main/playlists/countries/ma.m3u", []),
    ("iptv-org/iptv:countries/ma.m3u",
     "https://iptv-org.github.io/iptv/countries/ma.m3u",
     ["https://raw.githubusercontent.com/iptv-org/iptv/master/streams/ma.m3u"]),
    ("THEROCKSSS/sorted-iptv:languages/arabic.m3u",
     "https://raw.githubusercontent.com/THEROCKSSS/sorted-iptv/main/playlists/languages/arabic.m3u", []),
    ("gist:hassanalami/46bf18eb7d91cc50f7591cebd6124c55",
     "https://gist.githubusercontent.com/hassanalami/46bf18eb7d91cc50f7591cebd6124c55/raw/MAROC.m3u",
     ["gisthtml:https://gist.github.com/hassanalami/46bf18eb7d91cc50f7591cebd6124c55"]),
    # --- dépôts publics supplémentaires (recherche GitHub) ---
    ("iprd-org/iprd:streams/ma/ma_snrt.m3u",
     "https://raw.githubusercontent.com/iprd-org/iprd/main/streams/ma/ma_snrt.m3u", []),
    ("kilirushi/iptv:ma.m3u", "https://raw.githubusercontent.com/kilirushi/iptv/master/ma.m3u", []),
    ("kilirushi/iptv:arabic.m3u", "https://raw.githubusercontent.com/kilirushi/iptv/master/arabic.m3u", []),
    ("spookyhost1/yarr-stremio:ma.m3u",
     "https://raw.githubusercontent.com/spookyhost1/yarr-stremio/main/src/iptv/m3u-sources/ma.m3u", []),
    ("shiheb/iptv-player:Arabe/Maroc.m3u",
     "https://raw.githubusercontent.com/shiheb/iptv-player/master/Arabe/Maroc.m3u", []),
    ("KarimHassanein2021/iptv:MORICO.m3u",
     "https://raw.githubusercontent.com/KarimHassanein2021/iptv/main/MORICO.m3u", []),
    ("nsm-lab/iptv:channels/ma.m3u", "https://raw.githubusercontent.com/nsm-lab/iptv/master/channels/ma.m3u", []),
    ("Romaxa55/world_ip_tv:output/ma.m3u",
     "https://raw.githubusercontent.com/Romaxa55/world_ip_tv/master/output/ma.m3u", []),
    ("bugsfreeweb/LiveTVCollector:Arabic",
     "https://raw.githubusercontent.com/bugsfreeweb/LiveTVCollector/main/LiveTV/Arabic/LiveTV.m3u", []),
    ("AdeelWajid/iptv_validated_list:languages/ara.m3u",
     "https://raw.githubusercontent.com/AdeelWajid/iptv_validated_list/main/playlists/languages/ara.m3u", []),
    ("igorpetrenko3690/IGOR_IPTV:channels/ma.m3u",
     "https://raw.githubusercontent.com/igorpetrenko3690/IGOR_IPTV/master/channels/ma.m3u", []),
    ("levi-45/iptvstream:ma.m3u", "https://raw.githubusercontent.com/levi-45/iptvstream/main/ma.m3u", []),
    ("iliasse-sudo/tv:ma.m3u", "https://raw.githubusercontent.com/iliasse-sudo/tv/main/ma.m3u", []),
    ("chadisid/list-work:mar.m3u", "https://raw.githubusercontent.com/chadisid/list-work/master/mar.m3u", []),
    ("ahmadmk2023/free-channel:ma.m3u", "https://raw.githubusercontent.com/ahmadmk2023/free-channel/main/ma.m3u", []),
    ("Free-TV/IPTV:playlist.m3u8", "https://raw.githubusercontent.com/Free-TV/IPTV/main/playlist.m3u8", []),
    ("soso366/maroc-:maroc_simple.m3u", "https://raw.githubusercontent.com/soso366/maroc-/main/maroc_simple.m3u",
     ["local:maroc_simple.m3u"]),
]

# Chaînes cibles : (nom canonique, regex sur le nom normalisé, "fort")
# fort=True  -> le nom suffit pour retenir l'entrée même dans une playlist arabe
# fort=False -> il faut en plus un contexte marocain (tvg-id .ma, groupe Maroc, URL SNRT…)
TARGETS = [
    ("Laayoune TV", r"laayoune|layoune|laayoun|aayoune|laâyoune", True),
    ("Al Aoula", r"\baoula\b|\bal ?oula\b|\bal ula\b|\balaoula\b", True),
    ("2M Monde", r"\b2m ?monde\b|2m_monde|\b2m\b.*\b(monde|international|inter|es)\b", True),
    ("2M", r"\b2m\b|\b2m ?maroc\b|2mmaroc", True),
    ("Arryadia", r"arryadia|arriyadia|riyadia|riadia|arriadia|ryadia", True),
    ("Arrabiaa / Athaqafia", r"arrabi|rabi3a|rabiaa|\barrabia\b|thaqafia|thakafia|takafia|attakafia|athaqafia", True),
    ("Assadissa", r"sadissa|assadisa|sadisa|assadissa", True),
    ("Tamazight", r"tamazight|amazigh|tamazirt", False),
    ("Al Maghribia", r"maghribia|maghrebia|maghribiya", True),
    ("Aflam TV", r"\baflam\b", False),
    ("Medi1 TV", r"medi ?1|medi1|medi one|medi 1tv", True),
    ("Chada TV", r"\bchada\b", True),
    ("M24 / MAP TV News", r"\bm24\b|\bma[pb] ?tv\b|maptv|ma[pb] tv news|map news", False),
]
TARGET_NAMES = [t[0] for t in TARGETS]
EXCLUDE_NAME = re.compile(r"\bradio\b|\bfm\b|rotana|\btv4\b|\bpanorama\b|shahid|\bosn\b|zee ?aflam|\bmbc\b|"
                          r"\bsyria\b|almasar|\brasd\b|\bsnrt regional\b|amazighia \d", re.I)
EXCLUDE_URL = re.compile(r"_radio|hls_snrt_radio|/radio", re.I)
# préfixes de type "AR:IRQ-", "AR:SYR-" : seuls AR:MR-/AR:MA- sont marocains
FOREIGN_PREFIX = re.compile(r"^\s*(?:\[[^\]]*\]\s*)?ar\s*:\s*(?!mr\b|ma\b)[a-z]{2,3}\s*-", re.I)
MA_URL_HINT = re.compile(r"snrt|2m\.ma|medi1|aflam|chada|m24|mapnews|\.ma/|_maroc|maroc|morocco", re.I)

UA_DEFAULT = "VLC/3.0.20 LibVLC/3.0.20"
TOKEN_HINT = re.compile(r"(token|hdnts|hdnea|expires|exp=|sig=|signature|auth|wmsAuthSign|st=|e=)", re.I)
DENY_HINT = "host_not_allowed"


def _direct_dns_ok() -> bool:
    import socket
    try:
        socket.getaddrinfo("example.com", 80)
        return True
    except OSError:
        return False


# Environnement à sortie réseau restreinte (proxy à liste blanche, pas de DNS direct) :
# les erreurs DNS / connexion y sont des artefacts de l'environnement, pas des pannes de flux.
RESTRICTED_ENV = os.environ.get("CCR_AGENT_PROXY_ENABLED") == "1" or not _direct_dns_ok()
ENV_MSG = "réseau sortant de l'environnement de test restreint (DNS/port non autorisé) – non testable ici"

CONNECT_TIMEOUT = 8
READ_TIMEOUT = 12
FFMPEG_TIMEOUT = 40
MAX_SEGMENT_BYTES = 3 * 1024 * 1024
MAX_ATTEMPTS = 2


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------
@dataclass
class Entry:
    name: str
    url: str
    source: str
    tvg_id: str = ""
    group: str = ""
    logo: str = ""
    referer: str = ""
    user_agent: str = ""
    channel: str = ""


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


def parse_m3u(text: str, source: str) -> list[Entry]:
    out: list[Entry] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.strip().lstrip("﻿")
        if not line:
            continue
        if line.startswith("#EXTINF"):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            name = line.rsplit(",", 1)[-1].strip() if "," in line else ""
            cur = {"name": name, "tvg_id": attrs.get("tvg-id", ""), "group": attrs.get("group-title", ""),
                   "logo": attrs.get("tvg-logo", ""), "referer": attrs.get("http-referrer", ""),
                   "user_agent": attrs.get("http-user-agent", ""), "country": attrs.get("tvg-country", "")}
        elif line.startswith("#EXTVLCOPT") and cur is not None:
            m = re.match(r"#EXTVLCOPT:\s*http-(referrer|referer|user-agent)\s*=\s*(.+)", line, re.I)
            if m:
                key = "user_agent" if m.group(1).lower() == "user-agent" else "referer"
                cur[key] = m.group(2).strip()
        elif line.startswith("#"):
            continue
        elif cur is not None:
            if re.match(r"^(https?|rtmp|rtsp|udp|rtp)://", line, re.I):
                url = line.split("|")[0].strip()  # syntaxe Kodi url|Referer=...
                if "|" in line:
                    for k, v in re.findall(r"([\w-]+)=([^&]+)", line.split("|", 1)[1]):
                        if k.lower() in ("referer", "referrer"):
                            cur["referer"] = v
                        elif k.lower() == "user-agent":
                            cur["user_agent"] = v
                e = Entry(cur["name"], url, source, cur["tvg_id"], cur["group"], cur["logo"],
                          cur["referer"], cur["user_agent"])
                e._country = cur.get("country", "")  # type: ignore[attr-defined]
                out.append(e)
            cur = None
    return out


def ma_context(e: Entry) -> bool:
    tid = e.tvg_id.lower()
    if re.search(r"\.ma(@|$)", tid) or tid.endswith(" ma"):
        return True
    if re.search(r"maroc|morocco|marocain|moroccan|المغرب", (e.group or ""), re.I):
        return True
    if getattr(e, "_country", "").upper().split(";")[0:1] == ["MA"]:
        return True
    if re.search(r"\b(ma|maroc|morocco)\b", norm(e.name)):
        return True
    return bool(MA_URL_HINT.search(e.url))


def foreign_tvg(e: Entry) -> bool:
    m = re.search(r"\.([a-z]{2})(@|$)", e.tvg_id.lower())
    return bool(m and m.group(1) != "ma")


def classify(e: Entry) -> str | None:
    n = norm(e.name)
    if EXCLUDE_NAME.search(n) or EXCLUDE_URL.search(e.url) or foreign_tvg(e) or FOREIGN_PREFIX.search(e.name):
        return None
    if re.search(r"2m_monde|/2m/hls", e.url, re.I):
        return "2M Monde"
    ctx = ma_context(e)
    for cname, rx, strong in TARGETS:
        if re.search(rx, n) or re.search(rx, norm(e.tvg_id)):
            if strong or ctx:
                return cname
    if ctx and re.search(r"\.ma(@|$)", e.tvg_id.lower()):
        return "Autre : " + re.sub(r"\s*\(.*?\)|\s*\[.*?\]", "", e.name).strip()
    if ctx and re.search(r"maroc|morocco", e.group or "", re.I):
        return "Autre : " + re.sub(r"\s*\(.*?\)|\s*\[.*?\]", "", e.name).strip()
    return None


def canon_url(u: str) -> str:
    p = urlparse(u.strip())
    return p._replace(scheme=p.scheme.lower(), netloc=p.netloc.lower()).geturl()


# --------------------------------------------------------------------------
# Téléchargement des sources
# --------------------------------------------------------------------------
def gist_from_html(page: str) -> str:
    lines = re.findall(r'<td[^>]*class="blob-code blob-code-inner[^"]*"[^>]*>(.*?)</td>', page, re.S)
    return "\n".join(html.unescape(re.sub(r"<[^>]+>", "", l)) for l in lines) + "\n"


def fetch_sources(cache: str, repo_dir: str) -> tuple[list[Entry], list[dict]]:
    os.makedirs(cache, exist_ok=True)
    entries: list[Entry] = []
    report = []
    sess = requests.Session()
    for label, url, fallbacks in SOURCES:
        status, used, text, err = None, None, None, ""
        for cand in [url] + fallbacks:
            try:
                if cand.startswith("local:"):
                    p = os.path.join(repo_dir, cand[6:])
                    if os.path.exists(p):
                        text, used, status = open(p, encoding="utf-8").read(), cand, "local"
                        break
                    continue
                is_html = cand.startswith("gisthtml:")
                real = cand[9:] if is_html else cand
                r = sess.get(real, timeout=(CONNECT_TIMEOUT, 30))
                status = r.status_code
                if r.ok:
                    text = gist_from_html(r.text) if is_html else r.text
                    used = real + (" (extrait de la page HTML)" if is_html else "")
                    break
                err += f"{real} -> HTTP {r.status_code}; "
            except requests.RequestException as ex:
                err += f"{cand} -> {type(ex).__name__}: {str(ex)[:120]}; "
        n_total = n_ma = 0
        if text:
            fn = re.sub(r"[^\w.-]+", "_", label)[:80] + ".m3u"
            with open(os.path.join(cache, fn), "w", encoding="utf-8") as f:
                f.write(text)
            parsed = parse_m3u(text, label)
            n_total = len(parsed)
            for e in parsed:
                c = classify(e)
                if c:
                    e.channel = c
                    entries.append(e)
                    n_ma += 1
        report.append({"source": label, "url": url, "utilisee": used or "", "statut": status,
                       "entrees": n_total, "entrees_maroc": n_ma, "erreur": err.strip()})
        print(f"[source] {label}: {'OK' if text else 'ÉCHEC'} {n_total} entrées, {n_ma} marocaines", flush=True)
    return entries, report


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------
@dataclass
class Result:
    channel: str
    name: str
    url: str
    sources: list[str]
    referer: str = ""
    user_agent: str = ""
    tvg_id: str = ""
    logo: str = ""
    http_status: str = ""
    result: str = "NON TESTÉ"
    duration: float = 0.0
    reason: str = ""
    details: str = ""
    attempts: int = 0
    steps: list[str] = field(default_factory=list)


class Stop(Exception):
    def __init__(self, result: str, reason: str, http: str = "", transient: bool = False):
        super().__init__(reason)
        self.result, self.reason, self.http, self.transient = result, reason, http, transient


def headers_for(r: Result) -> dict:
    h = {"User-Agent": r.user_agent or UA_DEFAULT, "Accept": "*/*"}
    if r.referer:
        h["Referer"] = r.referer
    return h


def http_get(sess: requests.Session, url: str, hdr: dict, limit: int) -> tuple[requests.Response, bytes]:
    try:
        resp = sess.get(url, headers=hdr, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True, allow_redirects=True)
    except requests.exceptions.ProxyError as ex:
        if "403" in str(ex) or "Tunnel connection failed" in str(ex):
            raise Stop("NON TESTÉ", "hôte refusé par la politique réseau de l'environnement de test (proxy)")
        raise Stop("ÉCHEC", f"erreur proxy : {str(ex)[:100]}", transient=True)
    except requests.exceptions.SSLError as ex:
        raise Stop("ÉCHEC", f"erreur TLS : {str(ex)[:100]}", transient=True)
    except requests.exceptions.ConnectTimeout:
        if RESTRICTED_ENV:
            raise Stop("NON TESTÉ", ENV_MSG)
        raise Stop("ÉCHEC", "délai de connexion dépassé", transient=True)
    except requests.exceptions.ReadTimeout:
        raise Stop("ÉCHEC", "délai de lecture dépassé", transient=True)
    except requests.exceptions.ConnectionError as ex:
        msg = str(ex)
        if RESTRICTED_ENV:
            raise Stop("NON TESTÉ", ENV_MSG)
        if re.search(r"Name or service not known|getaddrinfo|NameResolution|nodename", msg):
            raise Stop("ÉCHEC", "DNS : nom d'hôte introuvable")
        raise Stop("ÉCHEC", f"connexion impossible : {msg[:100]}", transient=True)
    except requests.RequestException as ex:
        raise Stop("ÉCHEC", f"erreur HTTP : {str(ex)[:100]}", transient=True)
    if resp.headers.get("x-deny-reason", "") == DENY_HINT:
        resp.close()
        raise Stop("NON TESTÉ", "hôte refusé par la politique réseau de l'environnement de test (proxy)",
                   str(resp.status_code))
    data = b""
    try:
        for chunk in resp.iter_content(65536):
            data += chunk
            if len(data) >= limit:
                break
    except requests.RequestException as ex:
        if not data:
            resp.close()
            raise Stop("ÉCHEC", f"lecture interrompue : {str(ex)[:80]}", str(resp.status_code), transient=True)
    finally:
        resp.close()
    return resp, data


def check_status(resp: requests.Response, url: str, what: str) -> None:
    s = resp.status_code
    if s < 400:
        return
    tok = bool(TOKEN_HINT.search(urlparse(url).query or "")) or "token" in url.lower()
    if s in (401, 403):
        why = "jeton expiré/invalide" if tok else "accès refusé (géoblocage ou protection anti-hotlink probable)"
        raise Stop("BLOQUÉ", f"{what} : HTTP {s} – {why}", str(s))
    if s == 451:
        raise Stop("BLOQUÉ", f"{what} : HTTP 451 – géoblocage", str(s))
    if s == 410 and tok:
        raise Stop("BLOQUÉ", f"{what} : HTTP 410 – jeton expiré", str(s))
    if s in (404, 410):
        raise Stop("ÉCHEC", f"{what} : HTTP {s} – flux introuvable", str(s))
    if s == 429:
        raise Stop("ÉCHEC", f"{what} : HTTP 429 – trop de requêtes", str(s), transient=True)
    raise Stop("ÉCHEC", f"{what} : HTTP {s}", str(s), transient=s >= 500)


DRM_RX = re.compile(r"SAMPLE-AES|com\.widevine|com\.microsoft\.playready|com\.apple\.streamingkeydelivery|"
                    r"urn:uuid:edef8ba9|urn:uuid:9a04f079|skd://", re.I)


def is_hls(url: str, ctype: str, body: bytes) -> bool:
    return body.lstrip(b"\xef\xbb\xbf \r\n\t").startswith(b"#EXTM3U") or "mpegurl" in ctype.lower() \
        or urlparse(url).path.lower().endswith(".m3u8")


def parse_master(text: str, base: str) -> list[tuple[int, str, str]]:
    variants, lines = [], text.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("#EXT-X-STREAM-INF"):
            bw = re.search(r"BANDWIDTH=(\d+)", l)
            res = re.search(r"RESOLUTION=(\d+x\d+)", l)
            for nxt in lines[i + 1:]:
                nxt = nxt.strip()
                if nxt and not nxt.startswith("#"):
                    variants.append((int(bw.group(1)) if bw else 0, urljoin(base, nxt), res.group(1) if res else ""))
                    break
    return variants


def ffmpeg_decode(target: str, r: Result, extra_input: list[str] | None = None) -> tuple[bool, str]:
    """Décode réellement la vidéo. Retourne (ok, détail)."""
    if not shutil.which("ffmpeg"):
        return False, "ffmpeg absent"
    hdr = []
    is_url = re.match(r"^\w+://", target) is not None
    if is_url and target.startswith("http"):
        hdr = ["-user_agent", r.user_agent or UA_DEFAULT, "-rw_timeout", "15000000"]
        if r.referer:
            hdr += ["-headers", f"Referer: {r.referer}\r\n"]
    cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", *(extra_input or []), *hdr, "-i", target,
           "-map", "0:v:0?", "-frames:v", "30", "-t", "8", "-f", "null", "-", "-progress", "pipe:1"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, "ffmpeg : délai dépassé"
    frames = [int(x) for x in re.findall(r"^frame=(\d+)", p.stdout, re.M)]
    nframes = max(frames) if frames else 0
    info = ""
    if shutil.which("ffprobe"):
        try:
            q = subprocess.run(["ffprobe", "-v", "error", *(extra_input or []), *hdr, "-select_streams", "v:0",
                                "-show_entries", "stream=codec_name,width,height", "-of", "csv=p=0", target],
                               capture_output=True, text=True, timeout=FFMPEG_TIMEOUT)
            info = q.stdout.strip().splitlines()[0] if q.stdout.strip() else ""
        except subprocess.TimeoutExpired:
            pass
    if nframes > 0:
        return True, f"{nframes} images vidéo décodées" + (f" ({info})" if info else "")
    err = (p.stderr.strip().splitlines() or ["aucune image vidéo décodée"])[-1][:160]
    if "0:v:0" in p.stderr or not info:
        err = "aucune piste vidéo décodable – " + err
    return False, err


def test_once(r: Result, tmpdir: str) -> None:
    sess = requests.Session()
    hdr = headers_for(r)
    url = r.url
    scheme = urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        if RESTRICTED_ENV:
            raise Stop("NON TESTÉ", ENV_MSG)
        ok, det = ffmpeg_decode(url, r)
        r.steps.append(f"ffmpeg direct ({scheme}) : {det}")
        if ok:
            r.result, r.reason, r.details = "VALIDÉ", "", det
            return
        raise Stop("ÉCHEC", f"décodage : {det}", transient=True)

    resp, body = http_get(sess, url, hdr, 512 * 1024)
    r.http_status = str(resp.status_code)
    check_status(resp, resp.url, "manifeste/flux")
    ctype = resp.headers.get("content-type", "")

    if is_hls(resp.url, ctype, body):
        text = body.decode("utf-8", "replace")
        if not text.lstrip("﻿ \r\n\t").startswith("#EXTM3U"):
            raise Stop("ÉCHEC", "manifeste .m3u8 invalide (pas d'en-tête #EXTM3U)")
        if DRM_RX.search(text):
            raise Stop("BLOQUÉ", "flux protégé par DRM (non contourné)")
        media_url, media_text = resp.url, text
        variants = parse_master(text, resp.url)
        if variants:
            r.steps.append(f"master : {len(variants)} variante(s)")
            variants.sort(key=lambda v: v[0])
            last_err = None
            for bw, vurl, res in variants[:3]:  # variante la plus légère d'abord
                try:
                    vresp, vbody = http_get(sess, vurl, hdr, 512 * 1024)
                    check_status(vresp, vresp.url, "variante")
                    vtext = vbody.decode("utf-8", "replace")
                    if not vtext.lstrip("﻿").startswith("#EXTM3U"):
                        raise Stop("ÉCHEC", "variante : manifeste invalide")
                    media_url, media_text = vresp.url, vtext
                    r.steps.append(f"variante OK {res or ''} {bw} b/s")
                    last_err = None
                    break
                except Stop as ex:
                    last_err = ex
            if last_err:
                raise last_err
        if DRM_RX.search(media_text):
            raise Stop("BLOQUÉ", "flux protégé par DRM (non contourné)")
        segs = [urljoin(media_url, l.strip()) for l in media_text.splitlines()
                if l.strip() and not l.startswith("#")]
        if not segs:
            raise Stop("ÉCHEC", "manifeste sans segment")
        # segment proche du direct (avant-dernier) – les plus récents sont parfois incomplets
        seg = segs[-2] if len(segs) >= 2 else segs[-1]
        sresp, sbody = http_get(sess, seg, hdr, MAX_SEGMENT_BYTES)
        check_status(sresp, sresp.url, "segment")
        if len(sbody) < 188:
            raise Stop("ÉCHEC", f"segment vide ou tronqué ({len(sbody)} octets)", r.http_status, transient=True)
        r.steps.append(f"segment téléchargé : {len(sbody)} octets")
        # Décodage réel : sur le manifeste média (gère AES-128 standard, fMP4/EXT-X-MAP)
        ok, det = ffmpeg_decode(media_url, r)
        if not ok:
            # repli : décodage du segment téléchargé (TS non chiffré)
            p = os.path.join(tmpdir, "seg.bin")
            with open(p, "wb") as f:
                f.write(sbody)
            ok2, det2 = ffmpeg_decode(p, r)
            if ok2:
                ok, det = True, det2 + " (segment local)"
            else:
                det = f"{det} | segment local : {det2}"
        r.steps.append(f"ffmpeg : {det}")
        if ok:
            r.result, r.reason, r.details = "VALIDÉ", "", det
            return
        raise Stop("ÉCHEC", f"erreur de décodage : {det}", r.http_status, transient=True)

    # Autres formats (MPEG-TS, MP4, DASH…)
    if b"<MPD" in body[:2048] and re.search(rb"ContentProtection", body):
        raise Stop("BLOQUÉ", "manifeste DASH protégé par DRM (non contourné)")
    if not body:
        raise Stop("ÉCHEC", "réponse vide", r.http_status, transient=True)
    ok, det = ffmpeg_decode(resp.url, r)
    r.steps.append(f"ffmpeg : {det}")
    if ok:
        r.result, r.reason, r.details = "VALIDÉ", "", det
        return
    raise Stop("ÉCHEC", f"erreur de décodage : {det}", r.http_status, transient=True)


def test_stream(r: Result) -> Result:
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            r.attempts = attempt
            r.steps.append(f"tentative {attempt}")
            try:
                test_once(r, tmp)
                break
            except Stop as ex:
                r.result, r.reason = ex.result, ex.reason
                if ex.http:
                    r.http_status = ex.http
                if not ex.transient or attempt == MAX_ATTEMPTS:
                    break
                time.sleep(1.5)
            except Exception as ex:  # robustesse
                r.result, r.reason = "ÉCHEC", f"exception inattendue : {type(ex).__name__}: {ex}"[:200]
                break
    r.duration = round(time.time() - t0, 2)
    return r


# --------------------------------------------------------------------------
# Sorties
# --------------------------------------------------------------------------
def m3u_entry(r: Result, comment: str = "") -> str:
    attrs = []
    if r.tvg_id:
        attrs.append(f'tvg-id="{r.tvg_id}"')
    if r.logo:
        attrs.append(f'tvg-logo="{r.logo}"')
    attrs.append('group-title="Maroc"')
    lines = [f'#EXTINF:-1 {" ".join(attrs)},{r.channel if not r.channel.startswith("Autre") else r.name}'
             + (f" {comment}" if comment else "")]
    if r.referer:
        lines.append(f"#EXTVLCOPT:http-referrer={r.referer}")
    if r.user_agent:
        lines.append(f"#EXTVLCOPT:http-user-agent={r.user_agent}")
    lines.append(r.url)
    return "\n".join(lines)


def channel_sort_key(name: str):
    return (TARGET_NAMES.index(name) if name in TARGET_NAMES else 999, name.lower())


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=here)
    ap.add_argument("--cache", default=os.path.join(here, "_cache"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--no-test", action="store_true", help="extraction seule, sans test réseau")
    a = ap.parse_args()

    t_start = time.time()
    entries, src_report = fetch_sources(a.cache, os.path.dirname(here))

    # Dédoublonnage par URL (le même flux peut apparaître sous plusieurs sources/noms)
    by_url: dict[str, Result] = {}
    for e in entries:
        k = canon_url(e.url)
        if k not in by_url:
            by_url[k] = Result(e.channel, e.name, e.url.strip(), [e.source], e.referer, e.user_agent,
                               e.tvg_id, e.logo)
        else:
            r = by_url[k]
            if e.source not in r.sources:
                r.sources.append(e.source)
            # les noms "cibles" priment sur "Autre"
            if r.channel.startswith("Autre") and not e.channel.startswith("Autre"):
                r.channel, r.name = e.channel, e.name
            r.referer = r.referer or e.referer
            r.user_agent = r.user_agent or e.user_agent
            r.tvg_id = r.tvg_id or e.tvg_id
            r.logo = r.logo or e.logo
    results = sorted(by_url.values(), key=lambda r: (channel_sort_key(r.channel), r.url))
    print(f"[extraction] {len(entries)} entrées marocaines, {len(results)} URL uniques, "
          f"{len({r.channel for r in results})} chaînes", flush=True)

    if not a.no_test:
        with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
            futs = {ex.submit(test_stream, r): r for r in results}
            for i, f in enumerate(cf.as_completed(futs), 1):
                r = f.result()
                print(f"[{i}/{len(results)}] {r.result:9} {r.channel:22} {r.url[:70]} {r.reason[:60]}", flush=True)
    else:
        for r in results:
            r.reason = "test non exécuté (--no-test)"

    os.makedirs(a.out, exist_ok=True)
    # CSV
    with open(os.path.join(a.out, "maroc_resultats.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chaine", "nom_source", "url", "source_github", "statut_http", "resultat", "duree_s",
                    "motif_echec", "details", "tentatives"])
        for r in results:
            w.writerow([r.channel, r.name, r.url, " | ".join(r.sources), r.http_status, r.result, r.duration,
                        r.reason, r.details, r.attempts])
    # M3U validé
    valid = [r for r in results if r.result == "VALIDÉ"]
    with open(os.path.join(a.out, "maroc_valide.m3u"), "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Flux validés (segment téléchargé + vidéo décodée par FFmpeg) – "
                f"{time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n")
        if not valid:
            f.write("# Aucun flux n'a pu être validé lors de ce test – voir maroc_rapport.md\n")
        for r in valid:
            f.write(m3u_entry(r) + "\n")
    # M3U des candidats (non validés) – utile pour un test local
    with open(os.path.join(a.out, "maroc_candidats.m3u"), "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n# ATTENTION : candidats dédoublonnés NON VALIDÉS – à tester (ne pas considérer comme "
                "fonctionnels)\n")
        for r in results:
            if r.result != "VALIDÉ":
                f.write(m3u_entry(r, f"[{r.result}]") + "\n")
    with open(os.path.join(a.out, "resultats.json"), "w", encoding="utf-8") as f:
        json.dump({"date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "duree_totale_s": round(time.time() - t_start, 1),
                   "ffmpeg": shutil.which("ffmpeg") or "", "ffprobe": shutil.which("ffprobe") or "",
                   "sources": src_report, "targets": TARGET_NAMES,
                   "resultats": [asdict(r) for r in results]}, f, ensure_ascii=False, indent=1)

    counts: dict[str, int] = {}
    for r in results:
        counts[r.result] = counts.get(r.result, 0) + 1
    print("[résumé]", json.dumps(counts, ensure_ascii=False))
    sys.path.insert(0, here)
    import generer_rapport
    generer_rapport.main(a.out)


if __name__ == "__main__":
    main()
