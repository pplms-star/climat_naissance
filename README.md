# Le climat a-t-il changé depuis ta naissance ? (Alsace)

Site statique en format "scrollytelling" : une phrase à trous (année de
naissance + commune) déclenche un récit qui se construit au scroll, en 7
étapes — contexte national, référence personnelle, été, année, vue
d'ensemble, extrêmes, projections futures.

**Couverture actuelle** : Alsace entière (Bas-Rhin + Haut-Rhin), via 132
mailles de la réanalyse SAFRAN (grille 8km, Météo-France) et 882 communes
distinctes, chacune rattachée automatiquement à sa maille la plus proche.

## Structure

```
index.html                              → le site (HTML + CSS + JS, un seul fichier)
data/communes.json                      → 882 communes → maille SAFRAN la plus proche
data/safran-<cell>.json                 → stats annuelles + projections, une par maille (132 fichiers)
data/france-nationale.json              → température moyenne annuelle France 1958-2025 (étape 1)
data-safran/mailles_alsace.csv          → référence des 132 mailles (id, coordonnées, altitude, département)

scripts/extraire_alsace_safran.py       → étape 1/2 : filtre les fichiers SIM (SAFRAN) nationaux
                                           aux mailles alsaciennes, relançable par lots
scripts/generer_donnees_safran.py       → étape 2/2 : calcule les stats annuelles par maille
                                           à partir du fichier filtré, génère les JSON finaux
scripts/integrer_projections_drias.py   → ajoute les projections DRIAS (GWL20/GWL30) dans les
                                           JSON de maille déjà générés

scripts/diagnostic_filtrage_safran.py   → inspecte la structure d'un fichier SIM avant traitement

⚠️ obsolètes, gardés pour référence (ancienne approche par stations Météo-France
   classiques, abandonnée au profit de SAFRAN qui couvre toute l'Alsace sans
   dépendre de la présence d'une station physique) :
scripts/generer_toutes_stations.py, fusionner_sqr.py, generer_donnees_climat.py,
scripts/simplifier_donnees_entzheim*.py, diagnostic_sqr*.py, diagnostic_stations_temperature.py
```

## Pourquoi SAFRAN plutôt que des stations Météo-France classiques

Les stations Météo-France ne couvrent qu'un point précis, avec des trous
fréquents (poste sans thermomètre, historique fragmenté en plusieurs
identités après un changement de capteur). **SAFRAN** est une réanalyse à
maille régulière de 8km, calculée par Météo-France sur toute la France
depuis 1958 : chaque commune a donc une maille représentative à moins de
8km, sans dépendre de la présence d'une vraie station à proximité.

## Pipeline complet pour générer les données d'une maille

1. **Récupérer la liste des mailles** : un fichier GeoPackage (`safran.gpkg`)
   contient les 8602 mailles françaises avec leurs coordonnées et leur
   département — filtré ici aux 132 mailles Bas-Rhin/Haut-Rhin
   (`data-safran/mailles_alsace.csv`, colonnes `cell`, `longitude`,
   `latitude`, `altitude_m`, plus `lambx`/`lamby` en coordonnées Lambert-II
   étendu pour faire le lien avec les fichiers SIM).

2. **Télécharger les données SIM quotidiennes** sur meteo.data.gouv.fr
   (jeu "Données changement climatique — SIM quotidienne") : fichiers CSV
   par tranche d'années, **toute la France à chaque fois** (colonnes clés :
   `LAMBX`, `LAMBY`, `DATE`, `T` [moyenne], `TINF_H` [min], `TSUP_H` [max]).

3. **Extraire l'Alsace au fur et à mesure** avec
   `extraire_alsace_safran.py` : filtre chaque fichier SIM aux 132 mailles
   alsaciennes et **ajoute** le résultat à `jours_alsace_bruts.csv` (jamais
   d'écrasement — permet de traiter les tranches d'années par lots, en
   supprimant les gros fichiers sources au fur et à mesure pour économiser
   de la place disque).

4. **Générer les JSON finaux** avec `generer_donnees_safran.py`, une fois
   `jours_alsace_bruts.csv` complet sur toute la période voulue (idéalement
   depuis avant 1976 pour couvrir la période de référence).

## Projections futures (DRIAS)

`integrer_projections_drias.py` complète les JSON de maille déjà générés
avec des projections climatiques, à partir d'un CSV DRIAS déjà agrégé
(une ligne par point de grille DRIAS et par année simulée, colonnes
`Point`, `Latitude`, `Longitude`, `Niveau`, `Annee`, `TMm_yr`,
`TMm_seas_JJA`, `TMm_seas_DJF`, `TXm_seas_JJA`, `TX35D_yr`, `TX30D_yr`,
`TR_yr`, `IFM40_yr`).

Le `Niveau` correspond à un "Global Warming Level" (GWL) — un seuil de
réchauffement mondial atteint à une échéance donnée, plutôt qu'une date
fixe. Actuellement intégrés :
- **GWL20** : réchauffement Monde +2,0°C / France +2,7°C (fenêtre représentative 2052-2071)
- **GWL30** : réchauffement Monde +3,0°C / France +4°C (fenêtre représentative 2079-2098)

Le script moyenne toutes les années de la fenêtre pour chaque point DRIAS,
rattache chaque point à sa maille SAFRAN la plus proche, et remplit le champ
`"projections"` (dictionnaire par niveau) du JSON de maille correspondant.
129 mailles sur 132 ont au moins un point DRIAS proche.

## Format d'un fichier data/safran-<cell>.json

```json
{
  "station": "Maille SAFRAN 1205",
  "periode_reference": "1976-2005",
  "source": "Météo-France SAFRAN (réanalyse, maille 8km)",
  "comparaison": { "type": "fixe", "debut": 1994, "fin": 2023 },
  "projections": {
    "GWL20": {
      "scenario": "Réchauffement Monde +2,0°C / France +2,7°C (2052-2071)",
      "tm_annuelle": 12.1, "tm_ete": 20.4, "tm_hiver": 4.2, "tx_ete": 26.3,
      "jours_plus_30": 9, "jours_plus_35": 1, "nuits_tropicales": 4, "jours_risque_feu": 2
    },
    "GWL30": { "...": "même structure" }
  },
  "annees": [
    {
      "annee": 1958,
      "tx_moy": 14.3, "tn_moy": 5.9, "tm_moy": 10.1,
      "ete_tm_moy": 18.6, "ete_tx_moy": 24.1, "hiver_tm_moy": 3.0,
      "jours_chauds_25": 16, "jours_chauds_30": 2,
      "nuits_tropicales": 1, "jours_gel": 44, "jours_vague_chaleur": 0
    }
  ]
}
```

⚠️ Le champ `"comparaison"` (fixe/variable) est présent dans les données
mais **n'est plus utilisé par le site** — la méthode a été simplifiée en
cours de route : le site compare maintenant toujours la période de
référence personnelle (30 ans autour de la naissance) aux **10 dernières
années disponibles**, sans distinction fixe/variable.

## Format de data/communes.json

```json
{
  "communes": [
    { "commune": "Schiltigheim", "station_id": "safran-1851", "distance_km": 3.0 }
  ],
  "stations": [
    { "id": "safran-1851", "nom": "Maille SAFRAN 1851", "fichier": "data/safran-1851.json" }
  ]
}
```

Généré automatiquement à partir d'un fichier national de communes (avec
coordonnées lat/lon) et de `mailles_alsace.csv`, en calculant pour chaque
commune la maille SAFRAN la plus proche (distance haversine). Dédupliqué
(certains fichiers sources ont une ligne par code postal, donc plusieurs
lignes pour une même commune).

## Ajouter une commune ou une maille

- **Commune déjà couverte par une maille existante** : ajoute une ligne
  dans `communes.json` (liste `communes`) avec le bon `station_id` (le
  plus simple : recalculer la distance à la maille la plus proche parmi
  `mailles_alsace.csv`).
- **Nouvelle maille** (extension géographique au-delà de l'Alsace) : reprend
  tout le pipeline SAFRAN ci-dessus pour la nouvelle zone.

Aucune modification d'`index.html` n'est nécessaire dans les deux cas.

## Fonctionnalités du site

- Recherche de commune par autocomplétion (882 communes, recherche
  insensible à la casse et aux accents, navigable au clavier).
- Slider d'année de naissance (1955-2010), avec cas particulier pour les
  personnes nées après 2008 (référence fixe 1993-2023, une fenêtre ±15 ans
  n'aurait pas de sens à cet âge).
- Graphiques été/année : nuage de points + moyenne mobile 10 ans, avec
  révélation progressive au scroll (points → courbe → bandes de référence),
  point par point façon dessin animé.
- Étape 1 (contexte national) : température moyenne annuelle française
  1958-2025, transformation en climate stripes (barres bleu/rouge), deux
  chiffres clés (écart à la référence, écart entre première et dernière
  décennie).
- Étape 7 (projections) : sélecteur GWL20/GWL30, cartes de comparaison
  "aujourd'hui → projection" pour les indicateurs ayant un équivalent
  historique, et cartes simples pour les indicateurs propres aux
  projections (jours à risque feu, jours >35°C).

## Fonctionnalité retirée

Une section de comparaison entre deux communes (radar chart) a été
implémentée puis retirée (peu d'intérêt à comparer des communes proches
en Alsace, et un bug d'affichage lié au chargement de Chart.js n'a pas
été entièrement résolu avant la décision de la retirer). Le code a été
proprement nettoyé — aucune trace résiduelle dans `index.html`. À
reconsidérer sous une autre forme si utile un jour (comparer à une grande
ville éloignée, ou à la moyenne nationale de l'étape 1).

## Déploiement GitHub + Vercel

1. Pousse tout le dossier (structure complète, avec les sous-dossiers
   `data/` et `scripts/`) sur un repo GitHub — utilise GitHub Desktop plutôt
   que le glisser-déposer web si tu as beaucoup de fichiers, le
   glisser-déposer web ne gère pas toujours bien les sous-dossiers.
2. Sur vercel.com : "Add New… → Project" → sélectionne le repo → "Deploy"
   (site statique, aucune configuration nécessaire).
3. Chaque `git push` déclenche un redéploiement automatique.

## Pistes d'évolution possibles
- Étendre au-delà de l'Alsace avec le même pipeline SAFRAN.
- Repenser une comparaison entre communes (voir "Fonctionnalité retirée").
- Ajouter un indicateur de risque de feu de forêt en historique (pas
  seulement en projection) si une source de données quotidienne existe.
