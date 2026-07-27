# TODO - Corrections sécurité backend

- [x] Créer `.env` avec MODEL_PATH et PORT
- [x] Créer `.gitignore`
- [x] Sécuriser `app.py`
  - [x] Limiter taille uploads (16 Mo)
  - [x] Valider extensions fichiers (png, jpg, jpeg, gif, webp)
  - [x] Utiliser secure_filename
  - [x] Ajouter try/except
  - [x] Nettoyer fichiers après traitement
- [x] Sécuriser `ia/model.py` (CNN Keras)
  - [x] Vérifier existence modèle au démarrage
  - [x] Gérer erreurs inférence
  - [x] Vérifier présence détections avant accès
- [x] Mettre à jour `docker-compose.yml`


