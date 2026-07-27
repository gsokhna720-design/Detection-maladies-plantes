"""
Authentification — hash des mots de passe (bcrypt) + JWT + dépendances de rôle FastAPI.
Modèle : Utilisateur (idUtilisateur, nom, prenom, email, motDePasse, role)
         role ∈ {"administrateur", "maraicher"}
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

JWT_SECRET    = os.getenv('JWT_SECRET', 'dev-secret-a-changer-en-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRES_H = 24

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, AttributeError):
        return False


def generate_token(user: dict) -> str:
    """user doit contenir : idUtilisateur, email, role."""
    payload = {
        'idUtilisateur': user['idUtilisateur'],
        'email':         user['email'],
        'role':          user['role'],
        'exp':           datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_H),
        'iat':           datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    """Retourne le payload décodé, ou None si le token est invalide/expiré."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """Dépendance FastAPI : exige un token JWT valide. Lève 401 sinon."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentification requise')
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token invalide ou expiré')
    return payload


def require_role(*roles):
    """Fabrique une dépendance FastAPI exigeant un token valide ET un rôle parmi ceux fournis."""
    def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get('role') not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Accès refusé — rôle insuffisant')
        return current_user
    return dependency
