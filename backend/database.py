"""
MongoDB — 4 collections consolidées :
  utilisateurs    : comptes (administrateur / maraicher)
  analyses        : résultat CNN + image embarquée (fusion predictions + images)
  capteurs        : mesures DHT11 / humidité sol
  recommandations : maladie + conseils/traitement (fusion maladies + recommandations)

Connexion paresseuse et tolérante : si MongoDB est indisponible, get_db()
retourne None et l'API continue de fonctionner en mode dégradé (pas d'historique).
"""

import os
from pymongo import MongoClient, DESCENDING

_client = None
_db = None


def get_db():
    """Retourne la base 'plantai', ou None si MongoDB est injoignable."""
    global _client, _db
    if _db is not None:
        return _db
    try:
        uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/plantai')
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        _client.server_info()  # lève une exception si MongoDB est absent
        _db = _client['plantai']
        get_utilisateurs_col()
        get_analyses_col()
        get_capteurs_col()
        print("✅  MongoDB connecté →", uri)
    except Exception as e:
        print(f"⚠️   MongoDB non disponible : {e} — l'API fonctionne en mode dégradé")
        _db = None
    return _db


def is_connected() -> bool:
    return get_db() is not None


def get_utilisateurs_col():
    db = get_db()
    if db is None:
        return None
    col = db['utilisateurs']
    col.create_index('email', unique=True)
    return col


def get_analyses_col():
    db = get_db()
    if db is None:
        return None
    col = db['analyses']
    col.create_index([('date', DESCENDING)])
    return col


def get_capteurs_col():
    db = get_db()
    if db is None:
        return None
    col = db['capteurs']
    col.create_index([('dateMesure', DESCENDING)])
    return col


def get_recommandations_col():
    db = get_db()
    if db is None:
        return None
    col = db['recommandations']
    col.create_index('codeLabel', unique=True)
    return col


def serialize(doc: dict) -> dict:
    """Convertit ObjectId → str et datetime → ISO string pour la réponse JSON."""
    from bson import ObjectId
    from datetime import datetime
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [serialize(i) if isinstance(i, dict) else i for i in v]
        elif isinstance(v, dict):
            out[k] = serialize(v)
        else:
            out[k] = v
    return out
