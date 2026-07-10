#!/usr/bin/env python3
"""
Serveur local pour l'application Garde CHG - Version Flask + SQLite
Double-cliquer sur lancer.bat pour démarrer
Accès depuis les autres PC : http://[IP-DE-CE-PC]:8080
"""

from flask import Flask, request, jsonify, send_from_directory
import sqlite3
import json
import re
import os
import socket
import threading
import time
import requests
from datetime import datetime, date, timedelta

PORT = 8080
DB_FILE = "garde_data.db"
JSON_FILE = "garde_data.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === MODE TRANSVERS ===
# Chaque PC lance son propre serveur local, mais la base est prise dans le dossier
# où se trouve ce script. Si ce dossier est sur T:, tous les postes utilisent donc
# la même base SQLite partagée.
# Option avancée : définir la variable d'environnement GARDE_CHG_DB pour forcer
# un chemin précis, ex. T:\Transvers\Garde\garde_data.db
DB_PATH = os.environ.get("GARDE_CHG_DB") or os.path.join(BASE_DIR, DB_FILE)
IMAGES_PATH = os.path.join(os.path.dirname(DB_PATH), "images_cache")

app = Flask(__name__, static_folder=BASE_DIR)
_db_lock = threading.Lock()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_db():
    # timeout + busy_timeout : évite les erreurs quand deux postes sauvegardent presque en même temps.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    # Important sur lecteur réseau : WAL est déconseillé sur partage Windows.
    # DELETE est moins moderne mais beaucoup plus compatible avec un T: partagé.
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=FULL")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS records (
            id TEXT PRIMARY KEY, type TEXT, zone TEXT,
            week_key TEXT, day_of_week INTEGER, nom TEXT,
            notes TEXT, data TEXT, created_at TEXT, updated_at TEXT)""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON records(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_week ON records(week_key, day_of_week)")
        conn.commit()
    print("Base SQLite OK")

def record_to_dict(row):
    d = dict(row)
    if d.get("data"):
        try:
            d.update(json.loads(d["data"]))
        except: pass
    del d["data"]
    if d.get("created_at"): d["createdAt"] = d.pop("created_at")
    if d.get("updated_at"): d["updatedAt"] = d.pop("updated_at")
    if d.get("week_key"):   d["weekKey"]   = d.pop("week_key")
    if d.get("day_of_week") is not None: d["dayOfWeek"] = d.pop("day_of_week")
    return {k: v for k, v in d.items() if v is not None}

def dict_to_columns(r):
    fixed = {"id","type","zone","weekKey","week_key","dayOfWeek","day_of_week","nom","notes","createdAt","updatedAt","created_at","updated_at"}
    extra = {k: v for k, v in r.items() if k not in fixed}
    return {
        "id": r.get("id",""), "type": r.get("type",""), "zone": r.get("zone",""),
        "week_key": r.get("weekKey") or r.get("week_key",""),
        "day_of_week": r.get("dayOfWeek") or r.get("day_of_week"),
        "nom": r.get("nom",""), "notes": r.get("notes",""),
        "data": json.dumps(extra, ensure_ascii=False) if extra else "{}",
        "created_at": r.get("createdAt") or r.get("created_at") or datetime.now().isoformat(),
        "updated_at": r.get("updatedAt") or r.get("updated_at") or datetime.now().isoformat(),
    }

def migrate_json_to_sqlite():
    json_path = os.path.join(os.path.dirname(DB_PATH), JSON_FILE)
    if not os.path.exists(json_path):
        json_path = os.path.join(BASE_DIR, JSON_FILE)
    if not os.path.exists(json_path): return 0
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if count > 0:
            print(f"SQLite deja peuple ({count} enregistrements) - migration ignoree")
            return count
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("records", [])
        with get_db() as conn:
            for i, record in enumerate(records):
                if not record.get("id"):
                    record["id"] = f"rec_mig_{i}"
                cols = dict_to_columns(record)
                conn.execute("INSERT OR REPLACE INTO records (id,type,zone,week_key,day_of_week,nom,notes,data,created_at,updated_at) VALUES (:id,:type,:zone,:week_key,:day_of_week,:nom,:notes,:data,:created_at,:updated_at)", cols)
            conn.commit()
        os.rename(json_path, json_path + ".migrated.bak")
        print(f"Migration JSON->SQLite : {len(records)} enregistrements OK")
        return len(records)
    except Exception as e:
        print(f"Erreur migration : {e}")
        return 0

TYPES_PURGEABLES = {"sous_officier","effectif","depart","infirmier","verification","garde_nuit","astreinte"}

def purge_old_records():
    today = date.today()
    purged = 0
    with get_db() as conn:
        rows = conn.execute("SELECT id, week_key, day_of_week FROM records WHERE type IN ({})".format(",".join("?"*len(TYPES_PURGEABLES))), list(TYPES_PURGEABLES)).fetchall()
        ids_del = []
        for row in rows:
            try:
                monday = datetime.strptime(str(row["week_key"])[:10], "%Y-%m-%d").date()
                dow = row["day_of_week"]
                offset = 6 if dow == 0 else dow - 1
                if monday + timedelta(days=offset) < today:
                    ids_del.append(row["id"])
            except: continue
        if ids_del:
            conn.execute("DELETE FROM records WHERE id IN ({})".format(",".join("?"*len(ids_del))), ids_del)
            conn.commit()
            purged = len(ids_del)
    return purged

def run_daily_purge():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
        threading.Event().wait((next_midnight - now).total_seconds())
        try:
            purged = purge_old_records()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Purge : {purged} supprime(s)")
        except Exception as e:
            print(f"Erreur purge : {e}")

IMAGES_DIR = "images_cache"

def ensure_images_dir():
    path = IMAGES_PATH
    if not os.path.exists(path): os.makedirs(path, exist_ok=True)
    return path

def extract_images_from_record(record):
    record = dict(record)
    notes = record.get("notes", "")
    if not notes or len(notes) < 1000: return record
    try:
        parsed = json.loads(notes)
        if not isinstance(parsed, dict): return record
        changed = False
        for field in ("photo","image","img","video","media"):
            val = parsed.get(field, "")
            if isinstance(val, str) and len(val) > 10000 and val.startswith("data:"):
                import hashlib, base64
                ext = val.split(";")[0].split("/")[-1] if ";" in val else "bin"
                key = hashlib.md5(val[:200].encode()).hexdigest()[:12]
                fname = f"img_{key}.{ext}"
                fpath = os.path.join(IMAGES_PATH, fname)
                try:
                    b64 = val.split(",",1)[1] if "," in val else val
                    with open(fpath,"wb") as imgf: imgf.write(base64.b64decode(b64))
                    parsed[field] = f"__IMG__{fname}"
                    changed = True
                except: pass
        if changed: record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except: pass
    return record

def resolve_image_refs(record):
    import base64
    record = dict(record)
    notes = record.get("notes","")
    if not notes or "__IMG__" not in notes: return record
    try:
        parsed = json.loads(notes)
        if not isinstance(parsed, dict): return record
        for field in ("photo","image","img","video","media"):
            val = parsed.get(field,"")
            if isinstance(val, str) and val.startswith("__IMG__"):
                fname = val[7:]
                fpath = os.path.join(IMAGES_PATH, fname)
                if os.path.exists(fpath):
                    ext = fname.rsplit(".",1)[-1] if "." in fname else "bin"
                    mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","gif":"image/gif","webp":"image/webp","mp4":"video/mp4","webm":"video/webm"}.get(ext,"application/octet-stream")
                    with open(fpath,"rb") as imgf: b64 = base64.b64encode(imgf.read()).decode()
                    parsed[field] = f"data:{mime};base64,{b64}"
        record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except: pass
    return record



# === VIGILANCES MAYENNE : météo + vigicrues ===
MAYENNE_LAT = 47.83
MAYENNE_LON = -0.70

def _vig_level_info(text):
    t = (text or "").lower()
    if "rouge" in t:
        return {"niveau": "ROUGE", "couleur": "rouge", "rang": 4}
    if "orange" in t:
        return {"niveau": "ORANGE", "couleur": "orange", "rang": 3}
    if "jaune" in t:
        return {"niveau": "JAUNE", "couleur": "jaune", "rang": 2}
    if "vert" in t or "verte" in t:
        return {"niveau": "VERTE", "couleur": "vert", "rang": 1}
    return {"niveau": "INFO", "couleur": "bleu", "rang": 0}

def _vig_plain(text, limit=240):
    txt = re.sub(r"<[^>]+>", " ", text or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]

# === CACHE MÉTÉO CÔTÉ SERVEUR (évite les appels répétés aux APIs externes) ===
_meteo_cache = {"data": None, "ts": 0}
_vigicrues_cache = {"data": None, "ts": 0}
METEO_CACHE_TTL = 15 * 60   # 15 minutes : on ne rappelle Open-Meteo que toutes les 15 min
VIGICRUES_CACHE_TTL = 15 * 60

def get_weather_day_mayenne():
    """Météo du jour via Open-Meteo, sans clé API. Cache 15 min."""
    import time
    now = time.time()
    # Retourner le cache si encore frais
    if _meteo_cache["data"] and (now - _meteo_cache["ts"]) < METEO_CACHE_TTL:
        return _meteo_cache["data"]
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={MAYENNE_LAT}&longitude={MAYENNE_LON}"
            "&current=temperature_2m,weather_code,wind_speed_10m"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
            "&timezone=Europe%2FParis"
        )
        r = requests.get(url, timeout=5)   # timeout réduit à 5s
        r.raise_for_status()
        data = r.json()
        cur = data.get("current", {})
        daily = data.get("daily", {})
        temp = cur.get("temperature_2m", "?")
        vent = cur.get("wind_speed_10m", "?")
        tmin = (daily.get("temperature_2m_min") or ["?"])[0]
        tmax = (daily.get("temperature_2m_max") or ["?"])[0]
        pluie = (daily.get("precipitation_sum") or [0])[0]
        result = {
            "niveau": "INFO",
            "titre": "Météo du jour Mayenne",
            "description": f"{temp}°C actuellement. Mini {tmin}°C / Maxi {tmax}°C. Pluie prévue : {pluie} mm. Vent : {vent} km/h.",
            "source": "Open-Meteo"
        }
        # Mettre en cache uniquement si succès
        _meteo_cache["data"] = result
        _meteo_cache["ts"] = now
        return result
    except Exception as e:
        # En cas d'échec, retourner le cache expiré s'il existe (mieux que rien)
        if _meteo_cache["data"]:
            cached = dict(_meteo_cache["data"])
            cached["description"] += " (données en cache)"
            return cached
        return {
            "niveau": "INFO",
            "titre": "Météo du jour Mayenne",
            "description": "Météo temporairement indisponible. Nouvelle tentative dans quelques minutes.",
            "source": "Open-Meteo"
        }

def get_meteo_vigilance_or_weather_mayenne():
    """
    Essaie une vigilance météo Mayenne.
    Si pas d'alerte exploitable, affiche la météo du jour.
    """
    try:
        rss_url = "https://meteoalerte.com/france/meteoalerte_rss.php?dep=53"
        r = requests.get(rss_url, timeout=5, headers={"User-Agent": "IGNIS-CIS/1.0"})
        r.raise_for_status()
        txt = _vig_plain(r.text, 700)
        level = _vig_level_info(txt)

        # S'il n'y a pas d'alerte, on affiche la météo du jour comme demandé.
        if level["rang"] <= 1:
            return get_weather_day_mayenne()

        return {
            "niveau": level["niveau"],
            "titre": "Vigilance météo Mayenne",
            "description": _vig_plain(txt, 240),
            "source": "MétéoAlerte / Mayenne 53"
        }
    except Exception:
        return get_weather_day_mayenne()

def get_vigicrues_mayenne():
    """
    Vigicrues / crues Mayenne. Cache 15 min.
    La source Hub'Eau peut refuser certaines requêtes depuis certains réseaux.
    Dans ce cas on ne renvoie pas l'erreur technique à l'écran TV : on affiche un état INFO propre.
    """
    import time
    now = time.time()
    if _vigicrues_cache["data"] and (now - _vigicrues_cache["ts"]) < VIGICRUES_CACHE_TTL:
        return _vigicrues_cache["data"]
    try:
        # Requête légère pour tester l'accès au service.
        url = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/referentiel/stations?code_departement=53&size=1"
        r = requests.get(url, timeout=5, headers={
            "User-Agent": "Mozilla/5.0 IGNIS-CIS/1.0",
            "Accept": "application/json"
        })
        if r.status_code == 403:
            raise Exception("Accès Hub'Eau refusé")
        r.raise_for_status()
        result = {
            "niveau": "INFO",
            "titre": "Vigicrues Mayenne",
            "description": "Aucune alerte crue affichée automatiquement pour le moment.",
            "source": "Hub'Eau / Vigicrues"
        }
        _vigicrues_cache["data"] = result
        _vigicrues_cache["ts"] = now
        return result
    except Exception:
        if _vigicrues_cache["data"]:
            return _vigicrues_cache["data"]
        return {
            "niveau": "INFO",
            "titre": "Vigicrues Mayenne",
            "description": "Aucune alerte crue affichée automatiquement pour le moment.",
            "source": "Vigicrues"
        }

@app.route("/api/vigilances_mayenne", methods=["GET"])
def api_vigilances_mayenne():
    return jsonify({
        "updatedAt": datetime.now().isoformat(timespec="minutes"),
        "department": "Mayenne",
        "code": "53",
        "meteo": get_meteo_vigilance_or_weather_mayenne(),
        "vigicrues": get_vigicrues_mayenne()
    })


@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/status", methods=["GET"])
def api_status():
    try:
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        return jsonify({
            "ok": True,
            "mode": "transvers_local",
            "dbPath": DB_PATH,
            "records": count,
            "baseDir": BASE_DIR
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "dbPath": DB_PATH}), 500

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path):
    if not path: path = "Rassemblement_Garde_CHG.html"
    file_path = os.path.join(BASE_DIR, path)
    if os.path.isfile(file_path): return send_from_directory(BASE_DIR, path)
    return "Fichier non trouve", 404

@app.route("/api/records", methods=["OPTIONS"])
def options_records(): return "", 204

@app.route("/api/records", methods=["GET"])
def get_records():
    with_images = request.args.get("with_images","0") == "1"
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM records ORDER BY created_at ASC").fetchall()
    records = [record_to_dict(r) for r in rows]
    if with_images: records = [resolve_image_refs(r) for r in records]
    return jsonify({"records": records})

@app.route("/api/records", methods=["POST"])
def create_record():
    payload = request.get_json(silent=True) or {}
    if not payload.get("id"): payload["id"] = f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    payload["createdAt"] = datetime.now().isoformat()
    payload["updatedAt"] = datetime.now().isoformat()
    payload = extract_images_from_record(payload)
    cols = dict_to_columns(payload)
    with _db_lock:
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO records (id,type,zone,week_key,day_of_week,nom,notes,data,created_at,updated_at) VALUES (:id,:type,:zone,:week_key,:day_of_week,:nom,:notes,:data,:created_at,:updated_at)", cols)
            conn.commit()
    return jsonify({"id": payload["id"], "record": payload}), 201

@app.route("/api/records/<record_id>", methods=["OPTIONS"])
def options_record(record_id): return "", 204

@app.route("/api/records/<record_id>", methods=["PUT"])
def update_record(record_id):
    payload = request.get_json(silent=True) or {}
    payload["id"] = record_id
    payload["updatedAt"] = datetime.now().isoformat()
    payload = extract_images_from_record(payload)
    cols = dict_to_columns(payload)
    with _db_lock:
        with get_db() as conn:
            r = conn.execute("UPDATE records SET type=:type,zone=:zone,week_key=:week_key,day_of_week=:day_of_week,nom=:nom,notes=:notes,data=:data,updated_at=:updated_at WHERE id=:id", cols)
            conn.commit()
            if r.rowcount == 0: return jsonify({"error": "Non trouve"}), 404
    return jsonify({"id": record_id, "updated": True})

@app.route("/api/records/<record_id>", methods=["DELETE"])
def delete_record(record_id):
    with _db_lock:
        with get_db() as conn:
            r = conn.execute("DELETE FROM records WHERE id=?", (record_id,))
            conn.commit()
            if r.rowcount == 0: return jsonify({"error": "Non trouve"}), 404
    return jsonify({"deleted": True})

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    ip = get_local_ip()
    ensure_images_dir()
    init_db()
    migrate_json_to_sqlite()
    purged = purge_old_records()
    if purged > 0: print(f"Purge demarrage : {purged} supprime(s)")
    threading.Thread(target=run_daily_purge, daemon=True).start()
    print("=" * 55)
    print("  SERVEUR GARDE CHG (Flask + SQLite)")
    print("=" * 55)
    print(f"  Sur ce PC         : http://localhost:{PORT}")
    print(f"  Adresse locale    : http://127.0.0.1:{PORT}")
    print(f"  Base SQLite       : {DB_PATH}")
    print(f"  Images cache      : {IMAGES_PATH}")
    print("  Mode Transvers    : 1 serveur local par PC, base partagee sur T:")
    print("=" * 55)
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
