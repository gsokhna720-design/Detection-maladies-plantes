"""
Test des priorités 1 à 4 (auth, historique, utilisateurs, capteurs) via
FastAPI TestClient + mongomock (MongoDB en mémoire, aucun serveur requis).

Usage :
  cd backend
  pip install mongomock httpx   # dépendances de test uniquement, pas en prod
  python test_priorities.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import mongomock
from bson import ObjectId

# ── Injection d'une base MongoDB en mémoire AVANT d'importer app (bypass la
#    vraie connexion — database.get_db() retournera directement ce mock) ─────
import database
mock_db = mongomock.MongoClient()['plantai']
database._db = mock_db

import app as app_module
from auth import hash_password
from fastapi.testclient import TestClient

client = TestClient(app_module.app)

passed = failed = 0


def check(label, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label}")


# ══════════════════════════════════════════════════════════════════════════════
print("\n=== PRIORITÉ 1 — Authentification ===")

mock_db['utilisateurs'].insert_one({
    'nom': 'Diallo', 'prenom': 'Fatou', 'email': 'admin@plantai.test',
    'motDePasse': hash_password('admin123'), 'role': 'administrateur',
})
mock_db['utilisateurs'].insert_one({
    'nom': 'Ba', 'prenom': 'Moussa', 'email': 'marai@plantai.test',
    'motDePasse': hash_password('champs123'), 'role': 'maraicher', 'exploitation': 'Ferme du Nord',
})

r = client.post('/auth/login', json={'email': 'admin@plantai.test', 'motDePasse': 'mauvais'})
check("login refusé si mauvais mot de passe (401)", r.status_code == 401)

r = client.post('/auth/login', json={'email': 'admin@plantai.test', 'motDePasse': 'admin123'})
check("login admin réussi (200)", r.status_code == 200)
admin_token = r.json().get('token')
check("token présent", bool(admin_token))
check("role renvoyé = administrateur", r.json().get('role') == 'administrateur')

r = client.post('/auth/login', json={'email': 'marai@plantai.test', 'motDePasse': 'champs123'})
check("login maraîcher réussi (200)", r.status_code == 200)
marai_data = r.json()
marai_token = marai_data['token']
marai_id    = marai_data['idUtilisateur']

r = client.get('/users')
check("route protégée sans token → 401", r.status_code == 401)

r = client.get('/users', headers={'Authorization': f'Bearer {marai_token}'})
check("route admin refusée pour un maraîcher → 403", r.status_code == 403)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== PRIORITÉ 2 — Historique des analyses ===")

mock_db['analyses'].insert_one({
    'maladie': 'Tomato___Late_blight', 'confiance': 0.91,
    'diseaseInfo': {'maladie': 'Mildiou'}, 'image': {'nomImage': 'feuille1.jpg'},
    'source': 'api', 'date': datetime.now(timezone.utc), 'userId': marai_id,
})
mock_db['analyses'].insert_one({
    'maladie': 'Apple___healthy', 'confiance': 0.97,
    'diseaseInfo': {'maladie': None}, 'image': {'nomImage': 'feuille2.jpg'},
    'source': 'api', 'date': datetime.now(timezone.utc), 'userId': 'un-autre-user',
})

r = client.get('/history')
check("historique sans token → 401", r.status_code == 401)

r = client.get('/history', headers={'Authorization': f'Bearer {marai_token}'})
data = r.json()
check("maraîcher voit uniquement ses analyses (1)", r.status_code == 200 and len(data) == 1)
check("champ maladie correct", data and data[0]['diseaseInfo']['maladie'] == 'Mildiou')

r = client.get('/history', headers={'Authorization': f'Bearer {admin_token}'})
data = r.json()
check("admin voit toutes les analyses (2)", r.status_code == 200 and len(data) == 2)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== PRIORITÉ 3 — Gestion des utilisateurs (admin) ===")

r = client.post('/users', headers={'Authorization': f'Bearer {marai_token}'},
                 json={'nom': 'X', 'email': 'x@x.test', 'motDePasse': 'x', 'role': 'maraicher'})
check("création utilisateur refusée pour un maraîcher → 403", r.status_code == 403)

r = client.post('/users', headers={'Authorization': f'Bearer {admin_token}'}, json={
    'nom': 'Sow', 'prenom': 'Awa', 'email': 'awa@plantai.test',
    'motDePasse': 'motdepasse1', 'role': 'maraicher', 'exploitation': 'Verger Sud',
})
check("admin crée un utilisateur (201)", r.status_code == 201)
new_user_id = r.json()['idUtilisateur']
check("motDePasse absent de la réponse", 'motDePasse' not in r.json())

r = client.get('/users', headers={'Authorization': f'Bearer {admin_token}'})
check("liste des utilisateurs = 3", len(r.json()) == 3)

r = client.put(f'/users/{new_user_id}', headers={'Authorization': f'Bearer {admin_token}'},
                json={'exploitation': 'Verger Sud-Est'})
check("admin modifie un utilisateur (200)", r.status_code == 200 and r.json()['exploitation'] == 'Verger Sud-Est')

r = client.delete(f'/users/{new_user_id}', headers={'Authorization': f'Bearer {admin_token}'})
check("admin supprime un utilisateur (200)", r.status_code == 200)

r = client.get('/users', headers={'Authorization': f'Bearer {admin_token}'})
check("liste des utilisateurs revenue à 2", len(r.json()) == 2)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== PRIORITÉ 4 — Données capteurs ===")

r = client.post('/sensors/data/simulate')
check("simulation capteur (201, sans auth)", r.status_code == 201)

r = client.post('/sensors/data', json={
    'temperatureAir': 21.3, 'humiditeAir': 55.2, 'humiditeSol': 40.1,
})
check("envoi manuel de données capteur (201)", r.status_code == 201)

r = client.post('/sensors/data', json={'temperatureAir': 20})
check("champ manquant → 422", r.status_code == 422)

r = client.get('/sensors/data')
check("lecture capteurs sans token → 401", r.status_code == 401)

r = client.get('/sensors/data', headers={'Authorization': f'Bearer {marai_token}'})
check("lecture capteurs avec token → 200, 2 entrées", r.status_code == 200 and len(r.json()) == 2)

r = client.get('/sensors/data', headers={'Authorization': f'Bearer {admin_token}'})
check("lecture capteurs refusée pour un admin → 403 (route Maraîcher)", r.status_code == 403)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== SÉCURITÉ — rôle strict sur les routes Maraîcher ===")
# require_role() rejette avant même de valider le corps de la requête,
# donc ces routes peuvent être testées sans image ni modèle IA chargé.

for route in ('/api/predict', '/api/esp32/capture'):
    r = client.post(route)
    check(f"{route} sans token → 401", r.status_code == 401)

    r = client.post(route, headers={'Authorization': f'Bearer {admin_token}'})
    check(f"{route} avec un admin (mauvais rôle) → 403", r.status_code == 403)

    r = client.post(route, headers={'Authorization': f'Bearer {marai_token}'})
    check(f"{route} avec un maraîcher → passe le contrôle de rôle (pas de 401/403)", r.status_code not in (401, 403))

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ÉTAPE 2 — Catalogue Recommandations (maladie + conseils fusionnés) ===")

reco_id = mock_db['recommandations'].insert_one({
    'codeLabel': 'Test___Rouille', 'plante': 'Test 🌿', 'maladie': 'Rouille test',
    'niveau': 'sick', 'description': 'desc', 'traitement': 'Fongicide',
    'conseil': 'Traiter rapidement', 'produitsConseilles': ['Cuivre', 'Soufre'],
}).inserted_id

entry = {}
app_module._link_recommandation(entry, {'maladie': 'Test___Rouille'})
check("_link_recommandation rattache recommandationId depuis result['maladie']",
      entry.get('recommandationId') == str(reco_id))

entry2 = {}
app_module._link_recommandation(entry2, {'maladie': 'Inconnu___XYZ'})
check("_link_recommandation ignore silencieusement un code non référencé", 'recommandationId' not in entry2)

r = client.get('/recommandations')
check("GET /recommandations liste le catalogue", r.status_code == 200 and len(r.json()) == 1)

r = client.get(f'/recommandations/{reco_id}')
data = r.json()
check("GET /recommandations/<id> renvoie maladie + conseils",
      r.status_code == 200 and data['maladie'] == 'Rouille test' and data['texte'] == 'Traiter rapidement')

r = client.get('/recommandations/000000000000000000000000')
check("GET /recommandations/<id inexistant> → 404", r.status_code == 404)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ÉTAPE 3 — Persistance des images (embarquées dans 'analyses') ===")

os.makedirs(app_module.UPLOAD_FOLDER, exist_ok=True)
fake_upload = os.path.join(app_module.UPLOAD_FOLDER, 'test_upload.jpg')
with open(fake_upload, 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0FAKEJPEGDATA')

image_doc, permanent_path = app_module._persist_image_file(fake_upload, 'feuille_test.jpg')
check("_persist_image_file renvoie nomImage/cheminImage/dateCapture",
      image_doc['nomImage'] == 'feuille_test.jpg' and 'cheminImage' in image_doc and 'dateCapture' in image_doc)
check("_persist_image_file renomme vers un chemin permanent unique",
      permanent_path != fake_upload and os.path.exists(permanent_path))
check("l'ancien chemin temporaire n'existe plus (renommé, pas copié)", not os.path.exists(fake_upload))

analyse_id = mock_db['analyses'].insert_one({
    'maladie': 'Test___Rouille', 'confiance': 0.8, 'image': image_doc,
    'source': 'api', 'date': datetime.now(timezone.utc), 'userId': marai_id,
}).inserted_id

r = client.get(f'/images/{analyse_id}')
check("GET /images/<id> sert le fichier (200)", r.status_code == 200)

r = client.get('/images/000000000000000000000000')
check("GET /images/<id inexistant> → 404", r.status_code == 404)

os.remove(permanent_path)  # nettoyage du fichier de test

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ÉTAPE 4 — Rattachement automatique idAnalyse ↔ données capteurs ===")

recent_id = mock_db['capteurs'].insert_one({
    'temperatureAir': 22.0, 'humiditeAir': 60.0, 'humiditeSol': 35.0,
    'dateMesure': datetime.now(timezone.utc),
}).inserted_id

old_id = mock_db['capteurs'].insert_one({
    'temperatureAir': 18.0, 'humiditeAir': 50.0, 'humiditeSol': 30.0,
    'dateMesure': datetime.now(timezone.utc) - timedelta(seconds=999),
}).inserted_id

already_linked_id = mock_db['capteurs'].insert_one({
    'temperatureAir': 20.0, 'humiditeAir': 55.0, 'humiditeSol': 32.0,
    'dateMesure': datetime.now(timezone.utc), 'analyseId': 'une-autre-analyse',
}).inserted_id

app_module._link_recent_capteurs('analyse-test-1')

recent_doc  = mock_db['capteurs'].find_one({'_id': recent_id})
old_doc     = mock_db['capteurs'].find_one({'_id': old_id})
already_doc = mock_db['capteurs'].find_one({'_id': already_linked_id})

check("donnée récente sans analyseId → rattachée à la nouvelle analyse",
      recent_doc.get('analyseId') == 'analyse-test-1')
check("donnée ancienne (hors fenêtre) → non rattachée", 'analyseId' not in old_doc)
check("donnée déjà rattachée à une autre analyse → non écrasée",
      already_doc.get('analyseId') == 'une-autre-analyse')

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ÉTAPE 5 — Cultures cibles (5 avec IA / 2 sans IA) ===")

r = client.get('/cultures')
data = r.json()
check("GET /cultures → 200, 7 cultures", r.status_code == 200 and len(data) == 7)
ia_ids = {c['id'] for c in data if c['iaDisponible']}
sans_ia_ids = {c['id'] for c in data if not c['iaDisponible']}
check("5 cultures avec IA", ia_ids == {'tomate', 'aubergine', 'salade', 'oignon_vert', 'aloe_vera'})
check("2 cultures sans IA (persil, menthe)", sans_ia_ids == {'persil', 'menthe'})
check("les cultures sans IA ont un message explicite",
      all(c.get('message') for c in data if not c['iaDisponible']))

# /api/predict sur une culture sans IA → message clair, pas d'appel au modèle
fake_img = os.path.join(app_module.UPLOAD_FOLDER, 'persil_test.jpg')
os.makedirs(app_module.UPLOAD_FOLDER, exist_ok=True)
with open(fake_img, 'wb') as f:
    f.write(b'\xff\xd8\xff\xe0FAKEJPEGDATA')

with open(fake_img, 'rb') as f:
    r = client.post('/api/predict', headers={'Authorization': f'Bearer {marai_token}'},
                     data={'culture': 'persil'}, files={'image': ('persil_test.jpg', f, 'image/jpeg')})
check("POST /api/predict culture=persil → 200, iaDisponible=False",
      r.status_code == 200 and r.json().get('iaDisponible') is False and r.json().get('message'))

with open(fake_img, 'rb') as f:
    r = client.post('/api/predict', headers={'Authorization': f'Bearer {marai_token}'},
                     data={'culture': 'inconnue_xyz'}, files={'image': ('x.jpg', f, 'image/jpeg')})
check("POST /api/predict culture inconnue → 400", r.status_code == 400)

os.remove(fake_img)

# ══════════════════════════════════════════════════════════════════════════════
print("\n=== ÉTAPE 6 — Signalement manuel (Persil / Menthe) ===")

r = client.post('/api/observations', data={'culture': 'menthe', 'note': 'Taches jaunes sur les feuilles.'})
check("POST /api/observations sans token → 401", r.status_code == 401)

r = client.post('/api/observations', headers={'Authorization': f'Bearer {marai_token}'},
                 data={'culture': 'menthe', 'note': 'Taches jaunes sur les feuilles.'})
check("POST /api/observations sans image (201)", r.status_code == 201)
obs_id = r.json().get('idAnalyse')
check("idAnalyse renvoyé", bool(obs_id))

obs_doc = mock_db['analyses'].find_one({'_id': ObjectId(obs_id)})
check("document sauvegardé avec type='manuelle'", obs_doc is not None and obs_doc.get('type') == 'manuelle')
check("document sans champ 'maladie' (pas un diagnostic IA)", 'maladie' not in obs_doc or obs_doc.get('maladie') is None)

r = client.post('/api/observations', headers={'Authorization': f'Bearer {marai_token}'},
                 data={'culture': 'menthe', 'note': '   '})
check("note vide → 400", r.status_code == 400)

r = client.post('/api/observations', headers={'Authorization': f'Bearer {marai_token}'},
                 data={'culture': 'xyz', 'note': 'test'})
check("culture inconnue → 400", r.status_code == 400)

# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*50}\nRésultat : {passed} réussis / {failed} échoués\n{'='*50}")
sys.exit(1 if failed else 0)
