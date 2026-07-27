"""
Crée le premier compte Administrateur — à lancer une seule fois.
Nécessaire car /users (POST) est réservé aux administrateurs : il faut
un premier compte pour amorcer le système.

Usage :
  cd backend
  python seed_admin.py <email> <mot_de_passe> [nom] [prenom]
"""

import sys
import os

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from pymongo import MongoClient

from auth import hash_password

load_dotenv()


def main():
    if len(sys.argv) < 3:
        print("Usage : python seed_admin.py <email> <mot_de_passe> [nom] [prenom]")
        raise SystemExit(1)

    email        = sys.argv[1].strip().lower()
    mot_de_passe = sys.argv[2]
    nom          = sys.argv[3] if len(sys.argv) > 3 else 'Admin'
    prenom       = sys.argv[4] if len(sys.argv) > 4 else 'PlantAI'

    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/plantai')
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.server_info()
    users = client['plantai']['utilisateurs']
    users.create_index('email', unique=True)

    if users.find_one({'email': email}):
        print(f"Un utilisateur existe déjà avec l'email {email}")
        raise SystemExit(1)

    users.insert_one({
        'nom': nom, 'prenom': prenom, 'email': email,
        'motDePasse': hash_password(mot_de_passe),
        'role': 'administrateur',
    })
    print(f"✅ Administrateur créé : {email}")


if __name__ == '__main__':
    main()
