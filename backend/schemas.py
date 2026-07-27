"""Modèles Pydantic — corps des requêtes/réponses de l'API FastAPI."""

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    motDePasse: str


class UserCreate(BaseModel):
    nom: str
    prenom: Optional[str] = None
    email: str
    motDePasse: str
    role: str = 'maraicher'
    exploitation: Optional[str] = None


class UserUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    exploitation: Optional[str] = None
    motDePasse: Optional[str] = None


class SensorData(BaseModel):
    temperatureAir: float
    humiditeAir: float
    humiditeSol: float
    dateMesure: Optional[str] = None
    analyseId: Optional[str] = None


class ESP32CaptureRequest(BaseModel):
    ip: Optional[str] = None
