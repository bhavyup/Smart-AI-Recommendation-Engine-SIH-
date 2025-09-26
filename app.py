import hashlib
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import os
import uuid
import joblib
from smart_allocation_engine import SmartAllocationEngine
from language_support import LanguageSupport
from models import db, Candidate, Internship, Shortlist
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from flask_compress import Compress
import time

load_dotenv()

app = Flask(__name__)
CORS(app)
Compress(app)

# Session secret and admin credentials (env-driven)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
AN_CACHE = {'ts': 0, 'data': None}
AN_TTL = int(os.environ.get('ANALYTICS_TTL', '20'))  # seconds


def analytics_cache_get():
    now = time.time()
    if AN_CACHE['data'] is not None and (now - AN_CACHE['ts']) < AN_TTL:
        return AN_CACHE['data']
    return None


def analytics_cache_set(payload):
    AN_CACHE['data'] = payload
    AN_CACHE['ts'] = time.time()


def analytics_cache_clear():
    AN_CACHE['data'] = None
    AN_CACHE['ts'] = 0


# Dev convenience: allow plain ADMIN_PASSWORD, convert to hash
if not ADMIN_PASSWORD_HASH and os.environ.get('ADMIN_PASSWORD'):
    ADMIN_PASSWORD_HASH = generate_password_hash(os.environ['ADMIN_PASSWORD'])

if not ADMIN_PASSWORD_HASH:
    # Fallback for local/demo only. CHANGE in production.
    ADMIN_PASSWORD_HASH = generate_password_hash('admin123')
    print("⚠️ Using default admin password 'admin123'. Set ADMIN_PASSWORD or ADMIN_PASSWORD_HASH in .env")

# Optional hardening (recommended in prod)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
    # SESSION_COOKIE_SECURE=True  # enable on HTTPS
)

# Globals for persistence mode and state paths
DATA_DIR = 'data'
STATE_FILE = os.path.join(DATA_DIR, 'engine.joblib')
PERSISTENCE_MODE = None             # 'db' (Postgres), 'sqlite', or 'file'
ACTIVE_DB_URI = None
SHORTLIST_FILE = os.path.join(DATA_DIR, 'shortlist.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
SETTINGS_DEFAULTS = {
    "weights": {"skill": 30, "location": 20, "education": 20, "sector": 15, "diversity": 15},
    "language": {"default": "en", "enabled": ["en", "hi", "ta"]}
}
CSV_PATH = os.environ.get('INTERNSHIP_CSV') or os.path.join(
    DATA_DIR, 'internships.csv')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)

os.makedirs(DATA_DIR, exist_ok=True)

ai_engine = SmartAllocationEngine()
language_support = LanguageSupport()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get('is_admin'):
            return fn(*args, **kwargs)
        # JSON for API calls; redirect for pages
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        return redirect(url_for('login', next=request.path))
    return wrapper


def _nocache(resp):
    try:
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0, private'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
        # Helpful for proxies/CDNs to not reuse across users
        resp.headers['Vary'] = (resp.headers.get(
            'Vary', '') + ', Cookie').strip(', ')
    except Exception:
        pass
    return resp


@app.after_request
def add_no_cache_headers(resp):
    try:
        p = (request.path or '')
        # Never cache admin or login pages or admin API responses
        if p == '/admin' or p == '/login' or p.startswith('/api/admin'):
            return _nocache(resp)
    except Exception:
        pass
    return resp


def _read_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return json.loads(json.dumps(default))


def _write_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        return False


def _read_settings():
    return _read_json(SETTINGS_FILE, SETTINGS_DEFAULTS)


def _write_settings(s):
    return _write_json(SETTINGS_FILE, s)


CSV_META_FILE = os.path.join(DATA_DIR, 'csv_meta.json')


def _read_csv_meta():
    return _read_json(CSV_META_FILE, {"path": None, "sha256": None, "size": 0})


def _write_csv_meta(meta: dict):
    return _write_json(CSV_META_FILE, meta)


def _file_signature(path: str):
    try:
        h = hashlib.sha256()
        size = 0
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                size += len(chunk)
        return {"sha256": h.hexdigest(), "size": size}
    except Exception:
        return None


def _truncate_internships():
    # Truncate/clear internships table and reset identity safely across vendors
    if PERSISTENCE_MODE not in ('db', 'sqlite'):
        return
    eng = db.engine
    dialect = eng.url.get_dialect().name  # 'postgresql' or 'sqlite'
    if dialect == 'postgresql':
        db.session.execute(
            text("TRUNCATE TABLE internships RESTART IDENTITY CASCADE"))
    else:
        db.session.execute(text("DELETE FROM internships"))
        # reset sqlite autoincrement
        try:
            db.session.execute(
                text("DELETE FROM sqlite_sequence WHERE name='internships'"))
        except Exception:
            pass
    db.session.commit()


def _import_csv_to_db(path: str, mode: str = 'append') -> int:
    if not os.path.exists(path):
        raise FileNotFoundError(f'CSV not found: {path}')
    ok = ai_engine.load_internship_data_from_csv(path)
    if not ok or not ai_engine.internship_data:
        raise ValueError('CSV load returned no internships')

    imported = ai_engine.internship_data  # list[dict]

    if PERSISTENCE_MODE in ('db', 'sqlite'):
        with app.app_context():
            if mode == 'replace':
                _truncate_internships()

            # Dedup key – case-insensitive (title, company, location)
            existing = set()
            if mode == 'append':
                for i in Internship.query.all():
                    existing.add(
                        (i.title.lower(), i.company.lower(), i.location.lower()))

            adds = []
            for i in imported:
                key = (i['title'].lower(), i['company'].lower(),
                       i['location'].lower())
                if mode == 'append' and key in existing:
                    continue
                adds.append(Internship(
                    title=i['title'], company=i['company'], sector=i['sector'],
                    location=i['location'], skills_required=i.get(
                        'skills_required', []),
                    education_level=i['education_level'], capacity=i['capacity'],
                    duration_months=i['duration_months'], stipend=i['stipend'],
                    rural_friendly=bool(i.get('rural_friendly', False)),
                    diversity_focused=bool(i.get('diversity_focused', False))
                ))

            if adds:
                db.session.bulk_save_objects(adds)
                db.session.commit()

            # Sync engine + TF-IDF + snapshot
            load_db_into_engine()
            write_snapshot_from_engine()

            return len(adds)
    else:
        # FILE mode: replace/append engine
        if mode == 'replace':
            ai_engine.internship_data = imported
        else:
            seen = {(x.get('title'), x.get('company'), x.get('location'))
                    for x in (ai_engine.internship_data or [])}
            for it in imported:
                k = (it['title'], it['company'], it['location'])
                if k not in seen:
                    ai_engine.internship_data.append(it)
        ai_engine.rebuild_tfidf()
        write_snapshot_from_engine()
        return len(imported)


# Load settings now and apply weights to engine
SETTINGS = _read_settings()
try:
    ai_engine.set_weights(SETTINGS.get(
        'weights', SETTINGS_DEFAULTS['weights']))
except Exception:
    pass


def _read_shortlist_file():
    try:
        if not os.path.exists(SHORTLIST_FILE):
            return []
        with open(SHORTLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f) or []
    except Exception:
        return []


def _write_shortlist_file(entries: list):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SHORTLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _shortlist_add(email: str, internship_id: int):
    e = (email or '').strip().lower()
    iid = int(internship_id)
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        existing = Shortlist.query.filter_by(
            email=e, internship_id=iid).first()
        if existing:
            return 'exists'
        db.session.add(Shortlist(email=e, internship_id=iid))
        db.session.commit()
        return 'added'
    # FILE fallback
    entries = _read_shortlist_file()
    if any((x.get('email', '').lower(), int(x.get('internship_id', 0))) == (e, iid) for x in entries):
        return 'exists'
    entries.append({'email': e, 'internship_id': iid,
                   'created_at': datetime.utcnow().isoformat() + 'Z'})
    _write_shortlist_file(entries)
    return 'added'


def _shortlist_remove(email: str, internship_id: int):
    e = (email or '').strip().lower()
    iid = int(internship_id)
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        obj = Shortlist.query.filter_by(email=e, internship_id=iid).first()
        if not obj:
            return 'not_found'
        db.session.delete(obj)
        db.session.commit()
        return 'removed'
    # FILE fallback
    entries = _read_shortlist_file()
    before = len(entries)
    entries = [x for x in entries if (
        x.get('email', '').lower(), int(x.get('internship_id', 0))) != (e, iid)]
    _write_shortlist_file(entries)
    return 'removed' if len(entries) < before else 'not_found'


def _shortlist_ids(email: str):
    e = (email or '').strip().lower()
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        return [s.internship_id for s in Shortlist.query.filter_by(email=e).all()]
    # FILE fallback
    return [int(x.get('internship_id', 0)) for x in _read_shortlist_file() if (x.get('email', '').lower() == e)]


def _shortlist_remove_internship(internship_id: int):
    iid = int(internship_id)
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        try:
            Shortlist.query.filter_by(internship_id=iid).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()
        return
    # FILE fallback
    try:
        entries = _read_shortlist_file()
        entries = [e for e in entries if int(e.get('internship_id', 0)) != iid]
        _write_shortlist_file(entries)
    except Exception:
        pass


def _parse_bool(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    return bool(x)


def _parse_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [s.strip() for s in val.split(',') if s.strip()]
    return []


def _normalize_internship_payload(data: dict, partial: bool = False):
    required = ['title', 'company', 'sector', 'location', 'skills_required',
                'education_level', 'capacity', 'duration_months', 'stipend']
    if not partial:
        for f in required:
            if f not in data or data[f] in (None, '', []):
                raise ValueError(f'Missing required field: {f}')

    norm = {}
    if 'title' in data:
        norm['title'] = str(data['title']).strip()
    if 'company' in data:
        norm['company'] = str(data['company']).strip()
    if 'sector' in data:
        norm['sector'] = str(data['sector']).strip()
    if 'location' in data:
        norm['location'] = str(data['location']).strip()
    if 'skills_required' in data:
        norm['skills_required'] = _parse_list(data['skills_required'])
    if 'education_level' in data:
        norm['education_level'] = str(data['education_level']).strip()
    if 'capacity' in data:
        norm['capacity'] = int(data['capacity'])
    if 'duration_months' in data:
        norm['duration_months'] = int(data['duration_months'])
    if 'stipend' in data:
        norm['stipend'] = int(data['stipend'])
    if 'rural_friendly' in data:
        norm['rural_friendly'] = _parse_bool(data['rural_friendly'])
    if 'diversity_focused' in data:
        norm['diversity_focused'] = _parse_bool(data['diversity_focused'])

    return norm


def migrate_shortlist_file_to_db():
    """One-time import from data/shortlist.json into DB if table is empty."""
    try:
        if PERSISTENCE_MODE not in ('db', 'sqlite'):
            return
        count = db.session.execute(
            text("SELECT COUNT(*) FROM shortlist")).scalar() or 0
        if count > 0:
            return
        entries = _read_shortlist_file()
        added = 0
        for e in entries:
            email = (e.get('email') or '').strip().lower()
            try:
                iid = int(e.get('internship_id', 0))
            except Exception:
                continue
            if not email or not iid:
                continue
            if not Shortlist.query.filter_by(email=email, internship_id=iid).first():
                db.session.add(Shortlist(email=email, internship_id=iid))
                added += 1
        if added:
            db.session.commit()
            print(f"🧩 Migrated {added} shortlist entries from file to DB.")
    except Exception as ex:
        print(f"⚠️  Shortlist migration skipped: {ex}")


def load_db_into_engine():
    internships = [i.to_dict() for i in Internship.query.all()]
    candidates = [c.to_dict() for c in Candidate.query.all()]
    ai_engine.internship_data = internships
    ai_engine.candidate_data = candidates
    # Rebuild TF-IDF for DB-loaded internships
    try:
        ai_engine.rebuild_tfidf()
    except Exception:
        pass


def snapshot_state_to_file():
    try:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            with app.app_context():
                load_db_into_engine()
        # For file mode, engine is already current
        ai_engine.save_model(STATE_FILE)
        print(f"💾 Snapshot saved to {STATE_FILE}")
    except Exception as e:
        print(f"⚠️  Could not save snapshot to file: {e}")


def ensure_email_unique_index():
    try:
        with app.app_context():
            db.session.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_email ON candidates(email)"))
            db.session.commit()
    except Exception as e:
        print(f"⚠️  Could not create unique index on email: {e}")


def ensure_uid_column_and_index():
    try:
        with app.app_context():
            insp = inspect(db.engine)
            cols = [c['name'] for c in insp.get_columns('candidates')]
            if 'uid' not in cols:
                # Add column
                db.session.execute(
                    text("ALTER TABLE candidates ADD COLUMN uid VARCHAR(36)"))
                db.session.commit()
            # Backfill any NULL/empty uids
            rows = db.session.execute(
                text("SELECT id FROM candidates WHERE uid IS NULL OR uid = ''")).fetchall()
            for (cid,) in rows:
                db.session.execute(text("UPDATE candidates SET uid = :uid WHERE id = :id"),
                                   {'uid': str(uuid.uuid4()), 'id': cid})
            db.session.commit()
            # Create unique index if not exists (SQLite and Postgres support IF NOT EXISTS)
            db.session.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS idx_candidates_uid ON candidates(uid)"))
            db.session.commit()
    except Exception as e:
        print(f"⚠️  Could not ensure uid column/index: {e}")


def read_snapshot():
    try:
        if not os.path.exists(STATE_FILE):
            return [], []
        data = joblib.load(STATE_FILE)
        return data.get('candidate_data', []) or [], data.get('internship_data', []) or []
    except Exception as e:
        print(f"⚠️  Could not read snapshot: {e}")
        return [], []


def write_snapshot_from_engine():
    """Write current engine state to snapshot."""
    try:
        ai_engine.save_model(STATE_FILE)
        print(f"💾 Snapshot saved to {STATE_FILE}")
    except Exception as e:
        print(f"⚠️  Could not save snapshot: {e}")


def merge_candidates(existing: list, incoming: list) -> list:
    def norm_list(x):
        if not x:
            return []
        seen = set()
        out = []
        for s in x:
            val = (s or '').strip()
            if val and val.lower() not in seen:
                seen.add(val.lower())
                out.append(val)
        return out

    by_uid = {}
    # seed existing
    for c in existing or []:
        c = dict(c)
        if not c.get('uid'):
            c['uid'] = str(uuid.uuid4())
        c['skills'] = norm_list(c.get('skills'))
        c['sector_interests'] = norm_list(c.get('sector_interests'))
        by_uid[c['uid']] = c

    # merge incoming
    for c in incoming or []:
        c = dict(c)
        if not c.get('uid'):
            c['uid'] = str(uuid.uuid4())
        c['skills'] = norm_list(c.get('skills'))
        c['sector_interests'] = norm_list(c.get('sector_interests'))

        if c['uid'] not in by_uid:
            by_uid[c['uid']] = c
        else:
            base = by_uid[c['uid']]
            # prefer non-empty fields
            for k in ['name', 'email', 'education_level', 'location', 'social_category']:
                if not base.get(k) and c.get(k):
                    base[k] = c[k]
            # union lists
            base['skills'] = norm_list(
                (base.get('skills') or []) + (c.get('skills') or []))
            base['sector_interests'] = norm_list(
                (base.get('sector_interests') or []) + (c.get('sector_interests') or []))
            # booleans: OR
            for k in ['prefers_rural', 'from_rural_area', 'first_generation_graduate']:
                base[k] = bool(base.get(k) or c.get(k))
            by_uid[c['uid']] = base
    return list(by_uid.values())


def upsert_candidates_into_active_db(candidates: list):
    with app.app_context():
        for c in candidates:
            uid_val = c.get('uid') or str(uuid.uuid4())
            obj = Candidate.query.filter_by(uid=uid_val).first()
            if not obj:
                obj = Candidate(uid=uid_val,
                                name=c.get('name', ''),
                                email=c.get('email'),
                                education_level=c.get(
                                    'education_level', 'Bachelor'),
                                location=c.get('location', ''),
                                skills=c.get('skills') or [],
                                sector_interests=c.get(
                                    'sector_interests') or [],
                                prefers_rural=bool(
                                    c.get('prefers_rural', False)),
                                from_rural_area=bool(
                                    c.get('from_rural_area', False)),
                                social_category=c.get('social_category', ''),
                                first_generation_graduate=bool(c.get('first_generation_graduate', False)))
                db.session.add(obj)
            else:
                # update minimal fields (optional: extend merge policy)
                obj.name = obj.name or c.get('name', '')
                obj.email = obj.email or c.get('email')
                obj.education_level = obj.education_level or c.get(
                    'education_level', 'Bachelor')
                obj.location = obj.location or c.get('location', '')
                # union lists
                existing_sk = set((obj.skills or []))
                incoming_sk = set(c.get('skills') or [])
                obj.skills = list(existing_sk.union(incoming_sk))
                existing_sect = set((obj.sector_interests or []))
                incoming_sect = set(c.get('sector_interests') or [])
                obj.sector_interests = list(existing_sect.union(incoming_sect))
                # booleans OR
                obj.prefers_rural = bool(
                    obj.prefers_rural or c.get('prefers_rural', False))
                obj.from_rural_area = bool(
                    obj.from_rural_area or c.get('from_rural_area', False))
                obj.first_generation_graduate = bool(
                    obj.first_generation_graduate or c.get('first_generation_graduate', False))
                # social_category prefer non-empty
                if not obj.social_category and c.get('social_category'):
                    obj.social_category = c.get('social_category')
        db.session.commit()


def sync_from_file_to_active_db():

    if PERSISTENCE_MODE not in ('db', 'sqlite'):
        return
    with app.app_context():
        ensure_uid_column_and_index()
        # Load file snapshot (non-destructive)
        file_candidates, file_internships = read_snapshot()

        # Seed internships if the DB is empty:
        if Internship.query.count() == 0:
            seeded = False
            # Try CSV first
            try:
                if os.path.exists(CSV_PATH) and ai_engine.load_internship_data_from_csv(CSV_PATH):
                    for i in ai_engine.internship_data:
                        db.session.add(Internship(
                            title=i['title'], company=i['company'], sector=i['sector'],
                            location=i['location'], skills_required=i.get(
                                'skills_required', []),
                            education_level=i['education_level'], capacity=i['capacity'],
                            duration_months=i['duration_months'], stipend=i['stipend'],
                            rural_friendly=bool(
                                i.get('rural_friendly', False)),
                            diversity_focused=bool(
                                i.get('diversity_focused', False))
                        ))
                    db.session.commit()
                    print(f"🧩 Seeded internships from CSV: {CSV_PATH}")
                    seeded = True
            except Exception as e:
                print(f"⚠️  CSV seed failed: {e}")

            if not seeded:
                if file_internships:
                    for i in file_internships:
                        db.session.add(Internship(
                            title=i['title'], company=i['company'], sector=i['sector'],
                            location=i['location'], skills_required=i.get(
                                'skills_required', []),
                            education_level=i['education_level'], capacity=i['capacity'],
                            duration_months=i['duration_months'], stipend=i['stipend'],
                            rural_friendly=bool(
                                i.get('rural_friendly', False)),
                            diversity_focused=bool(
                                i.get('diversity_focused', False))
                        ))
                    db.session.commit()
                    print("🧩 Seeded internships from snapshot.")
                else:
                    ai_engine.load_sample_data()
                    for i in ai_engine.internship_data:
                        db.session.add(Internship(
                            title=i['title'], company=i['company'], sector=i['sector'],
                            location=i['location'], skills_required=i['skills_required'],
                            education_level=i['education_level'], capacity=i['capacity'],
                            duration_months=i['duration_months'], stipend=i['stipend'],
                            rural_friendly=i['rural_friendly'], diversity_focused=i['diversity_focused']
                        ))
                    db.session.commit()
                    print("🧩 Seeded internships from sample data.")

        # Merge candidates: DB current + snapshot, then upsert
        db_current = [c.to_dict() for c in Candidate.query.all()]
        merged = merge_candidates(db_current, file_candidates)
        upsert_candidates_into_active_db(merged)

        # Keep engine in sync and write snapshot again (authoritative snapshot)
        load_db_into_engine()
        write_snapshot_from_engine()


def auto_import_csv_if_changed():
    # 'off' | 'append' | 'replace'
    mode = (os.environ.get('CSV_IMPORT_MODE') or 'off').lower()
    if mode not in ('append', 'replace'):
        return
    if not os.path.exists(CSV_PATH):
        print(f"ℹ️  CSV_IMPORT_MODE='{mode}' but CSV not found at {CSV_PATH}")
        return
    sig = _file_signature(CSV_PATH)
    if not sig:
        print(f"ℹ️  Could not hash CSV: {CSV_PATH}")
        return
    meta = _read_csv_meta()
    if meta.get('path') == CSV_PATH and meta.get('sha256') == sig['sha256'] and meta.get('size') == sig['size']:
        print(f"ℹ️  CSV unchanged; skipping auto-import.")
        return
    try:
        cnt = _import_csv_to_db(CSV_PATH, mode)
        _write_csv_meta({"path": CSV_PATH, **sig})
        print(f"🧩 Auto-imported CSV ({mode}): {cnt} rows from {CSV_PATH}")
    except Exception as e:
        print(f"⚠️  Auto-import failed: {e}")


def can_connect(uri: str) -> bool:

    try:
        engine = create_engine(uri, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


postgres_uri = os.environ.get('DATABASE_URL')  # from .env
sqlite_path = Path(DATA_DIR) / 'app.db'
sqlite_path.parent.mkdir(parents=True, exist_ok=True)
sqlite_uri = f"sqlite:///{sqlite_path.resolve().as_posix()}"

if postgres_uri and can_connect(postgres_uri):
    PERSISTENCE_MODE = 'db'
    ACTIVE_DB_URI = postgres_uri
    print(f"✅ Using PostgreSQL: {ACTIVE_DB_URI}")
else:
    # Try SQLite fallback
    if can_connect(sqlite_uri):
        PERSISTENCE_MODE = 'sqlite'
        ACTIVE_DB_URI = sqlite_uri
        print(
            f"⚠️  PostgreSQL unavailable. Using SQLite fallback: {ACTIVE_DB_URI}")
    else:
        # Final fallback: file-based persistence
        PERSISTENCE_MODE = 'file'
        ACTIVE_DB_URI = None
        print("❌ Database unavailable. Using FILE-BASED fallback for persistence.")

if PERSISTENCE_MODE in ('db', 'sqlite'):
    app.config['SQLALCHEMY_DATABASE_URI'] = ACTIVE_DB_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        try:
            db.create_all()
            # Ensure schema supports uid and backfill
            ensure_uid_column_and_index()
            ensure_email_unique_index()
            migrate_shortlist_file_to_db()
            # Import from snapshot to ensure DB is never behind file
            sync_from_file_to_active_db()
            auto_import_csv_if_changed()
            print("✅ DB initialized and synchronized with snapshot.")
        except Exception as e:
            print(f"❌ DB initialization failed: {e}")
            print("   Falling back to FILE-BASED persistence.")
            PERSISTENCE_MODE = 'file'
            ACTIVE_DB_URI = None

if PERSISTENCE_MODE == 'file':
    try:
        ai_engine.load_model(STATE_FILE)
        print(f"📦 Loaded file-based state from {STATE_FILE}")
    except Exception:
        seeded = False
        try:
            if os.path.exists(CSV_PATH) and ai_engine.load_internship_data_from_csv(CSV_PATH):
                seeded = True
                print(f"🧩 Seeded internships from CSV: {CSV_PATH}")
        except Exception as e:
            print(f"⚠️  CSV load failed: {e}")
        if not seeded:
            ai_engine.load_sample_data()
            print("🧩 Seeded sample internships")
        ai_engine.save_model(STATE_FILE)
        print(f"💾 Created snapshot {STATE_FILE}")


@app.route('/')
def landing():
    """Landing page with navigation options"""
    return render_template('landing.html')


@app.route('/candidate')
def index():
    """Main page with candidate input form"""
    return render_template('index.html')


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard for system management"""
    resp = make_response(render_template('admin_dashboard.html'))
    return _nocache(resp)


@app.route('/api/admin/me')
@admin_required
def admin_me():
    return jsonify({'success': True, 'user': session.get('admin_user')})


@app.route('/api/recommendations/by-email')
def recommendations_by_email():
    """Get recommendations using the stored profile by email (no record creation)."""
    try:
        email = request.args.get('email', '').strip()
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            existing = Candidate.query.filter_by(email=email).first()
            if not existing:
                return jsonify({'success': False, 'error': 'Candidate not found'}), 404
            profile = existing.to_dict()
            ai_engine.internship_data = [i.to_dict()
                                         for i in Internship.query.all()]
        else:
            existing = next((c for c in (ai_engine.candidate_data or []) if (
                c.get('email') or '').strip().lower() == email.lower()), None)
            if not existing:
                return jsonify({'success': False, 'error': 'Candidate not found'}), 404
            profile = existing
            if not ai_engine.internship_data:
                ai_engine.load_sample_data()

        recs = ai_engine.get_recommendations(profile, top_n=5)
        return jsonify({'success': True, 'recommendations': recs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    """API endpoint to get internship recommendations (and register candidate)"""
    try:
        data = request.get_json()

        # Validate required fields (email required for dedupe)
        required_fields = ['name', 'email', 'education_level',
                           'skills', 'location', 'sector_interests']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Normalize candidate payload
        candidate_info = {
            'uid': data.get('uid') or str(uuid.uuid4()),
            'name': data['name'],
            'email': data['email'],
            'education_level': data['education_level'],
            'skills': data['skills'] if isinstance(data['skills'], list) else [data['skills']],
            'location': data['location'],
            'sector_interests': data['sector_interests'] if isinstance(data['sector_interests'], list) else [data['sector_interests']],
            'prefers_rural': bool(data.get('prefers_rural', False)),
            'from_rural_area': bool(data.get('from_rural_area', False)),
            'social_category': data.get('social_category', ''),
            'first_generation_graduate': bool(data.get('first_generation_graduate', False))
        }

        # If email exists, reuse stored profile; else create new
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            existing = Candidate.query.filter_by(
                email=candidate_info['email']).first()
            if existing:
                candidate_id = existing.id
                profile = existing.to_dict()  # use stored preferences
                # keep engine internships in sync with DB for scoring
                ai_engine.internship_data = [
                    i.to_dict() for i in Internship.query.all()]
            else:
                # create new
                candidate = Candidate(
                    uid=candidate_info['uid'],
                    name=candidate_info['name'],
                    email=candidate_info['email'],
                    education_level=candidate_info['education_level'],
                    location=candidate_info['location'],
                    skills=candidate_info['skills'],
                    sector_interests=candidate_info['sector_interests'],
                    prefers_rural=candidate_info['prefers_rural'],
                    from_rural_area=candidate_info['from_rural_area'],
                    social_category=candidate_info['social_category'],
                    first_generation_graduate=candidate_info['first_generation_graduate']
                )
                db.session.add(candidate)
                db.session.commit()
                candidate_id = candidate.id
                profile = candidate_info
                # Sync memory and snapshot for fallbacks
                with app.app_context():
                    load_db_into_engine()
                write_snapshot_from_engine()
        else:
            # FILE mode: dedupe by email within file snapshot/engine
            existing = next((c for c in (ai_engine.candidate_data or []) if c.get(
                'email') == candidate_info['email']), None)
            if existing:
                candidate_id = existing.get('id')
                profile = existing  # use stored preferences
            else:
                candidate_id = ai_engine.add_candidate(candidate_info)
                profile = candidate_info
                write_snapshot_from_engine()

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            pass  # internships already set above
        else:
            if not ai_engine.internship_data:
                ai_engine.load_sample_data()
                ai_engine.save_model(STATE_FILE)

        recommendations = ai_engine.get_recommendations(profile, top_n=5)

        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'recommendations': recommendations
        })
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/internships')
def get_internships():
    """Get all available internships"""
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        internships = [i.to_dict() for i in Internship.query.all()]
    else:
        internships = ai_engine.internship_data or []
    return jsonify({
        'success': True,
        'internships': internships
    })


@app.route('/api/internships/<int:internship_id>', methods=['GET'])
def get_internship(internship_id):
    """Get single internship by ID."""
    try:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Internship.query.get(internship_id)
            if not obj:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            return jsonify({'success': True, 'internship': obj.to_dict()})
        else:
            it = next((i for i in (ai_engine.internship_data or [])
                      if int(i.get('id', 0)) == internship_id), None)
            if not it:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            return jsonify({'success': True, 'internship': it})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/internships', methods=['POST'])
@admin_required
def create_internship():
    """Create a new internship."""
    try:
        data = request.get_json() or {}
        norm = _normalize_internship_payload(data, partial=False)

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Internship(
                title=norm['title'],
                company=norm['company'],
                sector=norm['sector'],
                location=norm['location'],
                skills_required=norm['skills_required'],
                education_level=norm['education_level'],
                capacity=norm['capacity'],
                duration_months=norm['duration_months'],
                stipend=norm['stipend'],
                rural_friendly=bool(norm.get('rural_friendly', False)),
                diversity_focused=bool(norm.get('diversity_focused', False))
            )
            db.session.add(obj)
            db.session.commit()
            analytics_cache_clear()

            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()

            return jsonify({'success': True, 'internship': obj.to_dict()})
        else:
            # FILE mode
            nxt_id = 1 + max([int(i.get('id', 0))
                             for i in (ai_engine.internship_data or [])] or [0])
            it = {
                'id': nxt_id,
                'title': norm['title'],
                'company': norm['company'],
                'sector': norm['sector'],
                'location': norm['location'],
                'skills_required': norm['skills_required'],
                'education_level': norm['education_level'],
                'capacity': norm['capacity'],
                'duration_months': norm['duration_months'],
                'stipend': norm['stipend'],
                'rural_friendly': bool(norm.get('rural_friendly', False)),
                'diversity_focused': bool(norm.get('diversity_focused', False))
            }
            ai_engine.internship_data = (ai_engine.internship_data or [])
            ai_engine.internship_data.append(it)
            ai_engine.rebuild_tfidf()
            write_snapshot_from_engine()
            return jsonify({'success': True, 'internship': it})
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/internships/<int:internship_id>', methods=['PUT'])
@admin_required
def update_internship(internship_id):
    """Update an internship (partial update allowed)."""
    try:
        data = request.get_json() or {}
        norm = _normalize_internship_payload(data, partial=True)

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Internship.query.get(internship_id)
            if not obj:
                return jsonify({'success': False, 'error': 'Not found'}), 404

            # Patch fields if present
            for k in ['title', 'company', 'sector', 'location', 'education_level', 'capacity', 'duration_months', 'stipend']:
                if k in norm:
                    setattr(obj, k, norm[k])
            if 'skills_required' in norm:
                obj.skills_required = norm['skills_required']
            if 'rural_friendly' in norm:
                obj.rural_friendly = bool(norm['rural_friendly'])
            if 'diversity_focused' in norm:
                obj.diversity_focused = bool(norm['diversity_focused'])

            db.session.commit()
            analytics_cache_clear()
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()
            return jsonify({'success': True, 'internship': obj.to_dict()})
        else:
            # FILE mode
            found = False
            for i in (ai_engine.internship_data or []):
                if int(i.get('id', 0)) == internship_id:
                    for k in ['title', 'company', 'sector', 'location', 'education_level', 'capacity', 'duration_months', 'stipend']:
                        if k in norm:
                            i[k] = norm[k]
                    if 'skills_required' in norm:
                        i['skills_required'] = norm['skills_required']
                    if 'rural_friendly' in norm:
                        i['rural_friendly'] = bool(norm['rural_friendly'])
                    if 'diversity_focused' in norm:
                        i['diversity_focused'] = bool(
                            norm['diversity_focused'])
                    found = True
                    break
            if not found:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            ai_engine.rebuild_tfidf()
            write_snapshot_from_engine()
            it = next(i for i in ai_engine.internship_data if int(
                i.get('id', 0)) == internship_id)
            return jsonify({'success': True, 'internship': it})
    except ValueError as ve:
        return jsonify({'success': False, 'error': str(ve)}), 400
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/internships/<int:internship_id>', methods=['DELETE'])
@admin_required
def delete_internship(internship_id):
    """Delete an internship and remove any shortlist entries referencing it."""
    try:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Internship.query.get(internship_id)
            if not obj:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            db.session.delete(obj)
            db.session.commit()
            analytics_cache_clear()
            _shortlist_remove_internship(internship_id)
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()
            return jsonify({'success': True})
        else:
            before = len(ai_engine.internship_data or [])
            ai_engine.internship_data = [i for i in (
                ai_engine.internship_data or []) if int(i.get('id', 0)) != internship_id]
            after = len(ai_engine.internship_data or [])
            if after == before:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            _shortlist_remove_internship(internship_id)
            ai_engine.rebuild_tfidf()
            write_snapshot_from_engine()
            return jsonify({'success': True})
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/languages')
def get_languages():
    """Get supported languages"""
    return jsonify({
        'success': True,
        'languages': language_support.get_supported_languages()
    })


@app.route('/api/translations/<language_code>')
def get_translations(language_code):
    """Get translations for a specific language"""
    language_support.set_language(language_code)
    return jsonify({
        'success': True,
        'translations': language_support.get_all_texts()
    })


@app.route('/api/analytics')
def get_analytics():
    """Get analytics data for dashboard (DB/SQLite/File) with TTL cache."""
    try:
        # 1) Serve from cache if fresh
        cached = analytics_cache_get()
        if cached is not None:
            return jsonify({'success': True, 'analytics': cached, 'cached': True})

            # 2) Compute fresh analytics
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            total_candidates = Candidate.query.count()
            total_internships = Internship.query.count()
            candidates = Candidate.query.all()
            internships = Internship.query.all()
            sector_counts = {}
            for i in internships:
                sector_counts[i.sector] = sector_counts.get(i.sector, 0) + 1
        else:
            candidates_list = ai_engine.candidate_data or []
            internships_list = ai_engine.internship_data or []
            total_candidates = len(candidates_list)
            total_internships = len(internships_list)
            sector_counts = {}
            for i in internships_list:
                sector_counts[i['sector']] = sector_counts.get(
                    i['sector'], 0) + 1

            class _C:
                def __init__(self, d): self.__dict__ = d
                def __getattr__(self, k): return self.__dict__.get(k)
            candidates = [_C(c) for c in candidates_list]

            # Diversity metrics
            diversity_candidates = sum(
                1 for c in candidates
                if getattr(c, 'from_rural_area', False) or
                getattr(c, 'social_category', '') in ['SC', 'ST', 'OBC'] or
                getattr(c, 'first_generation_graduate', False)
            )
            diversity_rate = (
                diversity_candidates / total_candidates * 100) if total_candidates > 0 else 0

            # Location distribution
            location_counts = {}
            for c in candidates:
                loc = getattr(c, 'location', 'Unknown')
                location_counts[loc] = location_counts.get(loc, 0) + 1

            # Education distribution
            education_counts = {}
            for c in candidates:
                edu = getattr(c, 'education_level', 'Unknown')
                education_counts[edu] = education_counts.get(edu, 0) + 1

            result = {
                'total_candidates': total_candidates,
                'total_internships': total_internships,
                'diversity_rate': round(diversity_rate, 1),
                'sector_distribution': sector_counts,
                'location_distribution': location_counts,
                'education_distribution': education_counts
            }

            # 3) Store and return
            analytics_cache_set(result)
            return jsonify({'success': True, 'analytics': result, 'cached': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/candidates')
def get_candidates():
    """Get all registered candidates"""
    if PERSISTENCE_MODE in ('db', 'sqlite'):
        candidates = [c.to_dict() for c in Candidate.query.all()]
    else:
        candidates = ai_engine.candidate_data or []
    return jsonify({
        'success': True,
        'candidates': candidates
    })


@app.route('/api/candidates', methods=['POST'])
def add_candidate():
    """Add a new candidate (persistent across DB/SQLite/File)"""
    try:
        data = request.get_json()

        # Validate required fields (email optional here; dedupe only if provided)
        required_fields = ['name', 'education_level',
                           'skills', 'location', 'sector_interests']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Normalize payload
        skills = data['skills'] if isinstance(
            data['skills'], list) else [data['skills']]
        sectors = data['sector_interests'] if isinstance(
            data['sector_interests'], list) else [data['sector_interests']]
        email = data.get('email')
        uid_val = data.get('uid') or str(uuid.uuid4())

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            # If email provided, dedupe by email
            if email:
                existing = Candidate.query.filter_by(email=email).first()
                if existing:
                    return jsonify({
                        'success': True,
                        'candidate_id': existing.id,
                        'message': 'Candidate already exists'
                    })
            candidate = Candidate(
                uid=uid_val,
                name=data['name'],
                email=email,
                education_level=data['education_level'],
                location=data['location'],
                skills=skills,
                sector_interests=sectors,
                prefers_rural=bool(data.get('prefers_rural', False)),
                from_rural_area=bool(data.get('from_rural_area', False)),
                social_category=data.get('social_category', ''),
                first_generation_graduate=bool(
                    data.get('first_generation_graduate', False))
            )
            db.session.add(candidate)
            db.session.commit()
            candidate_id = candidate.id
            analytics_cache_clear()

            # Sync memory and backup to file
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()
        else:
            # FILE mode
            if email:
                existing = next(
                    (c for c in (ai_engine.candidate_data or []) if c.get('email') == email), None)
                if existing:
                    return jsonify({
                        'success': True,
                        'candidate_id': existing.get('id'),
                        'message': 'Candidate already exists'
                    })
            candidate_info = {
                'uid': uid_val,
                'name': data['name'],
                'email': email,
                'education_level': data['education_level'],
                'location': data['location'],
                'skills': skills,
                'sector_interests': sectors,
                'prefers_rural': bool(data.get('prefers_rural', False)),
                'from_rural_area': bool(data.get('from_rural_area', False)),
                'social_category': data.get('social_category', ''),
                'first_generation_graduate': bool(data.get('first_generation_graduate', False))
            }
            candidate_id = ai_engine.add_candidate(candidate_info)
            write_snapshot_from_engine()

        return jsonify({
            'success': True,
            'candidate_id': candidate_id,
            'message': 'Candidate added successfully'
        })
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/candidates/lookup')
def candidate_lookup():
    """Lookup candidate by email (for live search). Returns exists + candidate if found."""
    try:
        email = request.args.get('email', '').strip()
        if not email:
            return jsonify({'success': True, 'exists': False, 'count': 0})
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            existing = Candidate.query.filter_by(email=email).first()
            if existing:
                return jsonify({
                    'success': True,
                    'exists': True,
                    'count': 1,
                    'candidate': existing.to_dict()
                })
            return jsonify({'success': True, 'exists': False, 'count': 0})
        else:
            existing = next(
                (c for c in (ai_engine.candidate_data or []) if c.get('email') == email), None)
            if existing:
                return jsonify({
                    'success': True,
                    'exists': True,
                    'count': 1,
                    'candidate': existing
                })
            return jsonify({'success': True, 'exists': False, 'count': 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/candidates/update', methods=['PUT'])
def update_candidate_by_email():
    """Update candidate by email; merge fields; return updated candidate_id."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        if not email:
            return jsonify({'success': False, 'error': 'Email is required for update'}), 400

        # Normalize lists
        skills = data.get('skills')
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(',') if s.strip()]
        sectors = data.get('sector_interests')
        if isinstance(sectors, str):
            sectors = [s.strip() for s in sectors.split(',') if s.strip()]

        if PERSISTENCE_MODE in ('db', 'sqlite'):
            existing = Candidate.query.filter_by(email=email).first()
            if not existing:
                return jsonify({'success': False, 'error': 'Candidate not found'}), 404

            # Update only provided fields
            if 'name' in data:
                existing.name = data['name']
            if 'education_level' in data:
                existing.education_level = data['education_level']
            if skills is not None:
                existing.skills = skills
            if 'location' in data:
                existing.location = data['location']
            if sectors is not None:
                existing.sector_interests = sectors
            if 'prefers_rural' in data:
                existing.prefers_rural = bool(data['prefers_rural'])
            if 'from_rural_area' in data:
                existing.from_rural_area = bool(data['from_rural_area'])
            if 'social_category' in data:
                existing.social_category = data['social_category']
            if 'first_generation_graduate' in data:
                existing.first_generation_graduate = bool(
                    data['first_generation_graduate'])

            db.session.commit()
            analytics_cache_clear()
            # Sync to engine and snapshot for fallbacks
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()

            return jsonify({'success': True, 'candidate_id': existing.id})
        else:
            # FILE mode: update by email
            found = False
            for c in ai_engine.candidate_data or []:
                if (c.get('email') or '').strip().lower() == email.lower():
                    if 'name' in data:
                        c['name'] = data['name']
                    if 'education_level' in data:
                        c['education_level'] = data['education_level']
                    if skills is not None:
                        c['skills'] = skills
                    if 'location' in data:
                        c['location'] = data['location']
                    if sectors is not None:
                        c['sector_interests'] = sectors
                    if 'prefers_rural' in data:
                        c['prefers_rural'] = bool(data['prefers_rural'])
                    if 'from_rural_area' in data:
                        c['from_rural_area'] = bool(data['from_rural_area'])
                    if 'social_category' in data:
                        c['social_category'] = data['social_category']
                    if 'first_generation_graduate' in data:
                        c['first_generation_graduate'] = bool(
                            data['first_generation_graduate'])
                    write_snapshot_from_engine()
                    return jsonify({'success': True, 'candidate_id': c.get('id')})
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/candidates/<int:candidate_id>', methods=['PUT'])
@admin_required
def admin_update_candidate(candidate_id):
    """Admin: update candidate by ID (DB/SQLite/File modes)."""
    try:
        payload = request.get_json() or {}
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Candidate.query.get(candidate_id)
            if not obj:
                return jsonify({'success': False, 'error': 'Candidate not found'}), 404
            # Map fields if present
            for k in ['name', 'email', 'education_level', 'location', 'social_category']:
                if k in payload:
                    setattr(obj, k, payload[k])
            if 'skills' in payload:
                obj.skills = payload['skills'] if isinstance(
                    payload['skills'], list) else [payload['skills']]
            if 'sector_interests' in payload:
                obj.sector_interests = payload['sector_interests'] if isinstance(
                    payload['sector_interests'], list) else [payload['sector_interests']]
            if 'prefers_rural' in payload:
                obj.prefers_rural = bool(payload['prefers_rural'])
            if 'from_rural_area' in payload:
                obj.from_rural_area = bool(payload['from_rural_area'])
            if 'first_generation_graduate' in payload:
                obj.first_generation_graduate = bool(
                    payload['first_generation_graduate'])
            db.session.commit()
            analytics_cache_clear()
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()
            return jsonify({'success': True})
        else:
            # FILE mode
            for c in ai_engine.candidate_data or []:
                if int(c.get('id', 0)) == candidate_id:
                    for k in ['name', 'email', 'education_level', 'location', 'social_category']:
                        if k in payload:
                            c[k] = payload[k]
                    if 'skills' in payload:
                        c['skills'] = payload['skills'] if isinstance(
                            payload['skills'], list) else [payload['skills']]
                    if 'sector_interests' in payload:
                        c['sector_interests'] = payload['sector_interests'] if isinstance(
                            payload['sector_interests'], list) else [payload['sector_interests']]
                    if 'prefers_rural' in payload:
                        c['prefers_rural'] = bool(payload['prefers_rural'])
                    if 'from_rural_area' in payload:
                        c['from_rural_area'] = bool(payload['from_rural_area'])
                    if 'first_generation_graduate' in payload:
                        c['first_generation_graduate'] = bool(
                            payload['first_generation_graduate'])
                    write_snapshot_from_engine()
                    return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/candidates/<int:candidate_id>', methods=['DELETE'])
@admin_required
def admin_delete_candidate(candidate_id):
    """Admin: delete candidate by ID (DB/SQLite/File modes)."""
    try:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            obj = Candidate.query.get(candidate_id)
            if not obj:
                return jsonify({'success': False, 'error': 'Candidate not found'}), 404
            db.session.delete(obj)
            db.session.commit()
            analytics_cache_clear()
            with app.app_context():
                load_db_into_engine()
            write_snapshot_from_engine()
            return jsonify({'success': True})
        else:
            before = len(ai_engine.candidate_data or [])
            ai_engine.candidate_data = [c for c in (
                ai_engine.candidate_data or []) if int(c.get('id', 0)) != candidate_id]
            after = len(ai_engine.candidate_data or [])
            if after < before:
                write_snapshot_from_engine()
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Candidate not found'}), 404
    except SQLAlchemyError as db_err:
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            db.session.rollback()
        return jsonify({'success': False, 'error': f'Database error: {str(db_err)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/shortlist', methods=['GET'])
def shortlist_get():
    """Return shortlist items (internship details + ids) for a candidate by email."""
    try:
        email = (request.args.get('email') or '').strip()
        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400
        ids = set(_shortlist_ids(email))
        # Build internship details from whichever store is active
        if PERSISTENCE_MODE in ('db', 'sqlite'):
            items = [i.to_dict() for i in Internship.query.filter(
                Internship.id.in_(ids)).all()] if ids else []
        else:
            items = [i for i in (ai_engine.internship_data or [])
                     if int(i.get('id')) in ids]
        return jsonify({'success': True, 'ids': list(ids), 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/shortlist', methods=['POST'])
def shortlist_add():
    """Add an item to shortlist by email + internship_id."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        internship_id = data.get('internship_id')
        if not email or not internship_id:
            return jsonify({'success': False, 'error': 'email and internship_id are required'}), 400
        status = _shortlist_add(email, int(internship_id))
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/shortlist', methods=['DELETE'])
def shortlist_delete():
    """Remove an item from shortlist by email + internship_id."""
    try:
        data = request.get_json() or {}
        email = (data.get('email') or '').strip()
        internship_id = data.get('internship_id')
        if not email or not internship_id:
            return jsonify({'success': False, 'error': 'email and internship_id are required'}), 400
        status = _shortlist_remove(email, int(internship_id))
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        s = _read_settings()
        return jsonify({'success': True, 'settings': s})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['PUT'])
@admin_required
def put_settings():
    try:
        payload = request.get_json() or {}
        s = _read_settings()

        # Validate and merge weights (normalize in engine)
        if 'weights' in payload:
            w = payload['weights'] or {}
            # accept any ints; engine will normalize
            s['weights'] = {
                'skill': int(w.get('skill', w.get('skills', s['weights']['skill']))),
                'location': int(w.get('location', s['weights']['location'])),
                'education': int(w.get('education', s['weights']['education'])),
                'sector': int(w.get('sector', s['weights']['sector'])),
                'diversity': int(w.get('diversity', s['weights']['diversity'])),
            }
            ai_engine.set_weights(s['weights'])

        # Validate language
        if 'language' in payload:
            lang = payload['language'] or {}
            default = (lang.get('default') or s['language']['default'])
            enabled = lang.get('enabled') or s['language']['enabled']
            if default not in enabled:
                enabled = list(dict.fromkeys(enabled + [default]))
            s['language'] = {'default': default, 'enabled': enabled}

        if not _write_settings(s):
            return jsonify({'success': False, 'error': 'Failed to persist settings'}), 500

        return jsonify({'success': True, 'settings': s})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/import_csv', methods=['POST'])
@admin_required
def admin_import_csv():
    try:
        payload = request.get_json(silent=True) or {}
        path = (payload.get('path') or CSV_PATH).strip()
        mode = (payload.get('mode') or 'append').lower()
        if mode not in ('append', 'replace'):
            return jsonify({'success': False, 'error': 'mode must be append or replace'}), 400
        cnt = _import_csv_to_db(path, mode)
        analytics_cache_clear()
        if path == CSV_PATH:
            sig = _file_signature(path)
            if sig:
                _write_csv_meta({"path": path, **sig})
        return jsonify({'success': True, 'imported': cnt, 'mode': mode, 'path': path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/upload_csv', methods=['POST'])
@admin_required
def admin_upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'file is required'}), 400
        f = request.files['file']
        if not f.filename.lower().endswith('.csv'):
            return jsonify({'success': False, 'error': 'only .csv allowed'}), 400
        mode = (request.form.get('mode') or request.args.get(
            'mode') or 'append').lower()
        if mode not in ('append', 'replace'):
            return jsonify({'success': False, 'error': 'mode must be append or replace'}), 400

        safe = secure_filename(f.filename)
        save_path = os.path.join(
            UPLOAD_DIR, f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{safe}")
        f.save(save_path)

        cnt = _import_csv_to_db(save_path, mode)
        analytics_cache_clear()
        return jsonify({'success': True, 'imported': cnt, 'mode': mode, 'path': save_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status')
def status():
    return jsonify({
        'success': True,
        'mode': PERSISTENCE_MODE,
        'db_uri': ACTIVE_DB_URI if ACTIVE_DB_URI else None
    })


@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if session.get('is_admin'):
            nxt = request.args.get('next') or url_for('admin_dashboard')
            return redirect(nxt)

        if request.method == 'POST':
            data = request.form or request.get_json(silent=True) or {}
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            if username == ADMIN_USER and check_password_hash(ADMIN_PASSWORD_HASH, password):
                session['is_admin'] = True
                session['admin_user'] = username
                nxt = request.args.get('next') or url_for('admin_dashboard')
                if request.is_json:
                    return jsonify({'success': True, 'redirect': nxt})
                return redirect(nxt)
            if request.is_json:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            return render_template('login.html', error='Invalid credentials', next=request.args.get('next') or '')
        return render_template('login.html', next=request.args.get('next') or '')
    except Exception as e:
        return render_template('login.html', error=str(e))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
