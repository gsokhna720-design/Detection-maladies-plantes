"""
Référentiel des 7 cultures cibles du mémoire (Technopole de Dakar).

5 cultures disposent d'un diagnostic IA automatique (modèle CNN entraîné sur
un dataset combiné — voir ia/train_model.py). 2 cultures (Persil, Menthe)
n'ont pas encore de base de données de maladies suffisante : elles restent
sélectionnables dans l'interface mais renvoient un message explicite au lieu
d'un diagnostic, avec possibilité de signalement manuel (voir /api/observations).

`prefixe` correspond au préfixe des classes du modèle CNN (ia/model/class_names.json),
ex. "Tomato___Late_blight" → prefixe "Tomato".
"""

MESSAGE_IA_INDISPONIBLE = (
    "Diagnostic automatique non disponible pour cette culture : aucune base de "
    "données de maladies suffisante n'existe actuellement. Collecte de données "
    "prévue en perspective de ce travail."
)

CULTURES = [
    {"id": "tomate",      "nom": "Tomate",      "emoji": "🍅", "prefixe": "Tomato",     "iaDisponible": True},
    {"id": "aubergine",   "nom": "Aubergine",    "emoji": "🍆", "prefixe": "Eggplant",   "iaDisponible": True},
    {"id": "salade",      "nom": "Salade",       "emoji": "🥬", "prefixe": "Lettuce",    "iaDisponible": True},
    {"id": "oignon_vert", "nom": "Oignon vert",  "emoji": "🌿", "prefixe": "GreenOnion", "iaDisponible": True},
    {"id": "aloe_vera",   "nom": "Aloé Vera",    "emoji": "🌵", "prefixe": "AloeVera",   "iaDisponible": True},
    {"id": "persil",      "nom": "Persil",       "emoji": "🌱", "prefixe": None, "iaDisponible": False, "message": MESSAGE_IA_INDISPONIBLE},
    {"id": "menthe",      "nom": "Menthe",       "emoji": "🍃", "prefixe": None, "iaDisponible": False, "message": MESSAGE_IA_INDISPONIBLE},
]

CULTURES_PAR_ID = {c["id"]: c for c in CULTURES}


def get_culture(culture_id: str):
    return CULTURES_PAR_ID.get(culture_id)


def ia_disponible(culture_id: str) -> bool:
    c = get_culture(culture_id)
    return bool(c and c["iaDisponible"])
