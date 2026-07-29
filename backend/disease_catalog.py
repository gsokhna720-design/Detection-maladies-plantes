"""
Catalogue des maladies — 5 cultures cibles du mémoire (Technopole de Dakar) :
Tomate, Aubergine, Salade, Oignon vert, Aloé Vera.

Chaque entrée est indexée par le codeLabel produit par le CNN Keras
(ia/model.py, class_names.json) et sert à peupler la collection MongoDB
"recommandations" (voir seed_recommandations.py) et à enrichir la réponse
de /api/predict.

Persil et Menthe n'ont volontairement aucune entrée ici — aucun dataset de
maladies suffisant n'existe pour ces 2 cultures (voir backend/cultures.py,
message MESSAGE_IA_INDISPONIBLE) : elles restent sélectionnables dans
l'interface mais sans diagnostic automatique.
"""

CLASS_INFO = {
    # ══════════════════════ TOMATE ══════════════════════
    "Tomato___Bacterial_spot": {
        "plante": "Tomate 🍅", "maladie": "Tache bactérienne", "niveau": "sick",
        "description": "Xanthomonas spp. Petites taches aqueuses, puis nécrotiques entourées d'un halo jaune.",
        "traitement": "Cuivre + mancozèbe dès les premiers symptômes. Retirer feuilles infectées.",
        "conseil": "Rotation 2–3 ans. Arrosage au sol uniquement. Désinfection des outils.",
    },
    "Tomato___Early_blight": {
        "plante": "Tomate 🍅", "maladie": "Alternariose", "niveau": "sick",
        "description": "Alternaria solani. Taches brunes concentriques en cible, anneau jaune autour.",
        "traitement": "Chlorothalonil ou azoxystrobine. Supprimer feuilles basses infectées.",
        "conseil": "Paillis pour éviter éclaboussures. Arrosage matinal.",
    },
    "Tomato___Late_blight": {
        "plante": "Tomate 🍅", "maladie": "Mildiou (Phytophthora infestans)", "niveau": "critical",
        "description": "Phytophthora infestans. Taches huileuses irrégulières, duvet blanc sous les feuilles. Extrêmement contagieux.",
        "traitement": "URGENCE : fongicide systémique (métalaxyl + cuivre). Arracher plants très atteints.",
        "conseil": "Abri en cas de pluie. Brûler les débris. Ne jamais composter. Rotation stricte.",
    },
    "Tomato___Leaf_Mold": {
        "plante": "Tomate 🍅", "maladie": "Moisissure des feuilles (Cladosporiose)", "niveau": "sick",
        "description": "Passalora fulva. Face supérieure jaune, face inférieure veloutée olive à brun.",
        "traitement": "Mancozèbe ou chlorothalonil. Améliorer drastiquement la ventilation.",
        "conseil": "Humidité relative < 85%. Espacer les plants. Serre bien ventilée.",
    },
    "Tomato___Septoria_leaf_spot": {
        "plante": "Tomate 🍅", "maladie": "Septoriose", "niveau": "sick",
        "description": "Septoria lycopersici. Petites taches circulaires blanches à centre gris, nombreux points noirs.",
        "traitement": "Cuivre ou chlorothalonil. Supprimer feuilles basses au moindre symptôme.",
        "conseil": "Éviter arrosage foliaire. Rotation des cultures. Tuteurage.",
    },
    "Tomato___Spider_mites Two-spotted_spider_mite": {
        "plante": "Tomate 🍅", "maladie": "Infestation d'acariens (Tetranychus urticae)", "niveau": "sick",
        "description": "Acarien Tetranychus urticae. Décoloration en mosaïque bronze, toiles fines sous les feuilles.",
        "traitement": "Acaricide (abamectine). Savon insecticide bio. Prédateurs biologiques (Phytoseiulus).",
        "conseil": "Hygrométrie élevée défavorable. Surveiller régulièrement la face inférieure.",
    },
    "Tomato___Target_Spot": {
        "plante": "Tomate 🍅", "maladie": "Tache en cible (Corynespora)", "niveau": "sick",
        "description": "Corynespora cassiicola. Taches concentriques brun-tan sur feuilles et fruits.",
        "traitement": "Azoxystrobine ou difénoconazole.",
        "conseil": "Bonne ventilation. Éliminer débris végétaux. Rotation des cultures.",
    },
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": {
        "plante": "Tomate 🍅", "maladie": "Virus TYLCV", "niveau": "critical",
        "description": "Geminiviridae transmis par Bemisia tabaci. Feuilles en cuillère, chlorose marginale. INCURABLE.",
        "traitement": "Aucun traitement curatif. Insecticide contre les aleurodes (vecteur). Filet insectproof.",
        "conseil": "Variétés résistantes TYLCV disponibles. Éliminer plants atteints sans tarder. Quarantaine.",
    },
    "Tomato___Tomato_mosaic_virus": {
        "plante": "Tomate 🍅", "maladie": "Virus mosaïque (ToMV)", "niveau": "critical",
        "description": "Tobamovirus. Mosaïque vert clair/foncé, déformation foliaire et des fruits. Très contagieux par contact.",
        "traitement": "Aucun traitement curatif. Arracher et brûler immédiatement les plants infectés.",
        "conseil": "Hygiène stricte : laver les mains, désinfecter outils. Plants certifiés indemnes.",
    },
    "Tomato___healthy": {
        "plante": "Tomate 🍅", "maladie": None, "niveau": "healthy",
        "description": "Plant de tomate en parfaite santé.",
        "traitement": "Aucun traitement requis.",
        "conseil": "Tuteurage et taille des gourmands. Fertilisation régulière calcium/magnésium.",
    },

    # ══════════════════════ AUBERGINE ══════════════════════
    "Eggplant___Healthy_Leaf": {
        "plante": "Aubergine 🍆", "maladie": None, "niveau": "healthy",
        "description": "Feuille d'aubergine en bonne santé, sans symptôme visible.",
        "traitement": "Aucun traitement requis.",
        "conseil": "Irrigation régulière. Surveillance préventive hebdomadaire.",
    },
    "Eggplant___Insect_Pest_Disease": {
        "plante": "Aubergine 🍆", "maladie": "Dommages d'insectes ravageurs", "niveau": "sick",
        "description": "Perforations, décoloration ou déformation causées par des ravageurs (pucerons, aleurodes, chenilles).",
        "traitement": "Insecticide ciblé ou savon insecticide bio. Identifier le ravageur avant traitement.",
        "conseil": "Favoriser les auxiliaires (coccinelles). Surveiller le dessous des feuilles.",
    },
    "Eggplant___Leaf_Spot_Disease": {
        "plante": "Aubergine 🍆", "maladie": "Tache foliaire fongique", "niveau": "sick",
        "description": "Taches brunes à noires, souvent circulaires (Cercospora / Alternaria), pouvant fusionner.",
        "traitement": "Fongicide cuivre ou mancozèbe. Retirer les feuilles atteintes.",
        "conseil": "Éviter l'arrosage foliaire. Espacer les plants pour l'aération.",
    },
    "Eggplant___Mosaic_Virus_Disease": {
        "plante": "Aubergine 🍆", "maladie": "Virus de la mosaïque", "niveau": "critical",
        "description": "Mosaïque vert clair/foncé, feuillage déformé et rabougri. Transmis par pucerons ou contact.",
        "traitement": "Aucun traitement curatif. Arracher et détruire les plants infectés.",
        "conseil": "Lutter contre les pucerons vecteurs. Désinfecter les outils entre plants.",
    },
    "Eggplant___White_Mold_Disease": {
        "plante": "Aubergine 🍆", "maladie": "Moisissure blanche (Sclerotinia)", "niveau": "critical",
        "description": "Sclerotinia sclerotiorum. Duvet blanc cotonneux sur tiges et feuilles, pourriture molle.",
        "traitement": "Fongicide spécifique (boscalid). Éliminer et détruire les parties atteintes.",
        "conseil": "Aération maximale. Éviter l'excès d'humidité stagnante au collet.",
    },
    "Eggplant___Wilt_Disease": {
        "plante": "Aubergine 🍆", "maladie": "Flétrissement (Verticillium/Fusarium)", "niveau": "critical",
        "description": "Jaunissement puis flétrissement progressif et irréversible, souvent d'un seul côté de la plante.",
        "traitement": "Aucun curatif efficace. Arracher les plants atteints pour limiter la propagation.",
        "conseil": "Rotation longue (4-5 ans). Variétés résistantes recommandées. Désinfecter le sol si récidive.",
    },

    # ══════════════════════ OIGNON VERT ══════════════════════
    "GreenOnion___Alternaria_D": {
        "plante": "Oignon vert 🌿", "maladie": "Alternariose", "niveau": "sick",
        "description": "Alternaria porri. Taches ovales brun-pourpre entourées d'un halo jaune, brûlure des feuilles.",
        "traitement": "Fongicide mancozèbe ou chlorothalonil dès les premiers symptômes.",
        "conseil": "Éviter l'irrigation par aspersion. Rotation des cultures.",
    },
    "GreenOnion___Botrytis_Leaf_Blight": {
        "plante": "Oignon vert 🌿", "maladie": "Brûlure de Botrytis", "niveau": "sick",
        "description": "Botrytis squamosa. Petites taches blanchâtres ovales, pouvant évoluer en brûlure généralisée par temps humide.",
        "traitement": "Fongicide de contact. Améliorer l'aération du feuillage.",
        "conseil": "Réduire la densité de plantation. Éviter l'humidité prolongée sur le feuillage.",
    },
    "GreenOnion___Bulb_blight-D": {
        "plante": "Oignon vert 🌿", "maladie": "Brûlure du bulbe", "niveau": "critical",
        "description": "Pourriture et nécrose au niveau du bulbe et de la base des feuilles.",
        "traitement": "Arracher et détruire les plants atteints. Fongicide préventif sur le reste de la parcelle.",
        "conseil": "Éviter les blessures mécaniques. Bon drainage du sol indispensable.",
    },
    "GreenOnion___Downy_mildew": {
        "plante": "Oignon vert 🌿", "maladie": "Mildiou", "niveau": "critical",
        "description": "Peronospora destructor. Duvet grisâtre-violacé sur les feuilles, jaunissement puis dessèchement.",
        "traitement": "Fongicide systémique à base de métalaxyl. Traiter dès l'apparition, très contagieux.",
        "conseil": "Éviter l'excès d'humidité. Rotation stricte, ne pas replanter sur la même parcelle.",
    },
    "GreenOnion___Fusarium-D": {
        "plante": "Oignon vert 🌿", "maladie": "Pourriture fusarienne", "niveau": "critical",
        "description": "Fusarium oxysporum. Pourriture basale, racines brunes, flétrissement des feuilles.",
        "traitement": "Aucun curatif efficace. Arracher les plants atteints.",
        "conseil": "Rotation longue (4 ans minimum). Sol bien drainé, éviter l'excès d'eau.",
    },
    "GreenOnion___Healthy_leaves": {
        "plante": "Oignon vert 🌿", "maladie": None, "niveau": "healthy",
        "description": "Feuillage d'oignon vert sain, vert uniforme sans lésion.",
        "traitement": "Aucun traitement requis.",
        "conseil": "Arrosage régulier et modéré. Désherbage pour limiter la concurrence.",
    },
    "GreenOnion___Iris_yellow_virus_augment": {
        "plante": "Oignon vert 🌿", "maladie": "Virus des taches jaunes de l'iris (IYSV)", "niveau": "critical",
        "description": "Virus transmis par le thrips. Lésions en losange jaune-brun nécrotiques sur les feuilles.",
        "traitement": "Aucun traitement curatif. Lutte insecticide contre les thrips vecteurs.",
        "conseil": "Éliminer les débris et mauvaises herbes hôtes. Surveiller les populations de thrips.",
    },
    "GreenOnion___Purple_blotch": {
        "plante": "Oignon vert 🌿", "maladie": "Tache pourpre", "niveau": "sick",
        "description": "Alternaria porri. Lésions concentriques pourpres à brunes, souvent à partir des pointes de feuilles.",
        "traitement": "Fongicide à base de cuivre ou d'azoxystrobine.",
        "conseil": "Éviter le stress hydrique. Bonne aération entre les rangs.",
    },
    "GreenOnion___Rust": {
        "plante": "Oignon vert 🌿", "maladie": "Rouille", "niveau": "sick",
        "description": "Puccinia allii. Pustules orangées poudreuses sur les feuilles.",
        "traitement": "Fongicide triazole si l'attaque est sévère.",
        "conseil": "Éviter l'excès d'azote. Aération du feuillage.",
    },
    "GreenOnion___Virosis-D": {
        "plante": "Oignon vert 🌿", "maladie": "Virose générale", "niveau": "critical",
        "description": "Symptômes viraux : mosaïque, striures jaunes, rabougrissement du feuillage.",
        "traitement": "Aucun traitement curatif. Éliminer les plants atteints.",
        "conseil": "Lutter contre les insectes vecteurs (pucerons, thrips). Utiliser des plants certifiés sains.",
    },
    "GreenOnion___Xanthomonas_Leaf_Blight": {
        "plante": "Oignon vert 🌿", "maladie": "Brûlure bactérienne (Xanthomonas)", "niveau": "sick",
        "description": "Xanthomonas spp. Stries aqueuses puis nécrotiques sur les feuilles.",
        "traitement": "Bactéricide à base de cuivre. Éviter l'arrosage par aspersion.",
        "conseil": "Désinfecter les outils. Rotation des cultures.",
    },
    "GreenOnion___stemphylium_Leaf_Blight": {
        "plante": "Oignon vert 🌿", "maladie": "Brûlure à Stemphylium", "niveau": "sick",
        "description": "Stemphylium vesicarium. Lésions allongées brun-jaunâtre, souvent associées à d'autres maladies foliaires.",
        "traitement": "Fongicide à large spectre (chlorothalonil).",
        "conseil": "Éviter l'humidité persistante sur le feuillage. Bonne rotation.",
    },

    # ══════════════════════ SALADE ══════════════════════
    # Catégories volontairement génériques (Bactérien/Fongique) — le dataset
    # disponible pour la Salade ne distingue pas les maladies précises,
    # contrairement aux autres cultures (limite documentée dans le mémoire).
    "Lettuce___Bacterial": {
        "plante": "Salade 🥬", "maladie": "Maladie bactérienne", "niveau": "sick",
        "description": "Symptômes compatibles avec une infection bactérienne (taches aqueuses, pourriture molle). Agent précis non déterminé par ce modèle.",
        "traitement": "Bactéricide à base de cuivre. Retirer les feuilles atteintes.",
        "conseil": "Éviter l'arrosage foliaire. Rotation des cultures. Consulter un agronome pour identification précise si récidive.",
    },
    "Lettuce___Fungal": {
        "plante": "Salade 🥬", "maladie": "Maladie fongique", "niveau": "sick",
        "description": "Symptômes compatibles avec une infection fongique (mildiou, oïdium, Sclerotinia...). Agent précis non déterminé par ce modèle.",
        "traitement": "Fongicide à large spectre. Améliorer la ventilation entre les plants.",
        "conseil": "Réduire l'humidité foliaire. Espacer les plants. Consulter un agronome pour identification précise si récidive.",
    },
    "Lettuce___Healthy": {
        "plante": "Salade 🥬", "maladie": None, "niveau": "healthy",
        "description": "Plant de salade en bonne santé, feuillage vert sans lésion.",
        "traitement": "Aucun traitement requis.",
        "conseil": "Arrosage régulier au sol. Surveiller les limaces et pucerons.",
    },

    # ══════════════════════ ALOÉ VERA ══════════════════════
    "AloeVera___Aloe_Rust": {
        "plante": "Aloé Vera 🌵", "maladie": "Rouille", "niveau": "sick",
        "description": "Pustules orangées à brunes sur les feuilles charnues, pouvant affaiblir la plante.",
        "traitement": "Fongicide triazole si l'attaque est étendue.",
        "conseil": "Éviter l'excès d'humidité sur le feuillage. Bonne circulation d'air.",
    },
    "AloeVera___Anthracnose": {
        "plante": "Aloé Vera 🌵", "maladie": "Anthracnose", "niveau": "critical",
        "description": "Taches noires déprimées, souvent avec un centre plus clair, pouvant s'étendre rapidement.",
        "traitement": "Fongicide à base de cuivre. Retirer et détruire les feuilles atteintes.",
        "conseil": "Éviter les blessures mécaniques. Réduire l'arrosage par aspersion.",
    },
    "AloeVera___Healthy": {
        "plante": "Aloé Vera 🌵", "maladie": None, "niveau": "healthy",
        "description": "Feuille d'aloé vera saine, charnue et sans lésion.",
        "traitement": "Aucun traitement requis.",
        "conseil": "Arrosage modéré et espacé. Sol bien drainé indispensable.",
    },
    "AloeVera___Leaf_Spot": {
        "plante": "Aloé Vera 🌵", "maladie": "Tache foliaire", "niveau": "sick",
        "description": "Taches brunes à noires, souvent circulaires, dispersées sur la feuille.",
        "traitement": "Fongicide de contact. Éliminer les feuilles fortement atteintes.",
        "conseil": "Éviter l'excès d'arrosage. Bonne aération autour des plants.",
    },
    "AloeVera___Sunburn": {
        "plante": "Aloé Vera 🌵", "maladie": "Coup de soleil (stress abiotique)", "niveau": "sick",
        "description": "Décoloration brun-rougeâtre due à une exposition solaire excessive — non infectieux, pas une maladie au sens strict.",
        "traitement": "Aucun traitement phytosanitaire nécessaire.",
        "conseil": "Ombrage partiel lors des fortes chaleurs. Acclimatation progressive au soleil direct.",
    },
}
