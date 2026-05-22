"""
Bilingual (FR/EN) free-text feedback templates by theme and sentiment polarity.
We deliberately do NOT tag sentiment here — that scoring belongs to the NLP stage
in the dbt staging layer (Part 2), so we exercise the full unstructured pipeline.
"""
from __future__ import annotations

# Each theme has 3 polarities: negative, positive, neutral. Multiple templates per
# polarity to provide lexical diversity. Placeholders {route}, {city} are filled at runtime.

TEMPLATES: dict[str, dict[str, list[str]]] = {
    "delay": {
        "fr_negative": [
            "Vol retardé de plusieurs heures sans information claire de l'équipage. Inacceptable pour un vol {route}.",
            "Encore un retard énorme à Abidjan, j'ai raté ma correspondance à {city}. Aucune compensation proposée.",
            "Le retard a duré près de 3 heures, le personnel au sol était introuvable. Très déçu.",
            "Décollage repoussé sans explication, je suis arrivé à {city} en pleine nuit.",
        ],
        "en_negative": [
            "Flight on route {route} was severely delayed, I missed my connection in {city}. No proper assistance.",
            "Painful delay at boarding, more than 2 hours and zero communication from the crew.",
            "Air Côte d'Ivoire keeps being late on this route. Last time was a 4h wait at the gate.",
        ],
        "fr_positive": [
            "Vol parti à l'heure, retour ABJ-{city} très efficace. Bravo.",
        ],
        "en_positive": [
            "Surprisingly on time on the {route} segment. Smooth turnaround.",
        ],
    },
    "baggage": {
        "fr_negative": [
            "Bagage perdu entre {city} et Abidjan, toujours pas récupéré 5 jours après. Service client injoignable.",
            "Ma valise est arrivée cassée à {city}, aucune indemnisation proposée. C'est la dernière fois.",
            "Délai de livraison des bagages à l'arrivée beaucoup trop long, près d'une heure à attendre.",
        ],
        "en_negative": [
            "Bag lost on connection from {city}, support agents very slow to respond.",
            "Damaged suitcase upon arrival, only got a generic apology email.",
            "Baggage handling at ABJ needs serious improvement, delays every time.",
        ],
        "fr_positive": [
            "Bagages livrés rapidement à {city}, parfait.",
        ],
    },
    "crew": {
        "fr_negative": [
            "Personnel de cabine peu aimable sur le vol vers {city}, ambiance tendue durant tout le trajet.",
            "L'hôtesse était désagréable lorsque j'ai demandé un verre d'eau.",
        ],
        "en_negative": [
            "Cabin crew rude to passengers asking for headphones. Disappointing professional standard.",
            "Crew rushing through service, no smile, very different from the previous experience.",
        ],
        "fr_positive": [
            "Équipage très professionnel et souriant, vol vers {city} agréable malgré la durée.",
            "Les hôtesses étaient adorables avec mon enfant. Merci à toute l'équipe.",
            "Service à bord excellent, on sent une vraie attention au client en classe Business.",
        ],
        "en_positive": [
            "Cabin crew was outstanding, very attentive especially in Business class.",
            "Friendly and professional crew on flight to {city}, made the trip much better.",
        ],
    },
    "food": {
        "fr_negative": [
            "Repas servi froid et portion ridicule pour un vol long-courrier vers {city}.",
            "Le plateau était immangeable, je n'ai presque rien touché.",
        ],
        "en_negative": [
            "Meal quality was poor on the long-haul. Expected better given the ticket price.",
        ],
        "fr_positive": [
            "Repas étonnamment bon en classe affaires, surtout le dessert.",
        ],
        "en_positive": [
            "The catering in Business was a pleasant surprise — nicely presented and tasty.",
        ],
    },
    "seat": {
        "fr_negative": [
            "Siège cassé en classe économique, impossible d'incliner. Vol pénible.",
            "Espace pour les jambes vraiment trop réduit sur ce vol vers {city}, je ne recommande pas.",
        ],
        "en_negative": [
            "Seat would not recline, requested a change but cabin was full. Long flight in pain.",
            "Premium Economy felt like regular Economy for the price difference.",
        ],
        "fr_positive": [
            "Sièges Business très confortables, j'ai pu dormir sur le vol de nuit.",
        ],
    },
    "booking": {
        "fr_negative": [
            "Site web impossible à utiliser, impossible de modifier ma réservation pour {city}.",
            "Application mobile bugguée, paiement refusé trois fois avant d'aboutir.",
            "Remboursement promis il y a deux mois, toujours pas reçu.",
        ],
        "en_negative": [
            "Mobile app crashed during check-in, had to queue at the airport for an hour.",
            "Refund process is a nightmare, multiple emails ignored.",
        ],
        "fr_positive": [
            "Réservation simple et rapide sur l'app mobile.",
        ],
    },
    "lounge": {
        "fr_negative": [
            "Salon d'Abidjan bondé, peu de places assises et offre limitée.",
        ],
        "en_negative": [
            "Lounge at ABJ was overcrowded and short on food options.",
        ],
        "fr_positive": [
            "Salon agréable à Abidjan, calme et bonne sélection de mets.",
        ],
        "en_positive": [
            "Lounge access was a nice touch, food and drinks well stocked.",
        ],
    },
    "upgrade": {
        "fr_positive": [
            "Surclassement gratuit en classe affaires, expérience fantastique vers {city}.",
            "L'upgrade proposé à l'embarquement était à un prix raisonnable, je n'ai pas hésité.",
        ],
        "en_positive": [
            "Got a complimentary upgrade thanks to my Gold status, top experience.",
            "Upgrade pricing at the gate was fair, totally worth it for the long-haul leg.",
        ],
        "fr_negative": [
            "Surclassement promis puis refusé à l'embarquement malgré une réservation flexible.",
        ],
    },
    "general": {
        "fr_positive": [
            "Très bonne expérience globale avec Air Côte d'Ivoire, je recommande pour {city}.",
            "Vol parfait sur la liaison {route}, je continuerai à voler avec eux.",
        ],
        "en_positive": [
            "Solid experience overall, will fly Air Côte d'Ivoire again on the {route} segment.",
            "Decent service and on-time performance, no complaints this time.",
        ],
        "fr_neutral": [
            "Expérience moyenne, ni vraiment satisfait, ni mécontent.",
            "Vol sans histoire vers {city}.",
        ],
        "en_neutral": [
            "Nothing remarkable, average experience to {city}.",
        ],
        "fr_negative": [
            "Service en chute libre, je vais regarder les concurrents la prochaine fois.",
        ],
        "en_negative": [
            "Quality has dropped on this route, may consider competitors next time.",
        ],
    },
}


# Approximate mapping theme -> trigger condition (used to bias selection of bookings).
THEME_TRIGGERS = {
    "delay":   {"disruption_types": ["Weather", "ATC", "Crew"], "boost": 4.0},
    "baggage": {"disruption_types": ["Other"], "boost": 2.0},
    "crew":    {"disruption_types": ["Crew"], "boost": 2.5},
    "food":    {"fare_classes": ["Premium Economy", "Business"], "boost": 1.6},
    "seat":    {"fare_classes": ["Economy", "Premium Economy"], "boost": 1.2},
    "booking": {"channels": ["Web", "Mobile App"], "boost": 1.3},
    "lounge":  {"fare_classes": ["Business"], "tiers": ["Gold", "Silver"], "boost": 2.0},
    "upgrade": {"fare_classes": ["Premium Economy", "Business"], "boost": 1.8},
    "general": {"boost": 1.0},
}


# Theme polarity probability distribution (depends on disruption presence)
# Rule: if booking has disruption -> 75% negative / 10% positive / 15% neutral
#       otherwise                 -> 35% negative / 50% positive / 15% neutral
POLARITY_IF_DISRUPTED = {"negative": 0.75, "positive": 0.10, "neutral": 0.15}
POLARITY_IF_CLEAN     = {"negative": 0.35, "positive": 0.50, "neutral": 0.15}
