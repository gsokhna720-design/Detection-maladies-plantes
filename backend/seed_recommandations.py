"""
Seed — peuple la collection MongoDB "recommandations" à partir du catalogue
PlantVillage (disease_catalog.CLASS_INFO). La maladie est un champ de chaque
document "recommandations" (pas de collection "maladies" séparée).

Modèle :
  recommandations : { codeLabel, plante, maladie, niveau, description,
                       traitement, conseil, produitsConseilles: [...] }

Idempotent : peut être relancé sans dupliquer (upsert sur codeLabel).
Les entrées "healthy" (pas de maladie) sont ignorées — une Analyse d'une
plante saine n'a simplement pas de recommandationId.

Usage :
  cd backend
  python seed_recommandations.py
"""

import os
import re
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from pymongo import MongoClient

from disease_catalog import CLASS_INFO

load_dotenv()


def _extract_produits(traitement: str) -> list:
    """Découpe le texte de traitement existant en une liste de produits candidats
    (aucune donnée inventée — simple segmentation du texte déjà présent)."""
    if not traitement:
        return []
    parts = re.split(r'\s+ou\s+|\s*\+\s*|,\s*|;\s*', traitement)
    return [p.strip().rstrip('.') for p in parts if len(p.strip()) > 2][:5]


def main():
    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/plantai')
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client['plantai']
    col = db['recommandations']
    col.create_index('codeLabel', unique=True)

    created = updated = skipped = 0

    for code_label, info in CLASS_INFO.items():
        if not info.get('maladie'):
            skipped += 1  # entrée "saine", pas une maladie
            continue

        traitement = info.get('traitement') or ''
        produits   = _extract_produits(traitement)

        existing = col.find_one({'codeLabel': code_label})
        col.update_one(
            {'codeLabel': code_label},
            {'$set': {
                'plante':             info.get('plante'),
                'maladie':            info['maladie'],
                'niveau':             info.get('niveau'),
                'description':        info.get('description'),
                'traitement':         traitement,
                'conseil':            info.get('conseil'),
                'produitsConseilles': produits,
            }},
            upsert=True,
        )
        if existing:
            updated += 1
        else:
            created += 1

    print(f"Recommandations créées : {created} | mises à jour : {updated} | ignorées (saines) : {skipped}")
    print(f"Total en base — recommandations : {col.count_documents({})}")


if __name__ == '__main__':
    main()
