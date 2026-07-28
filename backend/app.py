"""
PlantAI Backend — FastAPI
Pipeline IA unique : CNN Keras (ia/model.py, voir ia/train_model.py pour l'entraînement).
MongoDB — 4 collections : utilisateurs, analyses, capteurs, recommandations.
"""

import os
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

import requests as http_requests
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from auth import generate_token, get_current_user, hash_password, require_role, verify_password
from database import (
    get_analyses_col, get_capteurs_col, get_db, get_recommandations_col, get_utilisateurs_col, serialize,
)
from disease_catalog import CLASS_INFO
from schemas import ESP32CaptureRequest, LoginRequest, SensorData, UserCreate, UserUpdate

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

app = FastAPI(title="PlantAI Backend", description="Détection des maladies des plantes — CNN Keras")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Le frontend attend {"error": "..."} — FastAPI renvoie {"detail": "..."} par défaut."""
    return JSONResponse(status_code=exc.status_code, content={'error': exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Corps de requête invalide (422) — même format {"error": "..."} pour le frontend."""
    first = exc.errors()[0] if exc.errors() else {}
    field = '.'.join(str(p) for p in first.get('loc', []) if p != 'body')
    message = f"{field} : {first.get('msg')}" if field else (first.get('msg') or 'Requête invalide')
    return JSONResponse(status_code=422, content={'error': message})

# ── Configuration uploads ──────────────────────────────────────────────────────
UPLOAD_FOLDER      = 'uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 Mo
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Configuration ESP32 ────────────────────────────────────────────────────────
ESP32_DEFAULT_IP      = os.getenv('ESP32_IP', '')
ESP32_CONNECT_TIMEOUT = 8
ESP32_CAPTURE_TIMEOUT = 8

SENSOR_LINK_WINDOW_SECONDS = 120


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _predict_cnn(img_path: str) -> dict:
    """Import paresseux du CNN Keras (ia/model.py) : ne bloque pas le démarrage
    de l'API si TensorFlow / le modèle entraîné ne sont pas encore disponibles."""
    ia_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ia')
    if ia_dir not in sys.path:
        sys.path.insert(0, ia_dir)
    from model import predict_image
    return predict_image(img_path)


def _enrich_prediction(raw: dict) -> dict:
    """Ajoute les infos du catalogue (plante, niveau, traitement…) à la sortie brute du CNN."""
    label = raw.get('maladie')
    info = CLASS_INFO.get(label)
    if info is None:
        disease_info = {
            'plante':      'Inconnue',
            'maladie':     label or 'Inconnue',
            'niveau':      'unknown',
            'description': f"Détection : {label}" if label else "Aucune détection.",
            'traitement':  'Non applicable.',
            'conseil':     'Résultat non référencé dans le catalogue PlantVillage.',
        }
    else:
        disease_info = dict(info)
    return {
        'maladie':     label,
        'confiance':   raw.get('confiance'),
        'diseaseInfo': disease_info,
    }


def _persist_image_file(tmp_path: str, nom_image: str) -> tuple[dict, str]:
    """Rend l'image permanente (nom unique) et retourne le sous-document image
    à embarquer directement dans le document 'analyses'."""
    ext = os.path.splitext(tmp_path)[1] or os.path.splitext(nom_image)[1] or '.jpg'
    unique_name    = f"{uuid.uuid4().hex}{ext}"
    permanent_path = os.path.join(UPLOAD_FOLDER, unique_name)
    os.replace(tmp_path, permanent_path)
    image_doc = {
        'nomImage':    nom_image,
        'cheminImage': unique_name,
        'dateCapture': datetime.now(timezone.utc),
    }
    return image_doc, permanent_path


def _link_recommandation(entry: dict, result: dict):
    """Rattache l'Analyse à la Recommandation correspondante via codeLabel.
    N'échoue jamais — une plante saine ou un code non référencé n'a simplement pas de recommandationId."""
    col = get_recommandations_col()
    if col is None:
        return
    code_label = result.get('maladie')
    if not code_label:
        return
    reco = col.find_one({'codeLabel': code_label})
    if reco:
        entry['recommandationId'] = str(reco['_id'])


def _link_recent_capteurs(analyse_id: str):
    """Rattache à cette Analyse les données 'capteurs' reçues récemment et pas
    encore liées à une analyse. N'échoue jamais si aucune donnée récente n'existe."""
    col = get_capteurs_col()
    if col is None:
        return
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=SENSOR_LINK_WINDOW_SECONDS)
    col.update_many(
        {'analyseId': {'$exists': False}, 'dateMesure': {'$gte': cutoff}},
        {'$set': {'analyseId': analyse_id}},
    )


def _save_analysis(entry: dict):
    col = get_analyses_col()
    if col is None:
        return None
    try:
        result = col.insert_one(entry)
        return str(result.inserted_id)
    except Exception as e:
        print(f"⚠️  Erreur sauvegarde 'analyses' : {e}")
        return None


def _recommandation_to_dict(doc: dict) -> dict:
    return {
        'idRecommandation':   str(doc['_id']),
        'codeLabel':          doc.get('codeLabel'),
        'plante':             doc.get('plante'),
        'maladie':            doc.get('maladie'),
        'niveau':             doc.get('niveau'),
        'description':        doc.get('description'),
        'traitement':         doc.get('traitement'),
        'texte':              doc.get('conseil'),
        'produitsConseilles': doc.get('produitsConseilles', []),
    }


def _user_to_dict(doc: dict) -> dict:
    """Sérialise un document utilisateur pour l'API — ne renvoie jamais motDePasse."""
    out = {
        'idUtilisateur': str(doc['_id']),
        'nom':           doc.get('nom'),
        'prenom':        doc.get('prenom'),
        'email':         doc.get('email'),
        'role':          doc.get('role'),
    }
    if doc.get('role') == 'maraicher':
        out['exploitation'] = doc.get('exploitation')
    return out


def _object_id(raw_id: str) -> ObjectId:
    try:
        return ObjectId(raw_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=400, detail='Identifiant invalide')


# ══════════════════════════════════════════════════════════════════════════════
# ── ROUTE ACCUEIL ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/')
def home():
    return {
        'status':    'ok',
        'message':   'PlantAI Backend opérationnel',
        'endpoints': {
            '/auth/login':           'POST  — Connexion (email + motDePasse) → token + rôle',
            '/auth/logout':          'POST  — Déconnexion (authentifié)',
            '/api/predict':          'POST  — Analyser une image (CNN Keras, seul pipeline IA)',
            '/api/esp32/status':     'GET   — Vérifier la connexion ESP32-CAM',
            '/api/esp32/capture':    'POST  — Capturer depuis ESP32-CAM et analyser',
            '/api/esp32/stream':     'GET   — Proxy du flux MJPEG ESP32',
            '/api/history':          'GET/POST/DELETE — Historique des analyses (legacy, non authentifié)',
            '/history':              "GET   — Historique de l'utilisateur connecté (authentifié)",
            '/users':                'GET/POST — Gestion des utilisateurs (administrateur)',
            '/users/{id}':           'PUT/DELETE — Modifier/supprimer un utilisateur (administrateur)',
            '/sensors/data':         'GET/POST — Données capteurs (température/humidité)',
            '/sensors/data/simulate':'POST — Simule l\'envoi de données capteur (test)',
            '/recommandations':      'GET — Catalogue maladie + recommandation',
            '/recommandations/{id}': 'GET — Détail d\'une recommandation',
            '/images/{id}':          "GET — Image d'une analyse",
            '/health':               'GET   — Santé du service',
        },
    }


@app.get('/health')
def health():
    db_ok = get_db() is not None
    return {'status': 'healthy', 'mongodb': 'connected' if db_ok else 'unavailable'}


# ══════════════════════════════════════════════════════════════════════════════
# ── AUTHENTIFICATION ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.post('/auth/login')
def login(payload: LoginRequest):
    email        = payload.email.strip().lower()
    mot_de_passe = payload.motDePasse

    if not email or not mot_de_passe:
        raise HTTPException(status_code=400, detail='Email et mot de passe requis')

    col = get_utilisateurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')

    user = col.find_one({'email': email})
    if user is None or not verify_password(mot_de_passe, user['motDePasse']):
        raise HTTPException(status_code=401, detail='Identifiants invalides')

    user_out = _user_to_dict(user)
    token = generate_token({
        'idUtilisateur': user_out['idUtilisateur'],
        'email':         user_out['email'],
        'role':          user_out['role'],
    })
    return {'token': token, **user_out}


@app.post('/auth/logout')
def logout(current_user: dict = Depends(get_current_user)):
    # JWT stateless : la déconnexion est gérée côté client (suppression du token).
    return {'ok': True, 'message': 'Déconnecté'}


# ══════════════════════════════════════════════════════════════════════════════
# ── PRÉDICTION SUR IMAGE UPLOADÉE (CNN Keras — pipeline unique) ──────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.post('/api/predict')
def predict(
    image: UploadFile = File(...),
    current_user: dict = Depends(require_role('maraicher')),
):
    if image.filename == '':
        raise HTTPException(status_code=400, detail='Nom de fichier vide')
    if not allowed_file(image.filename):
        raise HTTPException(status_code=400, detail='Format non autorisé. Acceptés : png, jpg, jpeg, gif, webp')

    contents = image.file.read()
    if len(contents) > MAX_CONTENT_LENGTH:
        raise HTTPException(status_code=413, detail='Fichier trop volumineux. Maximum : 16 Mo')

    filename = os.path.basename(image.filename)
    tmp_path = os.path.join(UPLOAD_FOLDER, f"tmp_{uuid.uuid4().hex}_{filename}")
    with open(tmp_path, 'wb') as f:
        f.write(contents)

    try:
        image_doc, img_path = _persist_image_file(tmp_path, filename)
        raw = _predict_cnn(img_path)
        result = _enrich_prediction(raw)
    except ModuleNotFoundError:
        raise HTTPException(status_code=503, detail="Modèle CNN indisponible — installez requirements.txt (tensorflow)")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Erreur prédiction : {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors du traitement de l'image")

    entry = {
        **result,
        'image':   image_doc,
        'source':  'api',
        'date':    datetime.now(timezone.utc),
        'userId':  current_user['idUtilisateur'],
    }
    _link_recommandation(entry, result)
    db_id = _save_analysis(entry)
    if db_id:
        result['idAnalyse'] = db_id
        _link_recent_capteurs(db_id)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# ── ESP32-CAM : STATUT DE CONNEXION ───────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/api/esp32/status')
def esp32_status(ip: str = Query(default=None)):
    ip = (ip or ESP32_DEFAULT_IP).strip()

    if not ip:
        return {'connected': False, 'ip': None, 'message': 'Adresse IP ESP32 non configurée'}

    capture_url = f'http://{ip}/capture'
    try:
        r = http_requests.get(capture_url, timeout=ESP32_CONNECT_TIMEOUT, stream=True)
        r.close()
        connected = r.status_code == 200
        return {
            'connected':   connected,
            'ip':          ip,
            'stream_url':  f'http://{ip}:81/stream',
            'capture_url': capture_url,
            'message':     'ESP32-CAM connectée et opérationnelle' if connected else f'HTTP {r.status_code}',
        }
    except http_requests.exceptions.ConnectTimeout:
        return {'connected': False, 'ip': ip, 'message': 'Hôte injoignable (timeout)'}
    except http_requests.exceptions.ConnectionError:
        return {'connected': False, 'ip': ip, 'message': "Connexion refusée — vérifiez l'IP et le WiFi"}
    except Exception as e:
        return {'connected': False, 'ip': ip, 'message': str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# ── ESP32 : DONNÉES CAPTEURS IoT (DHT11 + humidité sol) ───────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/api/esp32/sensors')
def esp32_sensors(ip: str = Query(default=None)):
    ip = (ip or ESP32_DEFAULT_IP).strip()
    if not ip:
        raise HTTPException(status_code=400, detail='Adresse IP ESP32 non fournie')
    try:
        r = http_requests.get(f'http://{ip}/sensors', timeout=5)
        r.raise_for_status()
        return r.json()
    except http_requests.exceptions.ConnectTimeout:
        raise HTTPException(status_code=504, detail='Timeout — ESP32 injoignable')
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail='Connexion refusée')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# ── ESP32-CAM : CAPTURER ET ANALYSER ──────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.post('/api/esp32/capture')
def esp32_capture(
    payload: ESP32CaptureRequest = ESP32CaptureRequest(),
    current_user: dict = Depends(require_role('maraicher')),
):
    ip = (payload.ip or ESP32_DEFAULT_IP).strip()
    if not ip:
        raise HTTPException(status_code=400, detail='Adresse IP ESP32 non fournie')

    capture_url = f'http://{ip}/capture'
    try:
        r = http_requests.get(capture_url, timeout=ESP32_CAPTURE_TIMEOUT)
        r.raise_for_status()
        if 'image' not in r.headers.get('Content-Type', ''):
            raise HTTPException(status_code=502, detail="L'ESP32 n'a pas renvoyé une image valide")

        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False, dir=UPLOAD_FOLDER) as f:
            f.write(r.content)
            tmp_path = f.name

        image_doc, img_path = _persist_image_file(tmp_path, f'ESP32-CAM_{ip}.jpg')
        raw = _predict_cnn(img_path)
        result = _enrich_prediction(raw)
        result['source']   = 'esp32'
        result['esp32_ip'] = ip

    except http_requests.exceptions.ConnectTimeout:
        raise HTTPException(status_code=504, detail=f'ESP32 injoignable à {ip} (timeout)')
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail=f"Impossible de se connecter à {ip} — vérifiez l'IP")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f'ESP32 erreur HTTP : {e}')
    except HTTPException:
        raise
    except ModuleNotFoundError:
        raise HTTPException(status_code=503, detail="Modèle CNN indisponible — installez requirements.txt (tensorflow)")
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Erreur ESP32 capture : {e}")
        raise HTTPException(status_code=500, detail=f'Erreur interne : {str(e)}')

    entry = {
        **result,
        'image':   image_doc,
        'date':    datetime.now(timezone.utc),
        'userId':  current_user['idUtilisateur'],
    }
    _link_recommandation(entry, result)
    db_id = _save_analysis(entry)
    if db_id:
        result['idAnalyse'] = db_id
        _link_recent_capteurs(db_id)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# ── ESP32-CAM : PROXY DU FLUX MJPEG ───────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/api/esp32/stream')
def esp32_stream_proxy(ip: str = Query(default=None)):
    ip = (ip or ESP32_DEFAULT_IP).strip()
    if not ip:
        raise HTTPException(status_code=400, detail='IP manquante')

    stream_url = f'http://{ip}:81/stream'
    try:
        esp32_response = http_requests.get(stream_url, stream=True, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    def generate():
        try:
            for chunk in esp32_response.iter_content(chunk_size=4096):
                yield chunk
        except Exception:
            pass

    return StreamingResponse(
        generate(),
        media_type=esp32_response.headers.get('Content-Type', 'multipart/x-mixed-replace'),
    )


# ══════════════════════════════════════════════════════════════════════════════
# ── HISTORIQUE DES ANALYSES (legacy, non authentifié) ─────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/api/history')
def get_history():
    """Retourne les 200 dernières analyses triées du plus récent au plus ancien."""
    col = get_analyses_col()
    if col is None:
        return []
    from pymongo import DESCENDING
    records = list(col.find({}).sort('date', DESCENDING).limit(200))
    return [serialize(r) for r in records]


@app.post('/api/history', status_code=201)
def post_history(record: dict):
    col = get_analyses_col()
    if col is None:
        raise HTTPException(status_code=503, detail='MongoDB non disponible')
    raw_date = record.get('date')
    if isinstance(raw_date, str):
        try:
            record['date'] = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            record['date'] = datetime.now(timezone.utc)
    else:
        record['date'] = datetime.now(timezone.utc)
    result = col.insert_one(record)
    return {'ok': True, 'idAnalyse': str(result.inserted_id)}


@app.delete('/api/history/{analyse_id}')
def delete_one_history(analyse_id: str):
    col = get_analyses_col()
    if col is None:
        raise HTTPException(status_code=503, detail='MongoDB non disponible')
    col.delete_one({'_id': _object_id(analyse_id)})
    return {'ok': True}


@app.delete('/api/history')
def clear_history():
    col = get_analyses_col()
    if col is None:
        raise HTTPException(status_code=503, detail='MongoDB non disponible')
    col.delete_many({})
    return {'ok': True}


# ══════════════════════════════════════════════════════════════════════════════
# ── HISTORIQUE DE L'UTILISATEUR CONNECTÉ ──────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/history')
def get_user_history(current_user: dict = Depends(require_role('maraicher', 'administrateur'))):
    """Maraîcher : ses propres analyses. Administrateur : toutes les analyses."""
    col = get_analyses_col()
    if col is None:
        return []
    query = {}
    if current_user.get('role') != 'administrateur':
        query['userId'] = current_user['idUtilisateur']
    from pymongo import DESCENDING
    records = list(col.find(query).sort('date', DESCENDING).limit(200))
    return [serialize(r) for r in records]


# ══════════════════════════════════════════════════════════════════════════════
# ── GESTION DES UTILISATEURS (réservée à l'Administrateur) ───────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/users')
def list_users(current_user: dict = Depends(require_role('administrateur'))):
    col = get_utilisateurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')
    return [_user_to_dict(u) for u in col.find({})]


@app.post('/users', status_code=201)
def create_user(payload: UserCreate, current_user: dict = Depends(require_role('administrateur'))):
    nom          = payload.nom.strip()
    email        = payload.email.strip().lower()
    mot_de_passe = payload.motDePasse
    role         = payload.role or 'maraicher'

    if not nom or not email or not mot_de_passe:
        raise HTTPException(status_code=400, detail='nom, email et motDePasse sont requis')
    if role not in ('administrateur', 'maraicher'):
        raise HTTPException(status_code=400, detail="role doit être 'administrateur' ou 'maraicher'")

    col = get_utilisateurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')

    doc = {
        'nom': nom, 'prenom': payload.prenom, 'email': email,
        'motDePasse': hash_password(mot_de_passe), 'role': role,
    }
    if role == 'maraicher':
        doc['exploitation'] = payload.exploitation

    try:
        result = col.insert_one(doc)
        doc['_id'] = result.inserted_id
        return _user_to_dict(doc)
    except Exception as e:
        if 'duplicate key' in str(e).lower():
            raise HTTPException(status_code=409, detail='Cet email est déjà utilisé')
        raise HTTPException(status_code=500, detail=str(e))


@app.put('/users/{user_id}')
def update_user(user_id: str, payload: UserUpdate, current_user: dict = Depends(require_role('administrateur'))):
    updates = {k: v for k, v in payload.model_dump(exclude={'motDePasse'}).items() if v is not None}
    if payload.motDePasse:
        updates['motDePasse'] = hash_password(payload.motDePasse)

    if not updates:
        raise HTTPException(status_code=400, detail='Aucun champ à mettre à jour')

    col = get_utilisateurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')

    result = col.find_one_and_update(
        {'_id': _object_id(user_id)}, {'$set': updates},
        return_document=True,
    )
    if result is None:
        raise HTTPException(status_code=404, detail='Utilisateur introuvable')
    return _user_to_dict(result)


@app.delete('/users/{user_id}')
def delete_user(user_id: str, current_user: dict = Depends(require_role('administrateur'))):
    col = get_utilisateurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')
    result = col.delete_one({'_id': _object_id(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Utilisateur introuvable')
    return {'ok': True}


# ══════════════════════════════════════════════════════════════════════════════
# ── DONNÉES CAPTEURS (température/humidité air, humidité sol) ────────────────
# ══════════════════════════════════════════════════════════════════════════════
EXEMPLE_DONNEES_CAPTEUR = {
    'temperatureAir': 24.5,
    'humiditeAir':    62.0,
    'humiditeSol':    38.0,
}


def _insert_sensor_reading(data: dict) -> str:
    col = get_capteurs_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')

    raw_date = data.get('dateMesure')
    if isinstance(raw_date, str):
        try:
            date_mesure = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
        except ValueError:
            date_mesure = datetime.now(timezone.utc)
    else:
        date_mesure = datetime.now(timezone.utc)

    doc = {
        'temperatureAir': float(data['temperatureAir']),
        'humiditeAir':    float(data['humiditeAir']),
        'humiditeSol':    float(data['humiditeSol']),
        'dateMesure':     date_mesure,
    }
    if data.get('analyseId'):
        doc['analyseId'] = data['analyseId']

    result = col.insert_one(doc)
    return str(result.inserted_id)


@app.post('/sensors/data', status_code=201)
def post_sensor_data(payload: SensorData):
    """Appelé par le capteur physique (ESP32 devkit) — pas d'authentification requise."""
    inserted_id = _insert_sensor_reading(payload.model_dump())
    return {'ok': True, 'id': inserted_id}


@app.post('/sensors/data/simulate', status_code=201)
def simulate_sensor_data():
    """Route de test : simule l'envoi de données par un capteur, sans matériel réel."""
    inserted_id = _insert_sensor_reading(dict(EXEMPLE_DONNEES_CAPTEUR))
    return {'ok': True, 'id': inserted_id, 'donnees_simulees': EXEMPLE_DONNEES_CAPTEUR}


@app.get('/sensors/data')
def get_sensor_data(current_user: dict = Depends(require_role('maraicher'))):
    col = get_capteurs_col()
    if col is None:
        return []
    records = list(col.find({}).sort('dateMesure', -1).limit(200))
    return [serialize(r) for r in records]


# ══════════════════════════════════════════════════════════════════════════════
# ── IMAGE D'UNE ANALYSE (embarquée dans le document 'analyses') ──────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/images/{analyse_id}')
def get_image(analyse_id: str):
    col = get_analyses_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')
    doc = col.find_one({'_id': _object_id(analyse_id)})
    if doc is None or not doc.get('image'):
        raise HTTPException(status_code=404, detail='Image introuvable')
    chemin = os.path.join(os.path.abspath(UPLOAD_FOLDER), doc['image']['cheminImage'])
    if not os.path.exists(chemin):
        raise HTTPException(status_code=404, detail='Image introuvable')
    return FileResponse(chemin)


# ══════════════════════════════════════════════════════════════════════════════
# ── CATALOGUE MALADIE + RECOMMANDATION (collection unique) ───────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.get('/recommandations')
def list_recommandations():
    col = get_recommandations_col()
    if col is None:
        return []
    return [_recommandation_to_dict(r) for r in col.find({})]


@app.get('/recommandations/{recommandation_id}')
def get_recommandation(recommandation_id: str):
    col = get_recommandations_col()
    if col is None:
        raise HTTPException(status_code=503, detail='Base de données indisponible')
    doc = col.find_one({'_id': _object_id(recommandation_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail='Recommandation introuvable')
    return _recommandation_to_dict(doc)


# ══════════════════════════════════════════════════════════════════════════════
# ── DÉMARRAGE ─────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
@app.on_event('startup')
def on_startup():
    get_db()  # initialise la connexion MongoDB au démarrage
    print(f"\n🌿  PlantAI Backend démarré (FastAPI)")
    print(f"📡  ESP32 par défaut          : {ESP32_DEFAULT_IP or 'non configuré'}")
    print(f"🧠  Modèle                    : CNN Keras (ia/model.py)\n")
