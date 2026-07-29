"""
Prédiction — charge le modèle CNN Keras entraîné (voir train_model.py)
et retourne la maladie prédite pour une image donnée.
"""

import os
import json

import numpy as np
from PIL import Image

MODEL_DIR        = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model')
MODEL_PATH       = os.getenv('CNN_MODEL_PATH', os.path.join(MODEL_DIR, 'plant_disease_model.keras'))
CLASS_NAMES_PATH = os.path.join(MODEL_DIR, 'class_names.json')
IMG_SIZE         = 224

_model = None
_class_names = None


def _load_model():
    global _model
    if _model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Modèle introuvable : {MODEL_PATH} — entraînez-le d'abord avec train_model.py"
            )
        import tensorflow as tf
        _model = tf.keras.models.load_model(MODEL_PATH)
    return _model


def _load_class_names():
    global _class_names
    if _class_names is None:
        if not os.path.exists(CLASS_NAMES_PATH):
            raise FileNotFoundError(f"Fichier des classes introuvable : {CLASS_NAMES_PATH}")
        with open(CLASS_NAMES_PATH, encoding='utf-8') as f:
            _class_names = json.load(f)['classes']
    return _class_names


def predict_image(image_path, allowed_prefixes=None):
    """Charge le modèle entraîné et prédit la maladie sur l'image donnée.

    allowed_prefixes : si fourni (ex. ["Tomato"]), la prédiction est restreinte
    aux classes de ce préfixe (ex. "Tomato___Late_blight") — utilisé pour ne
    renvoyer que des diagnostics cohérents avec la culture sélectionnée par
    l'utilisateur, même si le modèle couvre plusieurs cultures."""
    model = _load_model()
    class_names = _load_class_names()

    img = Image.open(image_path).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
    batch = np.expand_dims(np.array(img, dtype=np.float32), axis=0)

    probs = model.predict(batch, verbose=0)[0]

    if allowed_prefixes:
        indices = [i for i, c in enumerate(class_names) if c.split('___')[0] in allowed_prefixes]
        if not indices:
            raise ValueError(f"Aucune classe entraînée pour : {allowed_prefixes}")
    else:
        indices = range(len(class_names))

    idx = max(indices, key=lambda i: probs[i])

    return {
        'maladie':   class_names[idx],
        'confiance': round(float(probs[idx]), 4),
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage : python model.py <chemin_image>")
        raise SystemExit(1)
    print(predict_image(sys.argv[1]))
