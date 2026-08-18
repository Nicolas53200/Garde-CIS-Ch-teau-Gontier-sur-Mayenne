#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IGNIS - Serveur local multi-CIS
--------------------------------
1 serveur Python + 1 base SQLite par CIS.

Types prévus :
- cis_mixte       : modèle Château-Gontier / garde classique PRO-VO
- cis_mixte_24h   : gros centre mixte PRO-VO / garde 24h
- cis_volontaire  : petite caserne volontaire / astreintes

Lancement : python serveur_multi_cis.py
Accès : http://localhost:8080
"""
from flask import Flask, request, jsonify, send_from_directory, redirect
import sqlite3, json, os, socket, threading, base64, hashlib, shutil, urllib.request, urllib.error, re, xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, date, timedelta

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configs"
DATABASE_DIR = BASE_DIR / "databases"
INTERFACE_DIR = BASE_DIR / "interfaces"
IMAGES_ROOT = BASE_DIR / "images_cache"
SETTINGS_FILE = BASE_DIR / "settings.json"

# Valeurs utilisées UNIQUEMENT si settings.json est absent : le serveur crée
# alors ce fichier automatiquement avec ces valeurs au tout premier lancement
# (voir load_settings()). "CHANGEZ-MOI" est donc le code super-administrateur
# réellement actif tant que personne n'a modifié settings.json — à changer
# avant tout déploiement réel, exactement comme les autres placeholders du
# projet. default_cis vide n'est pas un problème : tant qu'IGNIS.html est
# présent à la racine, il sert de point d'entrée et default_cis n'est utilisé
# qu'en repli interne (jamais bloquant).
DEFAULT_SETTINGS = {
    "default_cis": "",
    "super_admin_code": "CHANGEZ-MOI",
    "port": 8080,
    "admin_email": "",
    # Horodatage de la dernière consultation de la liste complète des
    # feedbacks (mis à jour automatiquement par /api/feedback_all). Sert à
    # calculer le badge "X nouveaux feedbacks" affiché sur l'écran d'accueil
    # du portail, sans avoir besoin du code super-admin pour ce simple compte.
    "last_feedback_seen_at": "",
}
ALLOWED_TYPES = {"cis_mixte", "cis_mixte_24h", "cis_volontaire"}

app = Flask(__name__, static_folder=str(BASE_DIR))
_db_lock = threading.Lock()

# ── Cache vigilances, désormais par département (et non plus un cache global
# unique partagé entre tous les CIS, ce qui aurait mélangé les données de
# centres situés dans des départements différents) ───────────────────────────
_vigilance_cache = {}   # clé = f"{type}:{dep_code}" -> {"data":..., "updated_at":...}
_CACHE_TTL = 10 * 60  # 10 minutes

def _meteo_rss_url(dep_code):
    """Flux RSS MétéoAlerte pour un département donné (code INSEE à 2-3 caractères)."""
    return f"https://meteoalerte.com/france/meteoalerte_rss.php?dep={dep_code}"

def _vigicrues_api_url(dep_code):
    """API Vigicrues - tronçons pour un département donné."""
    return f"https://api.vigicrues.gouv.fr/niveaux.json/index.php?TypEntVigiCru=8&CdEntVigiCru={dep_code}"

# Table des départements français (code INSEE -> nom), utilisée pour afficher
# un libellé lisible ("Mayenne", "Loire-Atlantique"...) à partir du seul code
# stocké dans la configuration de chaque CIS (ex: "departement": "53").
DEPARTEMENTS_FR = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence",
    "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes",
    "09": "Ariège", "10": "Aube", "11": "Aude", "12": "Aveyron", "13": "Bouches-du-Rhône",
    "14": "Calvados", "15": "Cantal", "16": "Charente", "17": "Charente-Maritime",
    "18": "Cher", "19": "Corrèze", "2A": "Corse-du-Sud", "2B": "Haute-Corse",
    "21": "Côte-d'Or", "22": "Côtes-d'Armor", "23": "Creuse", "24": "Dordogne",
    "25": "Doubs", "26": "Drôme", "27": "Eure", "28": "Eure-et-Loir", "29": "Finistère",
    "30": "Gard", "31": "Haute-Garonne", "32": "Gers", "33": "Gironde", "34": "Hérault",
    "35": "Ille-et-Vilaine", "36": "Indre", "37": "Indre-et-Loire", "38": "Isère",
    "39": "Jura", "40": "Landes", "41": "Loir-et-Cher", "42": "Loire", "43": "Haute-Loire",
    "44": "Loire-Atlantique", "45": "Loiret", "46": "Lot", "47": "Lot-et-Garonne",
    "48": "Lozère", "49": "Maine-et-Loire", "50": "Manche", "51": "Marne",
    "52": "Haute-Marne", "53": "Mayenne", "54": "Meurthe-et-Moselle", "55": "Meuse",
    "56": "Morbihan", "57": "Moselle", "58": "Nièvre", "59": "Nord", "60": "Oise",
    "61": "Orne", "62": "Pas-de-Calais", "63": "Puy-de-Dôme", "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales", "67": "Bas-Rhin",
    "68": "Haut-Rhin", "69": "Rhône", "70": "Haute-Saône", "71": "Saône-et-Loire",
    "72": "Sarthe", "73": "Savoie", "74": "Haute-Savoie", "75": "Paris",
    "76": "Seine-Maritime", "77": "Seine-et-Marne", "78": "Yvelines", "79": "Deux-Sèvres",
    "80": "Somme", "81": "Tarn", "82": "Tarn-et-Garonne", "83": "Var", "84": "Vaucluse",
    "85": "Vendée", "86": "Vienne", "87": "Haute-Vienne", "88": "Vosges", "89": "Yonne",
    "90": "Territoire de Belfort", "91": "Essonne", "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise",
    "971": "Guadeloupe", "972": "Martinique", "973": "Guyane", "974": "La Réunion",
    "975": "Saint-Pierre-et-Miquelon", "976": "Mayotte",
}

def departement_nom(code):
    """Nom lisible d'un département à partir de son code INSEE (ou le code lui-même si inconnu)."""
    code = str(code or "").strip().upper()
    return DEPARTEMENTS_FR.get(code, code or "département inconnu")

RECORDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id TEXT PRIMARY KEY,
    type TEXT,
    zone TEXT,
    week_key TEXT,
    day_of_week INTEGER,
    nom TEXT,
    notes TEXT,
    data TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_type ON records(type);
CREATE INDEX IF NOT EXISTS idx_week ON records(week_key, day_of_week);
CREATE TABLE IF NOT EXISTS cis_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

TYPES_PURGEABLES = {"sous_officier", "responsable_equipe", "effectif", "depart", "infirmier", "verification", "garde_nuit", "astreinte"}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}
        except Exception:
            return DEFAULT_SETTINGS.copy()
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def slugify(txt):
    import re, unicodedata
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^a-zA-Z0-9]+", "_", txt).strip("_").lower()
    return txt or f"cis_{datetime.now().strftime('%Y%m%d%H%M%S')}"


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def list_configs():
    CONFIG_DIR.mkdir(exist_ok=True)
    items = []
    for p in sorted(CONFIG_DIR.glob("*.json")):
        try:
            cfg = json.loads(p.read_text(encoding="utf-8"))
            if cfg.get("actif", True):
                items.append(cfg)
        except Exception as e:
            print(f"Config ignoree {p.name}: {e}")
    return items


def load_config(cis_id=None):
    settings = load_settings()
    cis_id = cis_id or request.args.get("cis") or request.headers.get("X-CIS-ID") or settings.get("default_cis")
    path = CONFIG_DIR / f"{cis_id}.json"
    if not path.exists():
        raise KeyError(f"CIS inconnu: {cis_id}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("type_cis") not in ALLOWED_TYPES:
        raise ValueError(f"Type CIS invalide: {cfg.get('type_cis')}")
    return cfg


def db_path_for(cfg):
    p = Path(cfg["database"])
    return p if p.is_absolute() else BASE_DIR / p


def images_path_for(cfg):
    p = IMAGES_ROOT / cfg["id"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def init_db(path, cfg=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    conn.executescript(RECORDS_SCHEMA)
    if cfg:
        for k, v in {"cis_id": cfg["id"], "nom": cfg.get("nom"), "type_cis": cfg.get("type_cis")}.items():
            conn.execute("INSERT OR REPLACE INTO cis_meta(key,value) VALUES(?,?)", (k, json.dumps(v, ensure_ascii=False)))
    conn.commit()
    return conn


def get_db(cis_id=None):
    cfg = load_config(cis_id)
    return init_db(db_path_for(cfg), cfg)


def record_to_dict(row):
    d = dict(row)
    if d.get("data"):
        try:
            d.update(json.loads(d["data"]))
        except Exception:
            pass
    d.pop("data", None)
    if d.get("created_at"): d["createdAt"] = d.pop("created_at")
    if d.get("updated_at"): d["updatedAt"] = d.pop("updated_at")
    if d.get("week_key"): d["weekKey"] = d.pop("week_key")
    if d.get("day_of_week") is not None: d["dayOfWeek"] = d.pop("day_of_week")
    return {k: v for k, v in d.items() if v is not None}


def dict_to_columns(r):
    fixed = {"id","type","zone","weekKey","week_key","dayOfWeek","day_of_week","nom","notes","createdAt","updatedAt","created_at","updated_at","cis"}
    extra = {k: v for k, v in r.items() if k not in fixed}
    return {
        "id": r.get("id", ""),
        "type": r.get("type", ""),
        "zone": r.get("zone", ""),
        "week_key": r.get("weekKey") or r.get("week_key", ""),
        "day_of_week": r.get("dayOfWeek") if r.get("dayOfWeek") is not None else r.get("day_of_week"),
        "nom": r.get("nom", ""),
        "notes": r.get("notes", ""),
        "data": json.dumps(extra, ensure_ascii=False) if extra else "{}",
        "created_at": r.get("createdAt") or r.get("created_at") or datetime.now().isoformat(),
        "updated_at": r.get("updatedAt") or r.get("updated_at") or datetime.now().isoformat(),
    }


def extract_images_from_record(record, cfg):
    record = dict(record)
    notes = record.get("notes", "")
    if not notes or len(notes) < 1000:
        return record
    try:
        parsed = json.loads(notes)
        if not isinstance(parsed, dict):
            return record
        changed = False
        for field in ("photo", "image", "img", "video", "media"):
            val = parsed.get(field, "")
            if isinstance(val, str) and len(val) > 10000 and val.startswith("data:"):
                ext = val.split(";")[0].split("/")[-1] if ";" in val else "bin"
                key = hashlib.md5(val[:200].encode()).hexdigest()[:12]
                fname = f"img_{key}.{ext}"
                fpath = images_path_for(cfg) / fname
                b64 = val.split(",", 1)[1] if "," in val else val
                fpath.write_bytes(base64.b64decode(b64))
                parsed[field] = f"__IMG__{fname}"
                changed = True
        if changed:
            record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return record


def resolve_image_refs(record, cfg):
    record = dict(record)
    notes = record.get("notes", "")
    if not notes or "__IMG__" not in notes:
        return record
    try:
        parsed = json.loads(notes)
        if not isinstance(parsed, dict):
            return record
        for field in ("photo", "image", "img", "video", "media"):
            val = parsed.get(field, "")
            if isinstance(val, str) and val.startswith("__IMG__"):
                fname = val[7:]
                fpath = images_path_for(cfg) / fname
                if fpath.exists():
                    ext = fname.rsplit(".", 1)[-1] if "." in fname else "bin"
                    mime = {"jpg":"image/jpeg", "jpeg":"image/jpeg", "png":"image/png", "gif":"image/gif", "webp":"image/webp", "mp4":"video/mp4", "webm":"video/webm"}.get(ext, "application/octet-stream")
                    parsed[field] = f"data:{mime};base64," + base64.b64encode(fpath.read_bytes()).decode()
        record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return record


def cis_from_request_payload(payload=None):
    payload = payload or {}
    return payload.get("cis") or request.args.get("cis") or request.headers.get("X-CIS-ID") or load_settings().get("default_cis")


@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CIS-ID"
    # Interdit toute mise en cache des pages HTML (portail IGNIS.html et
    # interfaces de CIS) : ce sont des outils en évolution active, et un
    # navigateur servant une copie en cache après une mise à jour des
    # fichiers (même après redémarrage du serveur) donne l'impression
    # trompeuse qu'une modification n'a pas été appliquée alors qu'elle l'a
    # bien été côté fichiers — seul le navigateur affiche encore l'ancienne
    # version. Les réponses JSON de l'API ne sont volontairement pas
    # concernées (inutile, et ça pourrait gêner d'éventuelles optimisations).
    if response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    """Sert le portail IGNIS.html s'il existe, sinon redirige vers le CIS par défaut."""
    portail = BASE_DIR / "IGNIS.html"
    if portail.exists():
        return send_from_directory(str(BASE_DIR), "IGNIS.html")
    settings = load_settings()
    return redirect(f"/cis/{settings.get('default_cis')}")


@app.route("/IGNIS.html")
def serve_portail():
    """Sert explicitement le portail IGNIS.html."""
    portail = BASE_DIR / "IGNIS.html"
    if portail.exists():
        return send_from_directory(str(BASE_DIR), "IGNIS.html")
    return "Portail IGNIS.html introuvable à la racine du dossier.", 404


@app.route("/ignis_tour.js")
def serve_tour_js():
    """Sert le script du tour guidé + FAQ (injecté dans chaque interface CIS)."""
    tour = BASE_DIR / "ignis_tour.js"
    if tour.exists():
        resp = send_from_directory(str(BASE_DIR), "ignis_tour.js")
        resp.headers["Content-Type"] = "application/javascript; charset=utf-8"
        return resp
    return "// ignis_tour.js introuvable", 404, {"Content-Type": "application/javascript"}


# Script injecté dans le <head> : force l'identification du CIS actif depuis
# l'URL, masque l'accueil intégré, force l'affichage de l'app.
# Compatible avec plusieurs variantes d'interfaces (Volontaire, Mixte, Mixte 24h).
def build_head_patch(cfg):
    """Construit le script injecté dans le <head> pour ce CIS précis.
    Embarque le vrai nom et département (au format "Nom (Code)", ex: "Mayenne (53)")
    afin que l'interface (widget météo/vigilance, titres génériques, etc.) puisse
    s'adapter automatiquement au centre servi, sans rien coder en dur.
    config.centre_name est aussi pré-rempli avec le nom du CIS : sans cela,
    l'interface affiche son placeholder par défaut ("CIS À CONFIGURER") tant
    qu'un administrateur ne l'a pas saisi manuellement dans Paramètres.
    adminCode (= admin_code de configs/<id>.json) devient le SUPER_ADMIN_CODE
    réel de CE CIS — sans cela, tous les CIS partageraient le même mot de
    passe codé en dur dans le HTML statique (CHANGEZ-MOI)."""
    dep_code = str(cfg.get("departement") or "53").strip() or "53"
    nom_cis = cfg.get("nom") or cfg.get("id")
    centre_obj = {
        "id": cfg.get("id"),
        "nom": nom_cis,
        "departement": f"{departement_nom(dep_code)} ({dep_code})",
        "adminCode": cfg.get("admin_code"),
        "config": {"centre_name": nom_cis} if nom_cis else {},
    }
    centre_json = json.dumps(centre_obj, ensure_ascii=False)
    return """
<style>
/* Patch IGNIS multi-CIS : forcer l'état accueil masqué / app visible */
#ignis-accueil, .ignis-accueil, [data-ignis-accueil],
.ignis-home, #ignis-home, .accueil-ignis { display: none !important; }
#app { display: block !important; visibility: visible !important; opacity: 1 !important; }
</style>
<script>
/* Patch IGNIS multi-CIS — initialisation du centre actif (HEAD) */
(function(){
  var rest = (location.pathname.split('/cis/')[1] || '');
  var cisId = rest.split('/')[0].split('?')[0].split('#')[0];
  if (!cisId) return;

  // Centre injecté par le serveur pour CE CIS précis (nom + département réels)
  var centre = """ + centre_json + """;
  centre.serverUrl = location.origin;
  window.IGNIS_CENTRE_ACTIF = centre;
  window.IGNIS_CENTRES = [centre];
  window.currentCentreId = cisId;
  window.currentCentre = cisId;
  window.JSON_SERVER_URL = location.origin;

  try { localStorage.setItem('ignis_centre_id', cisId); } catch(e) {}
  try { localStorage.setItem('chg_server_url', location.origin); } catch(e) {}

  // ── Isolation des données par CIS ────────────────────────────────────────
  // Les interfaces HTML appellent l'API (/api/records, /api/vigilances_mayenne,
  // etc.) SANS jamais préciser pour quel CIS — ce n'est pas un oubli ponctuel,
  // aucune des interfaces actuelles ne le fait. Sans ce correctif, le serveur
  // retombe systématiquement sur le CIS par défaut de settings.json pour CHAQUE
  // appel, quel que soit le CIS réellement affiché à l'écran : tous les centres
  // finiraient par lire/écrire dans la même base. On intercepte donc fetch()
  // ici, une seule fois côté serveur, pour ajouter automatiquement l'en-tête
  // X-CIS-ID à tout appel vers /api/ — ainsi aucune interface (existante ou
  // future) n'a besoin d'être modifiée pour respecter l'isolation par CIS.
  var _origFetch = window.fetch;
  window.fetch = function(input, init){
    try {
      var urlStr = (typeof input === 'string') ? input : (input && input.url) || '';
      if (urlStr.indexOf('/api/') !== -1) {
        init = init || {};
        var headers = new Headers(init.headers || (typeof input === 'object' && input.headers) || {});
        if (!headers.has('X-CIS-ID')) headers.set('X-CIS-ID', cisId);
        init.headers = headers;
      }
    } catch(e) {}
    return _origFetch.call(this, input, init);
  };

  console.log('[IGNIS-PATCH] HEAD: centre actif =', cisId, centre);
})();
</script>
"""

# Script injecté avant </body> : force le switch DOM avec MutationObserver +
# retry, redirige le bouton retour vers le portail, et charge le tour guidé.
def build_body_patch(cfg):
    """Construit le script injecté avant </body> pour ce CIS précis.
    Le repli assurerCentreDansListe() embarque lui aussi le vrai nom/département
    (et non plus un centre générique vide), pour le cas où le HTML Mixte écrase
    window.IGNIS_CENTRES avec sa propre liste hardcodée. config.centre_name est
    pré-rempli pour la même raison que dans build_head_patch (voir ce commentaire).
    adminCode est repris à l'identique du head patch (voir ce commentaire) pour
    rester cohérent si ce repli venait à s'exécuter."""
    dep_code = str(cfg.get("departement") or "53").strip() or "53"
    nom_cis = cfg.get("nom") or cfg.get("id")
    centre_obj = {
        "id": cfg.get("id"),
        "nom": nom_cis,
        "departement": f"{departement_nom(dep_code)} ({dep_code})",
        "adminCode": cfg.get("admin_code"),
        "config": {"centre_name": nom_cis} if nom_cis else {},
    }
    centre_json = json.dumps(centre_obj, ensure_ascii=False)
    return """
<script src="/ignis_tour.js" defer></script>
<script>
/* Patch IGNIS multi-CIS — force affichage app + bouton retour (BODY) */
(function(){
  var cisId = (location.pathname.split('/cis/')[1] || '').split('/')[0].split('?')[0].split('#')[0];

  // Override du bouton retour accueil → portail IGNIS
  window.ignisRetourAccueil = function(){
    try { localStorage.removeItem('ignis_centre_id'); } catch(e) {}
    try { window.IGNIS_CENTRE_ACTIF = null; } catch(e) {}
    window.location.href = '/';
  };

  if (!cisId) return;

  // ⚠️ Le HTML Mixte écrase window.IGNIS_CENTRES avec sa liste hardcodée
  // (qui ne contient pas les nouveaux CIS créés via le portail). Donc avant
  // d'appeler les fonctions officielles, on s'assure que notre centre y est
  // (avec son vrai nom et département, injectés par le serveur).
  function assurerCentreDansListe(){
    var centre = """ + centre_json + """;
    centre.serverUrl = location.origin;
    if (Array.isArray(window.IGNIS_CENTRES)) {
      var found = window.IGNIS_CENTRES.find(function(c){ return c && c.id === cisId; });
      if (!found) {
        window.IGNIS_CENTRES.push(centre);
        console.log('[IGNIS-PATCH] BODY: centre ajouté à IGNIS_CENTRES (avait été écrasé)');
      }
    } else {
      window.IGNIS_CENTRES = [centre];
      console.log('[IGNIS-PATCH] BODY: IGNIS_CENTRES re-créé');
    }
    window.IGNIS_CENTRE_ACTIF = centre;
    window.currentCentreId = cisId;
    window.currentCentre = cisId;
  }

  // Forcer le bon état DOM (cacher accueil, montrer app)
  function forceEtat(){
    var accueil = document.getElementById('ignis-accueil');
    var app = document.getElementById('app');
    var changes = 0;
    if (accueil && accueil.style.display !== 'none') {
      accueil.style.setProperty('display', 'none', 'important');
      changes++;
    }
    if (app && (app.style.display === 'none' || app.style.visibility === 'hidden')) {
      app.style.setProperty('display', 'block', 'important');
      app.style.setProperty('visibility', 'visible', 'important');
      changes++;
    }
    return changes;
  }

  // Essayer d'appeler les fonctions d'init/lancement officielles
  function tryLaunch(){
    // D'abord, s'assurer que notre centre est bien dans la liste
    assurerCentreDansListe();

    var fns = ['ignisLancerCentre', 'lancerCentre', 'selectCentre', 'chargerCentre'];
    for (var i=0; i<fns.length; i++) {
      if (typeof window[fns[i]] === 'function') {
        try {
          window[fns[i]](cisId);
          console.log('[IGNIS-PATCH] BODY: appelé', fns[i] + '("' + cisId + '")');
          // Continuer à appeler init() après, au cas où la fonction officielle
          // n'a pas tout fait (et pour les cas où elle return sans init).
          if (typeof window.init === 'function') {
            try { window.init(); console.log('[IGNIS-PATCH] BODY: init() appelé'); } catch(e) {}
          }
          return true;
        } catch(e) { console.warn('[IGNIS-PATCH]', fns[i], 'a planté:', e); }
      }
    }
    if (typeof window.init === 'function') {
      try { window.init(); console.log('[IGNIS-PATCH] BODY: init() seul appelé'); return true; } catch(e) {}
    }
    return false;
  }

  function go(){
    console.log('[IGNIS-PATCH] BODY: démarrage du forçage');
    var launched = tryLaunch();
    forceEtat();

    // Retry pendant 5 secondes au cas où des scripts s'exécutent en retard
    var ticks = 0;
    var iv = setInterval(function(){
      ticks++;
      var changes = forceEtat();
      if (changes > 0) console.log('[IGNIS-PATCH] BODY: re-forçage à t+' + (ticks*100) + 'ms');
      if (ticks >= 50) clearInterval(iv); // 5 secondes
    }, 100);

    // MutationObserver : si un script modifie le style de #ignis-accueil ou #app,
    // on remet le bon état immédiatement.
    var accueil = document.getElementById('ignis-accueil');
    var app = document.getElementById('app');
    if (window.MutationObserver && (accueil || app)) {
      var obs = new MutationObserver(function(){ forceEtat(); });
      if (accueil) obs.observe(accueil, { attributes: true, attributeFilter: ['style', 'class'] });
      if (app)     obs.observe(app,     { attributes: true, attributeFilter: ['style', 'class'] });
      setTimeout(function(){ obs.disconnect(); }, 10000); // arrêt après 10s
      console.log('[IGNIS-PATCH] BODY: MutationObserver actif sur ignis-accueil et app');
    }
  }

  if (document.readyState === 'complete') go();
  else window.addEventListener('load', go);
})();
</script>
"""


@app.route("/cis/<cis_id>")
def serve_cis(cis_id):
    """Sert l'interface HTML d'un CIS, avec patch automatique des ports et du bouton retour."""
    try:
        cfg = load_config(cis_id)
    except Exception as e:
        return str(e), 404
    interface = Path(cfg.get("interface", ""))
    interface_path = interface if interface.is_absolute() else BASE_DIR / interface
    if not interface_path.exists():
        return f"Interface introuvable pour {cis_id}: {interface_path}", 404

    try:
        # Lire le HTML
        html = interface_path.read_text(encoding="utf-8")

        # 1. Patcher les ports hardcodés (8080) par le port réel du serveur
        current_port = int(load_settings().get("port", 8080))
        if current_port != 8080:
            html = html.replace("127.0.0.1:8080", f"127.0.0.1:{current_port}")
            html = html.replace("localhost:8080",  f"localhost:{current_port}")

        # 2. Injecter le HEAD_PATCH avant le PREMIER </head>
        # (le premier </head> du document est toujours le vrai ; les autres
        # éventuelles occurrences sont dans des template literals JS)
        if "</head>" in html:
            html = html.replace("</head>", build_head_patch(cfg) + "</head>", 1)

        # 3. Injecter le BODY_PATCH avant le DERNIER </body>
        # (certains HTML contiennent des </body> dans des template literals JS
        # — ex: génération d'une page d'impression. Le dernier est le vrai)
        body_patch = build_body_patch(cfg)
        idx = html.rfind("</body>")
        if idx != -1:
            html = html[:idx] + body_patch + html[idx:]
        else:
            html += body_patch

        return html, 200, {"Content-Type": "text/html; charset=utf-8"}
    except Exception as e:
        print(f"[serve_cis] Erreur patch HTML pour {cis_id}: {e} → service brut")
        return send_from_directory(str(interface_path.parent), interface_path.name)


@app.route("/interfaces/<path:path>")
def serve_interface_asset(path):
    return send_from_directory(str(INTERFACE_DIR), path)


ANIMATIONS_DIR = BASE_DIR / "animations"

@app.route("/animations/<path:path>")
def serve_animation(path):
    """Sert les fichiers d'animation (personnages animés)."""
    return send_from_directory(str(ANIMATIONS_DIR), path)


@app.route("/api/status", methods=["GET"])
def api_status():
    try:
        cfg = load_config(request.args.get("cis"))
        with get_db(cfg["id"]) as conn:
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        # Sécurité : route non authentifiée, ne jamais y exposer admin_code
        # (même principe que pour GET /api/cis, voir commentaire plus bas).
        safe_cfg = {k: v for k, v in cfg.items() if k != "admin_code"}
        return jsonify({"ok": True, "mode": "multi_cis", "cis": safe_cfg, "dbPath": str(db_path_for(cfg)), "records": count})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/verify_super_admin", methods=["POST"])
def api_verify_super_admin():
    """Vérifie un code super-administrateur sans jamais exposer le vrai code
    au client. À utiliser par les portails/UI pour valider l'accès à la
    gestion des centres — plutôt que de comparer côté client contre une
    valeur lue depuis une réponse serveur (ce qui reviendrait à divulguer
    le secret à quiconque sait observer cette réponse)."""
    payload = request.get_json(silent=True) or {}
    code = payload.get("super_admin_code") or payload.get("superAdminCode")
    settings = load_settings()
    if not code or code != settings.get("super_admin_code"):
        return jsonify({"ok": False}), 403
    return jsonify({"ok": True})


@app.route("/api/cis/<cis_id>/verify_admin", methods=["POST"])
def api_verify_cis_admin(cis_id):
    """Vérifie le code d'accès (admin_code) d'UN CIS précis, sans jamais
    exposer ce code au client — même principe que /api/verify_super_admin,
    mais à l'échelle d'un seul centre. Sert de "porte d'entrée" : un
    portail peut appeler cette route avant de naviguer vers /cis/<id>.
    Si ce CIS n'a aucun admin_code configuré (chaîne vide), on considère
    qu'aucune protection n'a été demandée pour lui et on laisse passer,
    plutôt que de rendre le centre injoignable sans raison."""
    try:
        cfg = load_config(cis_id)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 404
    payload = request.get_json(silent=True) or {}
    code = payload.get("admin_code") or payload.get("adminCode")
    code_attendu = cfg.get("admin_code")
    if not code_attendu:
        return jsonify({"ok": True})
    if not code or code != code_attendu:
        return jsonify({"ok": False}), 403
    return jsonify({"ok": True})


@app.route("/api/cis", methods=["GET"])
def api_list_cis():
    # Sécurité : on ne renvoie jamais admin_code dans cette liste publique
    # (la route n'exige aucune authentification — n'importe qui pouvant
    # joindre le serveur pourrait sinon récupérer le mot de passe admin de
    # CHAQUE CIS en un seul appel). admin_code reste lisible uniquement via
    # le fichier de config local, ou en le redéfinissant via PUT.
    safe_cis = [{k: v for k, v in cfg.items() if k != "admin_code"} for cfg in list_configs()]
    # Sécurité : on ne renvoie jamais super_admin_code ici non plus — même
    # raisonnement que pour admin_code ci-dessus. La vérification du code
    # super-admin doit passer par POST /api/verify_super_admin, jamais par
    # une comparaison côté client contre une valeur lue ici.
    settings = load_settings()
    safe_settings = {k: v for k, v in settings.items() if k != "super_admin_code"}
    return jsonify({"cis": safe_cis, "settings": safe_settings})


def _collecter_tous_feedbacks():
    """Rassemble les feedbacks de tous les CIS (fonction interne, réutilisée
    par /api/feedback_all et /api/feedback_count)."""
    tous = []
    for cfg in list_configs():
        try:
            with get_db(cfg["id"]) as conn:
                row = conn.execute(
                    "SELECT notes FROM records WHERE type='config' AND zone='feedbackList' "
                    "ORDER BY updated_at DESC LIMIT 1"
                ).fetchone()
            if not row or not row["notes"]:
                continue
            items = json.loads(row["notes"])
            for item in items:
                item = dict(item)
                item["cis_id"] = cfg["id"]
                item["cis_nom"] = cfg.get("nom") or cfg["id"]
                tous.append(item)
        except Exception as e:
            print(f"[feedback] Erreur lecture feedback pour {cfg.get('id')}: {e}")
            continue
    return tous


@app.route("/api/feedback_count", methods=["GET"])
def api_feedback_count():
    """Nombre de feedbacks 'nouveaux' (apparus depuis la dernière consultation
    complète via /api/feedback_all), pour le badge affiché sur l'écran
    d'accueil du portail. Volontairement SANS authentification : ne renvoie
    qu'un nombre, jamais le contenu des feedbacks eux-mêmes — utile pour un
    coup d'œil rapide sans avoir à entrer le code super-admin à chaque fois."""
    tous = _collecter_tous_feedbacks()
    vu_depuis = load_settings().get("last_feedback_seen_at") or ""
    nouveaux = [f for f in tous if (f.get("date") or "") > vu_depuis] if vu_depuis else tous
    return jsonify({"count": len(nouveaux), "total": len(tous)})


@app.route("/api/feedback_all", methods=["POST"])
def api_feedback_all():
    """Centralise les feedbacks de TOUS les CIS en un seul endroit, pour le
    portail (Gestion des centres). Chaque centre stocke son propre feedback
    localement (zone 'feedbackList', visible uniquement depuis SA propre
    Administration) — cette route les rassemble sans avoir besoin de se
    connecter à chacun individuellement. Protégée par le code super-admin
    puisqu'elle expose potentiellement des retours sensibles de plusieurs
    centres en une seule réponse."""
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode")
    if super_code != load_settings().get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403

    tous = _collecter_tous_feedbacks()

    # On vient de tout consulter : marquer comme "vu" maintenant, pour que
    # le badge de l'écran d'accueil reparte à zéro jusqu'au prochain nouveau
    # feedback soumis depuis n'importe quel centre.
    settings = load_settings()
    # UTC avec suffixe "Z" : même convention que new Date().toISOString() côté
    # navigateur. Comparer une heure locale serveur à une date UTC client en
    # tant que simples chaînes de caractères donnerait un résultat faux selon
    # le fuseau horaire du serveur (l'écart se voit surtout en cas de
    # comparaison à quelques heures près).
    settings["last_feedback_seen_at"] = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    save_settings(settings)

    tous.sort(key=lambda it: it.get("date") or "", reverse=True)
    return jsonify({"feedback": tous})


@app.route("/api/feedback_delete", methods=["POST"])
def api_feedback_delete():
    """Supprime UN feedback précis d'UN centre précis, depuis la vue
    centralisée du portail. On identifie l'élément par son 'date' (horodatage
    ISO créé via new Date().toISOString() côté interface — précis à la
    milliseconde, donc fiable comme identifiant pratique en l'absence d'un
    vrai id sur chaque feedback)."""
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode")
    if super_code != load_settings().get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403

    cis_id = payload.get("cis_id")
    date_cible = payload.get("date")
    if not cis_id or not date_cible:
        return jsonify({"error": "cis_id et date sont requis"}), 400

    try:
        cfg = load_config(cis_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

    with get_db(cfg["id"]) as conn:
        row = conn.execute(
            "SELECT id, notes FROM records WHERE type='config' AND zone='feedbackList' "
            "ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return jsonify({"error": "Aucun feedback trouvé pour ce centre"}), 404
        try:
            items = json.loads(row["notes"]) if row["notes"] else []
        except Exception:
            items = []
        nouveaux = [it for it in items if it.get("date") != date_cible]
        conn.execute(
            "UPDATE records SET notes = ?, updated_at = ? WHERE id = ?",
            (json.dumps(nouveaux, ensure_ascii=False), datetime.now().isoformat(), row["id"]),
        )
        conn.commit()

    return jsonify({"deleted": True})


@app.route("/api/settings", methods=["PUT"])
def api_update_settings():
    """Modifie les paramètres globaux (admin_email pour l'instant).
    Protégé par le code super-administrateur."""
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode")
    settings = load_settings()
    if super_code != settings.get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403

    # Champs modifiables (whitelist par sécurité)
    if "admin_email" in payload:
        email = str(payload.get("admin_email", "")).strip()
        settings["admin_email"] = email

    # Sauvegarder
    save_settings(settings)
    # On ne renvoie PAS le super_admin_code dans la réponse pour limiter l'exposition
    safe = {k: v for k, v in settings.items() if k != "super_admin_code"}
    return jsonify({"ok": True, "settings": safe})


@app.route("/api/cis", methods=["POST"])
def api_create_cis():
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode")
    if super_code != load_settings().get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403

    nom = payload.get("nom") or "Nouveau CIS"
    cis_id = payload.get("id") or slugify(nom)
    type_cis = payload.get("type_cis") or payload.get("typeCis") or "cis_volontaire"
    if type_cis not in ALLOWED_TYPES:
        return jsonify({"error": f"type_cis invalide. Valeurs: {sorted(ALLOWED_TYPES)}"}), 400
    cfg_file = CONFIG_DIR / f"{cis_id}.json"
    if cfg_file.exists():
        # On distingue un vrai doublon (CIS actif) d'un conflit avec un CIS
        # désactivé : "Désactiver" dans Gestion des centres ne supprime pas
        # le fichier, il masque seulement le centre du carrousel — son nom
        # reste donc "pris" tant que le fichier existe. Sans cette
        # distinction, le message "existe déjà" est trompeur pour quelqu'un
        # qui pense avoir tout supprimé.
        try:
            existing_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            existing_cfg = {}
        if existing_cfg.get("actif", True):
            return jsonify({"error": "Ce CIS existe déjà", "id": cis_id}), 409
        else:
            return jsonify({
                "error": (
                    f"Un centre désactivé porte déjà ce nom (\"{cis_id}\"). "
                    "Réactivez-le depuis Gestion des centres, ou supprimez "
                    f"définitivement configs/{cis_id}.json et "
                    f"databases/{cis_id}.db avant de recréer un centre avec ce nom."
                ),
                "id": cis_id,
                "inactive_conflict": True,
            }), 409

    interface_by_type = {
        "cis_mixte": "interfaces/Rassemblement_CIS_Mixte.html",
        "cis_mixte_24h": "interfaces/Rassemblement_CIS_Mixte_24h_BASE_A_ADAPTER.html",
        "cis_volontaire": "interfaces/Rassemblement_CIS_Volontaire.html",
    }
    cfg = {
        "id": cis_id,
        "nom": nom,
        "departement": payload.get("departement", "53"),
        "type_cis": type_cis,
        "database": f"databases/{cis_id}.db",
        "interface": payload.get("interface") or interface_by_type[type_cis],
        # Pas de valeur par défaut imposée ici : si admin_code est laissé
        # vide (volontairement, depuis le formulaire de création), le centre
        # reste sans protection — voir /api/cis/<id>/verify_admin, qui laisse
        # passer n'importe quel code (y compris vide) quand aucun code n'est
        # configuré pour ce CIS.
        "admin_code": payload.get("admin_code") or payload.get("adminCode") or "",
        "ville": payload.get("ville", ""),
        "actif": True,
        "description": payload.get("description", "")
    }
    cfg_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    init_db(db_path_for(cfg), cfg).close()
    images_path_for(cfg)
    return jsonify({"created": True, "cis": cfg}), 201


@app.route("/api/cis/<cis_id>", methods=["PUT"])
def api_update_cis(cis_id):
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode")
    if super_code != load_settings().get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403
    cfg = load_config(cis_id)
    for key in ("nom", "departement", "admin_code", "ville", "description", "interface", "actif"):
        if key in payload:
            cfg[key] = payload[key]
    if "type_cis" in payload:
        if payload["type_cis"] not in ALLOWED_TYPES:
            return jsonify({"error": "type_cis invalide"}), 400
        cfg["type_cis"] = payload["type_cis"]
    (CONFIG_DIR / f"{cis_id}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"updated": True, "cis": cfg})


@app.route("/api/cis/<cis_id>", methods=["DELETE"])
def api_delete_cis(cis_id):
    payload = request.get_json(silent=True) or {}
    super_code = payload.get("super_admin_code") or payload.get("superAdminCode") or request.args.get("super_admin_code")
    if super_code != load_settings().get("super_admin_code"):
        return jsonify({"error": "Code administrateur général invalide"}), 403
    cfg = load_config(cis_id)
    cfg["actif"] = False
    (CONFIG_DIR / f"{cis_id}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return jsonify({"deleted": True, "soft_delete": True})


@app.route("/api/records", methods=["OPTIONS"])
def options_records():
    return "", 204


@app.route("/api/records", methods=["GET"])
def get_records():
    cis_id = cis_from_request_payload()
    cfg = load_config(cis_id)
    with get_db(cfg["id"]) as conn:
        rows = conn.execute("SELECT * FROM records ORDER BY created_at ASC").fetchall()
    records = [record_to_dict(r) for r in rows]
    if request.args.get("with_images", "0") == "1":
        records = [resolve_image_refs(r, cfg) for r in records]
    return jsonify({"cis": cfg["id"], "records": records})


@app.route("/api/records", methods=["POST"])
def create_record():
    payload = request.get_json(silent=True) or {}
    cfg = load_config(cis_from_request_payload(payload))
    if not payload.get("id"):
        payload["id"] = f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    payload["createdAt"] = datetime.now().isoformat()
    payload["updatedAt"] = datetime.now().isoformat()
    payload = extract_images_from_record(payload, cfg)
    cols = dict_to_columns(payload)
    with _db_lock:
        with get_db(cfg["id"]) as conn:
            conn.execute("""INSERT OR REPLACE INTO records
                (id,type,zone,week_key,day_of_week,nom,notes,data,created_at,updated_at)
                VALUES (:id,:type,:zone,:week_key,:day_of_week,:nom,:notes,:data,:created_at,:updated_at)""", cols)
            conn.commit()
    return jsonify({"cis": cfg["id"], "id": payload["id"], "record": payload}), 201


@app.route("/api/records/<record_id>", methods=["OPTIONS"])
def options_record(record_id):
    return "", 204


@app.route("/api/records/<record_id>", methods=["PUT"])
def update_record(record_id):
    payload = request.get_json(silent=True) or {}
    cfg = load_config(cis_from_request_payload(payload))
    payload["id"] = record_id
    payload["updatedAt"] = datetime.now().isoformat()
    payload = extract_images_from_record(payload, cfg)
    cols = dict_to_columns(payload)
    with _db_lock:
        with get_db(cfg["id"]) as conn:
            r = conn.execute("""UPDATE records SET type=:type, zone=:zone, week_key=:week_key,
                day_of_week=:day_of_week, nom=:nom, notes=:notes, data=:data, updated_at=:updated_at
                WHERE id=:id""", cols)
            conn.commit()
            if r.rowcount == 0:
                return jsonify({"error": "Non trouvé", "cis": cfg["id"]}), 404
    return jsonify({"cis": cfg["id"], "id": record_id, "updated": True})


@app.route("/api/records/<record_id>", methods=["DELETE"])
def delete_record(record_id):
    cfg = load_config(cis_from_request_payload())
    with _db_lock:
        with get_db(cfg["id"]) as conn:
            r = conn.execute("DELETE FROM records WHERE id=?", (record_id,))
            conn.commit()
            if r.rowcount == 0:
                return jsonify({"error": "Non trouvé", "cis": cfg["id"]}), 404
    return jsonify({"cis": cfg["id"], "deleted": True})


def purge_old_records_for(cis_id):
    cfg = load_config(cis_id)
    today = date.today()
    purged = 0
    with get_db(cfg["id"]) as conn:
        placeholders = ",".join("?" * len(TYPES_PURGEABLES))
        rows = conn.execute(f"SELECT id, week_key, day_of_week FROM records WHERE type IN ({placeholders})", list(TYPES_PURGEABLES)).fetchall()
        ids_del = []
        for row in rows:
            try:
                monday = datetime.strptime(str(row["week_key"])[:10], "%Y-%m-%d").date()
                dow = row["day_of_week"]
                offset = 6 if dow == 0 else dow - 1
                if monday + timedelta(days=offset) < today:
                    ids_del.append(row["id"])
            except Exception:
                continue
        if ids_del:
            conn.execute(f"DELETE FROM records WHERE id IN ({','.join('?' * len(ids_del))})", ids_del)
            conn.commit()
            purged = len(ids_del)
    return purged


def run_daily_purge():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
        threading.Event().wait((next_midnight - now).total_seconds())
        for cfg in list_configs():
            try:
                purged = purge_old_records_for(cfg["id"])
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Purge {cfg['id']} : {purged} supprimé(s)")
            except Exception as e:
                print(f"Erreur purge {cfg.get('id')}: {e}")


def _fetch_url(url, timeout=8):
    """Télécharge une URL et retourne le texte, ou lève une exception."""
    req = urllib.request.Request(url, headers={"User-Agent": "IGNIS-Server/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _niveau_from_text(text):
    """Détermine le niveau de vigilance depuis un texte."""
    t = text.lower()
    if "rouge"  in t: return {"niveau": "ROUGE",  "couleur": "#dc2626", "emoji": "🔴", "rang": 4}
    if "orange" in t: return {"niveau": "ORANGE", "couleur": "#f97316", "emoji": "🟠", "rang": 3}
    if "jaune"  in t: return {"niveau": "JAUNE",  "couleur": "#facc15", "emoji": "🟡", "rang": 2}
    if "vert"   in t: return {"niveau": "VERTE",  "couleur": "#22c55e", "emoji": "🟢", "rang": 1}
    return {"niveau": "INFO", "couleur": "#38bdf8", "emoji": "ℹ️", "rang": 0}


def _fetch_meteo_departement(dep_code):
    """Récupère la vigilance météo d'un département donné depuis MétéoAlerte RSS."""
    nom = departement_nom(dep_code)
    try:
        xml_text = _fetch_url(_meteo_rss_url(dep_code))
        root = ET.fromstring(xml_text)
        items = root.findall(".//item")
        if not items:
            raise ValueError("Aucun item RSS")
        item = items[0]

        titre = (item.findtext("title") or f"Vigilance météo {nom}").strip()
        desc  = (item.findtext("description") or "").strip()
        # Nettoyer les balises HTML dans la description
        desc_clean = re.sub(r"<[^>]+>", " ", desc).strip()
        desc_clean = re.sub(r"\s+", " ", desc_clean)

        niveau = _niveau_from_text(titre + " " + desc_clean)
        est_meteo_du_jour = niveau["rang"] <= 1  # INFO = pas de vigilance → afficher météo du jour

        return {
            **niveau,
            "titre":       f"Météo du jour {nom}" if est_meteo_du_jour else titre,
            "description": desc_clean,
            "resume":      desc_clean[:200] if desc_clean else "",
            "source":      f"MétéoAlerte / {nom} {dep_code}",
            "isWeatherDay": est_meteo_du_jour,
        }
    except Exception as e:
        print(f"[Vigilances] Météo {nom} ({dep_code}) indisponible : {e}")
        return {
            "niveau": "INFO", "couleur": "#38bdf8", "emoji": "🌤️", "rang": 0,
            "titre": "Météo en chargement…",
            "description": "Service météo temporairement indisponible.",
            "source": f"MétéoAlerte / {nom} {dep_code}",
            "isWeatherDay": True,
        }


def _fetch_vigicrues_departement(dep_code):
    """Récupère les vigilances crues d'un département donné depuis l'API Vigicrues."""
    nom = departement_nom(dep_code)
    try:
        raw = _fetch_url(_vigicrues_api_url(dep_code))
        data = json.loads(raw)

        # L'API retourne une liste de tronçons avec leur niveau
        troncons = data if isinstance(data, list) else data.get("Observations", {}).get("ListeObservations", [])

        niveau_max = 0
        noms = []
        for t in troncons:
            # Selon le format de l'API vigicrues
            niv_raw = t.get("NivSituVigiCruEnt") or t.get("niveau") or t.get("NivVig") or 1
            try:
                niv = int(niv_raw)
            except (TypeError, ValueError):
                niv = 1
            if niv > niveau_max:
                niveau_max = niv
            ncrue = t.get("LbEntVigiCru") or t.get("nom") or ""
            if ncrue:
                noms.append(ncrue)

        niveaux = {
            1: {"niveau": "VERTE",  "couleur": "#22c55e", "emoji": "🟢", "rang": 1},
            2: {"niveau": "JAUNE",  "couleur": "#facc15", "emoji": "🟡", "rang": 2},
            3: {"niveau": "ORANGE", "couleur": "#f97316", "emoji": "🟠", "rang": 3},
            4: {"niveau": "ROUGE",  "couleur": "#dc2626", "emoji": "🔴", "rang": 4},
        }
        info = niveaux.get(niveau_max, {"niveau": "INFO", "couleur": "#38bdf8", "emoji": "🌊", "rang": 0})

        if niveau_max <= 1:
            desc = "Aucune alerte crue pour le moment. Surveillance normale."
        else:
            desc = f"Vigilance {info['niveau']} sur {len(noms)} tronçon(s) : {', '.join(noms[:3])}."

        return {
            **info,
            "titre":       f"Vigicrues {nom}",
            "description": desc,
            "resume":      desc[:200],
            "source":      f"Vigicrues / {nom} {dep_code}",
            "nbTroncons":  len(troncons),
        }
    except Exception as e:
        print(f"[Vigilances] Vigicrues {nom} ({dep_code}) indisponible : {e}")
        return {
            "niveau": "INFO", "couleur": "#38bdf8", "emoji": "🌊", "rang": 0,
            "titre": f"Vigicrues {nom}",
            "description": "Service Vigicrues temporairement indisponible.",
            "source": f"Vigicrues / {nom} {dep_code}",
        }


def _get_cached_dep(kind, dep_code, fetch_fn):
    """Retourne la donnée en cache pour ce (type, département) si encore fraîche, sinon rafraîchit.
    Le cache est désormais par département : deux CIS de départements différents
    n'écrasent plus mutuellement leurs données météo/vigicrues."""
    key = f"{kind}:{dep_code}"
    cache = _vigilance_cache.setdefault(key, {"data": None, "updated_at": None})
    now = datetime.now()
    if cache["data"] is None or cache["updated_at"] is None or \
       (now - cache["updated_at"]).total_seconds() > _CACHE_TTL:
        cache["data"] = fetch_fn(dep_code)
        cache["updated_at"] = now
        print(f"[Vigilances] Cache '{key}' rafraîchi à {now.strftime('%H:%M:%S')}")
    return cache["data"]


def _resolve_departement_for_request():
    """Détermine le code département à utiliser : celui du CIS demandé
    (via ?cis=, header X-CIS-ID, ou CIS par défaut), avec repli sur la Mayenne
    (53) si la config est introuvable ou ne précise pas de département."""
    try:
        cfg = load_config(cis_from_request_payload())
        return str(cfg.get("departement") or "53").strip() or "53"
    except Exception:
        return "53"


@app.route("/api/vigilances_mayenne", methods=["GET"])
def api_vigilances_mayenne():
    """
    Retourne les vigilances météo + vigicrues pour le département du CIS demandé
    (paramètre ?cis=<id> ou en-tête X-CIS-ID ; repli sur le CIS par défaut, puis
    sur la Mayenne si rien n'est résolu). Le nom de la route reste
    "vigilances_mayenne" pour compatibilité avec les interfaces existantes, mais
    le contenu retourné dépend désormais du département configuré pour le CIS.
    Cache de 10 minutes par département. Accepte ?force=1 pour le rafraîchir.
    """
    dep_code = _resolve_departement_for_request()

    if request.args.get("force") == "1":
        for kind in ("meteo", "vigicrues"):
            cache = _vigilance_cache.get(f"{kind}:{dep_code}")
            if cache:
                cache["updated_at"] = None

    meteo     = _get_cached_dep("meteo",     dep_code, _fetch_meteo_departement)
    vigicrues = _get_cached_dep("vigicrues", dep_code, _fetch_vigicrues_departement)

    return jsonify({
        "ok":              True,
        "updatedAt":       datetime.now().isoformat(),
        "departement":     dep_code,
        "departement_nom": departement_nom(dep_code),
        "meteo":           meteo,
        "vigicrues":       vigicrues,
    })


@app.route("/api/vigilances_mayenne/refresh", methods=["POST"])
def api_vigilances_refresh():
    """Force le rafraîchissement immédiat du cache vigilances pour le département du CIS demandé."""
    dep_code = _resolve_departement_for_request()
    for kind in ("meteo", "vigicrues"):
        cache = _vigilance_cache.get(f"{kind}:{dep_code}")
        if cache:
            cache["updated_at"] = None
    meteo     = _get_cached_dep("meteo",     dep_code, _fetch_meteo_departement)
    vigicrues = _get_cached_dep("vigicrues", dep_code, _fetch_vigicrues_departement)
    return jsonify({
        "ok": True,
        "departement": dep_code,
        "departement_nom": departement_nom(dep_code),
        "meteo": meteo,
        "vigicrues": vigicrues,
    })


def boot():
    CONFIG_DIR.mkdir(exist_ok=True)
    DATABASE_DIR.mkdir(exist_ok=True)
    IMAGES_ROOT.mkdir(exist_ok=True)
    settings = load_settings()
    for cfg in list_configs():
        init_db(db_path_for(cfg), cfg).close()
        images_path_for(cfg)
    return settings


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    settings = boot()
    threading.Thread(target=run_daily_purge, daemon=True).start()
    ip = get_local_ip()
    port = int(settings.get("port", 8080))
    portail_present = (BASE_DIR / "IGNIS.html").exists()
    print("=" * 62)
    print("  IGNIS - SERVEUR MULTI-CIS")
    print("=" * 62)
    print(f"  Sur ce PC      : http://localhost:{port}")
    print(f"  Réseau local   : http://{ip}:{port}")
    if portail_present:
        print(f"  Portail IGNIS  : http://localhost:{port}/   (IGNIS.html)")
    else:
        print(f"  ⚠️  IGNIS.html non trouvé à la racine — la / redirige vers le CIS par défaut")
    print(f"  CIS par défaut : {settings.get('default_cis')}")
    print(f"  Configs        : {CONFIG_DIR}")
    print(f"  Bases SQLite   : {DATABASE_DIR}")
    print("=" * 62)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
