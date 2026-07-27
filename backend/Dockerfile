# Image de base Python 3.11 slim
FROM python:3.11-slim

# Éviter les fichiers .pyc et buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires (TensorFlow / Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers requirements
COPY backend/requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le backend et le module IA (CNN Keras — utilisé par backend/app.py)
COPY backend/ .
COPY ia/ ../ia/

# Créer les dossiers utilisés par l'application
RUN mkdir -p uploads

# Exposer le port
EXPOSE 5000

# Variables d'environnement par défaut
ENV PORT=5000
ENV CNN_MODEL_PATH=/ia/model/plant_disease_model.keras

# Démarrer l'application avec Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
