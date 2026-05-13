#!/usr/bin/env python3
"""
Serveur local pour l'application Garde CHG - Version Flask
Double-cliquer sur lancer.bat pour démarrer
Accès depuis les autres PC : http://[IP-DE-CE-PC]:80
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
import json
import os
import socket
import threading
import time
from datetime import datetime, date, timedelta

PORT = 8080
DATA_FILE = "garde_data.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR)

# Verrou threading local
_file_lock = threading.Lock()

# Types de données purgeables
GARDE_TYPES_PURGEABLES = {
    "sous_officier", "effectif", "depart", "infirmier",
    "verification", "garde_nuit", "astreinte"
}

# ── Utilitaires réseau ────────────────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# ── Lecture / écriture JSON ───────────────────────────────────────────────────

def load_data():
    path = os.path.join(BASE_DIR, DATA_FILE)
    if os.path.exists(path):
        for _ in range(10):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                mtime = os.path.getmtime(path)
                data = json.loads(content)
                data['__mtime'] = mtime
                return data
            except (json.JSONDecodeError, IOError):
                time.sleep(0.1)
        return {}
    return {}

def save_data(data):
    path = os.path.join(BASE_DIR, DATA_FILE)
    lock_path = path + ".lock"
    tmp_path = path + ".tmp"
    data = {k: v for k, v in data.items() if k != '__mtime'}
    with _file_lock:
        waited = 0
        while os.path.exists(lock_path) and waited < 5.0:
            time.sleep(0.1)
            waited += 0.1
        try:
            with open(lock_path, 'w') as lf:
                lf.write(str(os.getpid()))
        except:
            pass
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            os.replace(tmp_path, path)
        finally:
            try: os.remove(lock_path)
            except: pass

def safe_modify(modify_fn):
    path = os.path.join(BASE_DIR, DATA_FILE)
    for attempt in range(5):
        data = load_data()
        mtime_before = data.pop('__mtime', 0)
        modified_data = modify_fn(data)
        if modified_data is None:
            return data
        try:
            mtime_after = os.path.getmtime(path)
        except:
            mtime_after = 0
        if abs(mtime_after - mtime_before) < 0.5:
            save_data(modified_data)
            return modified_data
        time.sleep(0.1 * (attempt + 1))
    save_data(modified_data)
    return modified_data

def save_data_backup(data):
    path = os.path.join(BASE_DIR, DATA_FILE)
    backup_path = path + ".bak"
    if os.path.exists(path):
        import shutil
        shutil.copy2(path, backup_path)
    save_data(data)

# ── Purge ─────────────────────────────────────────────────────────────────────

def parse_week_key(week_key):
    if not week_key:
        return None
    try:
        date_part = str(week_key).strip()[:10]
        return datetime.strptime(date_part, "%Y-%m-%d").date()
    except:
        return None

def get_record_date(record):
    week_key = record.get("weekKey") or record.get("week_key")
    day_of_week = record.get("dayOfWeek") or record.get("day_of_week")
    monday = parse_week_key(week_key)
    if monday is None:
        return None
    try:
        dow = int(day_of_week)
    except (TypeError, ValueError):
        return None
    if dow == 0:
        offset = 6
    else:
        offset = dow - 1
    return monday + timedelta(days=offset)

def purge_old_garde_records(data):
    records = data.get("records", [])
    today = date.today()
    kept = []
    purged = 0
    for record in records:
        record_type = record.get("type", "")
        if record_type not in GARDE_TYPES_PURGEABLES:
            kept.append(record)
            continue
        record_date = get_record_date(record)
        if record_date is None:
            kept.append(record)
            continue
        if record_date < today:
            purged += 1
        else:
            kept.append(record)
    data["records"] = kept
    return data, purged

# ── Images ────────────────────────────────────────────────────────────────────

IMAGES_DIR = "images_cache"

def ensure_images_dir():
    path = os.path.join(BASE_DIR, IMAGES_DIR)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def extract_images_from_record(record):
    import re
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
                import hashlib
                ext = val.split(";")[0].split("/")[-1] if ";" in val else "bin"
                key = hashlib.md5(val[:200].encode()).hexdigest()[:12]
                fname = f"img_{key}.{ext}"
                fpath = os.path.join(BASE_DIR, IMAGES_DIR, fname)
                try:
                    import base64
                    b64 = val.split(",", 1)[1] if "," in val else val
                    with open(fpath, "wb") as imgf:
                        imgf.write(base64.b64decode(b64))
                    parsed[field] = f"__IMG__{fname}"
                    changed = True
                except Exception:
                    pass
        if changed:
            record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return record

def migrate_existing_images():
    migrated = 0
    data = load_data()
    records = data.get("records", [])
    changed = False
    for i, r in enumerate(records):
        new_r = extract_images_from_record(r)
        if new_r.get("notes") != r.get("notes"):
            records[i] = new_r
            changed = True
            migrated += 1
    if changed:
        data["records"] = records
        save_data(data)
    return migrated

def resolve_image_refs(record):
    import re, base64
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
                fpath = os.path.join(BASE_DIR, IMAGES_DIR, fname)
                if os.path.exists(fpath):
                    ext = fname.rsplit(".", 1)[-1] if "." in fname else "bin"
                    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "png": "image/png", "gif": "image/gif",
                            "webp": "image/webp", "mp4": "video/mp4",
                            "webm": "video/webm"}.get(ext, "application/octet-stream")
                    with open(fpath, "rb") as imgf:
                        b64 = base64.b64encode(imgf.read()).decode()
                    parsed[field] = f"data:{mime};base64,{b64}"
        record["notes"] = json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return record

# ── Routes Flask ──────────────────────────────────────────────────────────────

def cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

@app.after_request
def after_request(response):
    return cors_headers(response)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if not path:
        path = 'Rassemblement_Garde_CHG.html'
    file_path = os.path.join(BASE_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(BASE_DIR, path)
    return "Fichier non trouvé", 404

@app.route('/api/records', methods=['GET', 'OPTIONS'])
def get_records():
    if request.method == 'OPTIONS':
        return '', 204
    with_images = request.args.get('with_images', '0') == '1'
    data = load_data()
    records = data.get("records", [])
    if with_images:
        records = [resolve_image_refs(r) for r in records]
    return jsonify({"records": records})

@app.route('/api/records', methods=['POST'])
def create_record():
    payload = request.get_json(silent=True) or {}
    new_id = payload.get("id") or f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    payload["createdAt"] = datetime.now().isoformat()
    payload["updatedAt"] = datetime.now().isoformat()

    def do_create(data):
        records = data.get("records", [])
        existing_ids = {r.get("id", "") for r in records}
        rid = new_id
        while rid in existing_ids:
            rid = f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        payload["id"] = rid
        record_to_save = extract_images_from_record(payload)
        records.append(record_to_save)
        data["records"] = records
        return data

    safe_modify(do_create)
    return jsonify({"id": new_id, "record": payload}), 201

@app.route('/api/records/<record_id>', methods=['PUT'])
def update_record(record_id):
    payload = request.get_json(silent=True) or {}
    payload["id"] = record_id
    payload["updatedAt"] = datetime.now().isoformat()
    payload = extract_images_from_record(payload)

    def do_update(data):
        records = data.get("records", [])
        for i, r in enumerate(records):
            if r.get("id") == record_id:
                records[i] = payload
                data["records"] = records
                return data
        return None

    result = safe_modify(do_update)
    if result is not None:
        return jsonify({"id": record_id, "updated": True})
    return jsonify({"error": "Non trouvé"}), 404

@app.route('/api/records/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    def do_delete(data):
        records = data.get("records", [])
        new_records = [r for r in records if r.get("id") != record_id]
        if len(new_records) < len(records):
            data["records"] = new_records
            return data
        return None

    result = safe_modify(do_delete)
    if result is not None:
        return jsonify({"deleted": True})
    return jsonify({"error": "Non trouvé"}), 404

@app.route('/api/records/<record_id>', methods=['OPTIONS'])
def options_record(record_id):
    return '', 204

# ── Purge quotidienne ─────────────────────────────────────────────────────────

def run_daily_purge():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
        wait_seconds = (next_midnight - now).total_seconds()
        print(f"⏰  Prochaine purge automatique : {next_midnight.strftime('%d/%m/%Y à %H:%M:%S')}")
        threading.Event().wait(wait_seconds)
        try:
            data = load_data()
            data, purged_count = purge_old_garde_records(data)
            if purged_count > 0:
                save_data(data)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🗑️  Purge minuit : {purged_count} enregistrement(s) supprimé(s)")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Purge minuit : rien à supprimer")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️  Erreur purge : {e}")

# ── Démarrage ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(BASE_DIR)
    ip = get_local_ip()

    data_path = os.path.join(BASE_DIR, DATA_FILE)
    if not os.path.exists(data_path):
        save_data({"records": [], "version": "1.0", "createdAt": datetime.now().isoformat()})
        print(f"✓ Fichier de données créé : {DATA_FILE}")

    ensure_images_dir()
    img_migrated = migrate_existing_images()

    data = load_data()
    records_before = len(data.get("records", []))

    data, purged_count = purge_old_garde_records(data)

    seen = {}
    deduped = []
    for r in reversed(data.get("records", [])):
        key = (r.get("type",""), r.get("weekKey",""), str(r.get("dayOfWeek","")), r.get("nom","") or r.get("name","") or r.get("id",""))
        if key not in seen:
            seen[key] = True
            deduped.append(r)
    deduped.reverse()
    dupes_removed = len(data.get("records", [])) - len(deduped)
    data["records"] = deduped

    records_after = len(data["records"])
    if purged_count > 0 or dupes_removed > 0:
        save_data_backup(data)
        print(f"🗑️  Purge démarrage : {purged_count} garde(s) passée(s) supprimée(s)")
        if dupes_removed > 0:
            print(f"🧹  Dédoublonnage : {dupes_removed} doublon(s) supprimé(s)")
        print(f"📦  Records : {records_before} → {records_after}")
    else:
        print("✓ Fichier propre, aucun nettoyage nécessaire")

    purge_thread = threading.Thread(target=run_daily_purge, daemon=True, name="PurgeQuotidienne")
    purge_thread.start()

    print("=" * 55)
    print("  🚒  SERVEUR GARDE CHG DÉMARRÉ (Flask)")
    print("=" * 55)
    print(f"  Sur ce PC         : http://localhost:{PORT}")
    print(f"  Depuis les autres : http://{ip}:{PORT}")
    print("=" * 55)
    print("  Fermez cette fenêtre pour arrêter le serveur")
    print("=" * 55)

    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
