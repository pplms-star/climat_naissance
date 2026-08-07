[README.md](https://github.com/user-attachments/files/29789842/README.md)
# Comment le climat a t-il évolué depuis ta naissance ? Edition Alsace
Site statique en format "scrollytelling" : une phrase à trous (année de
naissance + commune) déclenche un récit qui se construit au scroll, en 7 étapes : contexte national, référence personnelle selon l'année de naissance et la commune sélectionnée, évolution des températures en été, par année, indicateurs des jours extrêmes, projections futures.  


Couverture actuelle : Alsace entière(Bas-Rhin + Haut-Rhin), via 132 mailles de la réanalyse SAFRAN et 882 communes distinctes, chacune rattachée automatiquement à sa maille la plus proche. 
Données Météo-France SAFRAN, grille 8km

## Structure

```
index.html                                    → le site (HTML + CSS + JS, un seul fichier)
data/communes.json                            → 882 communes --> maille SAFRAN la plus proche
data/safran-<cell>.json                       → stats annuelles + projections, une par maille (132 fichiers)
data/france-nationale.json                    → température moyenne annuelle en France 1958-2025
data-safran/maille_alsace.csv                 → référence des 132 mailles (id, coordonnées, altitude, département)
scripts/extraire_alsace_safran.py             → étape 1/2 : filtre les fichiers SIM (SAFRAN) nationaux aux mailles alsaciennes, relançable par lots
scripts/generer_donnees_safran.py             → étape 2/2 : calcule les stats annuelles par maille à partir du fichier filtré, génère les JSON finaux
scripts/integrer_projections_drias.py         → ajoute les projections drias (GWL20/30) dans les JSON de mailles déjà générés
scripts/diagnostic_filtrage_safran.py         → inspecte la structure d'un fichier SIM avant traitement


Partie obsolètes : conservée pour référence, ancienne approche par stations Météo-France classiques, abandonnée au profit de SAFRAN qui couvre toute l'Alsace sans dépendre de la présence d'une station physique, avec des données plus complètes. 
scripts/generer_toutes_stations.py            → génère les stats depuis un fichier Météo-France départemental brut (Q_67_.../Q_68_...)
scripts/fusionner_sqr.py                       → génère les mêmes stats mais à partir des Séries Quotidiennes de Référence (SQR), homogénéisées, pour les stations qui en disposent
scripts/diagnostic_stations_temperature.py     → vérifie la complétude TX d'une station
scripts/diagnostic_sqr.py / diagnostic_sqr_v2.py → inspecte la structure des dossiers SQR
scripts/generer_donnees_climat.py
scripts/simplifier_donnees_entzheim.py

```
Choix de SAFRAN plutôt que des stations Météo-France classiques :
Les stations Météo-France ne couvrent qu'un point précis, avec des trous fréquents (poste sans thermomètre, historique fragmenté en plusieurs identités après un changement de capteur)
SAFRAN est une réanalyse à maille régulière de 8 km.
Il fournit des séries chronologiques continues de variables atmosphériques depuis 1958 sur une grille régulière de 8 km en France métropolitaine.


## Méthodologie pour générer les données d'une maille : 
1. Récupérer la liste des mailles : un fichier GeoPackage ('safran.gpkg'), qui contient les 8602 mailles françaises avec leurs coordonnées et leur département, filtré ici aux 132 mailles Alsaciennes ('data-safran/mailles_alsace.csv', colonnes 'cell', 'longitude', 'latitude', 'altitude_m', plus 'lambx'/'lamby' en coordonnées Lambert-II étendu pour faire le lien avec les fichiers SIM).
2. Télécharger les données SIM quotidiennes sur meteo.data.gouv.fr : fichiers CSV par tranche d'années, toute la France à chaque fois. Colonnes clés : 'LAMBX', LAMBY', 'DATE', 'T' (moyenne), 'TINF_H' (min), 'TSUP_H' (max).
3. Extraire l'Alsace au fur et à mesure avec : 'extraire_alsace_safran.py' : filtre chaque fichier SIM aux 132 mailles alsaciennes et ajoute le résultat à 'jours_alsace_bruts.csv', permet de traiter les tranches d'années par lots, en supprimant les gros fichiers sources au fur et à mesure pour faire de la place sur le disque du pc.
4. Générer les JSON finaux : avec 'generer_donnees_safran.py', une fois 'jours_alsace_bruts.csv' complet sur toute la période voulue (idéalement avant 1976 pour couvrir la période de référence prise en compte, à savoir 1976-2005). 

## Projections futures (DRIAS) : 
'integrer_projections_drias.py' complète les JSON de mailles déjà générés avec des projections climatiques, à partir d'un CSV DRIAS déjà agrégé (une ligne par point de grille DRIAS et par année simulée, colonnes 'Point', 'Latitude', 'Longitude', 'Niveau', 'Annee', TMm_yr', TMm_seas_JJA', TMm_seas_DJF', 'TXm_seas_JJA', 'TX35D_yr', 'TX30D_yr', 'TR_yr', 'IFM40_yr'). 

Le 'Niveau' correspond à un Global Warming Level (GWL) : c'est à dire un seuil de réchauffement mondial atteint à une échéance donnée, plutôt qu'une date fixe. 
Actuellement sont intégrés : 
- GWL20 : réchauffement Monde +2°C / France +2.7°C (fenêtre représentative 2052-2071)
- GWL30 : réchauffement Monde +3.5 / France +4°C (fenêtre représentative 2079-2098)

Le script moyenne toutes les années de la fenêtre pour chaque point DRIAS, rattache chaque point à sa maille SAFRAN la plus proche et remplit le champ 'projections' du JSON de mailles correspondant. 
129 mailles sur 132 ont au moins un point DRIAS proche.

## Format d'un fichier sata/safran-<cell>.json
```json
{
  "station":"Maille SAFRAN 1205",
"periode_reference":"1976-2005",
"source":"Météo-France SAFRAN (réanalyse, maille 8km)",
"comparaison":{"type":"fixe", "debut":1994, "fin"2023},
"projections":{
    "GWL20":{
        "scenario":"Réchauffement Monde +2°C / France +2.7°C (2052-2071)",
        "tm_annuelle": 12.1, "tm_ete":20.4, "tm_hiver":4.2, "tx_ete":26.3,
        "jours_plus_30":9, "jours_plus_35":1, "nuits_tropicales":4,
"jours_risque_feu":2
    },
    "GWL30": {"...": même structure"}
  },
  "annees": [
    {
        "annee":1958,
        "tx_moy": 14.3, "tn_moy":5.9, "tm_moy":10.1,
        "ete_tm_moy" : 18.6, "ete_tx_moy":24.1, "hiver_tm_moy":3.0,
        "jours_chauds_25":15, "jours_chauds_30":2,
        "nuits_tropicales": 1, "jours_gel": 44, "jours_vague_chaleur": 0
    }
  ]
}
```
Le champ comparaison (fixe/variable) est présent dans les données mais n'est plus utilisé par le site. la méthode a été simplifiée en cours de route : le site compare maintenant toujours la période de référence personnelle (30 ans autour de l'année de naissance) aux 10 dernières années disponibles, sans distinction fixe/variable. 

## Format de data/communes.json

A COMPLETER

Généré automatiquement à partir d'un fichier national de communes (avec coordonnées lat/long) et de 'mailles_alsace.csv', en calculant pour chaque commune la maille SAFRAN la plus proche (distance haversine).
Dédupliqué (certains fichiers sources ont une ligne par code postal, donc plusieurs lignes pour une même commune). 

## Ajouter une commune ou une maille 
Pour les communes déjà couverte par une maille existante : ajoute une ligne dans 'communes.json' (liste 'communes') avec le bon 'station_id' (le plus simple : recalculer la distance à la maille la plus proche parmi 'mailles_alsace.csv'). 

Pour les nouvelles mailles (extension géographique au-delà de l'Alsace) : reprendre tout le pipeline SAFRAN ci-dessus pour la nouvelle zone. 

Aucune modifiqion d''index.html' n'est nécessaire dans les deux cas. 

## Fonctionnalités du site : 
- Recherche de commune par autocomplétion (882 communes, recherche insensible à la casse et aux accents, navigable au clavier).
- Slider d'année de naissance (1955-2010), avec cas particulier pour les personnes nées après 2008 (référence fixe 1993-2023), une fenêtre +/- 15 ans n'aurait pas de sens à cet âge).
- Graphique été/année : nuage de points + moyenne mobile 10 ans, avec révélation progressive au scroll (points --> courbe --> bandes de référence), point par point façon dessin animé.
- Etape 1 (contexte national) : température moyenne annuelle française 1958-2025, transformation en climate stripes, deux chiffres clés (écart à la référence, écart entre première et dernière décennie).
- Etape 7 (projections) : sélecteur GWL20/30, cartes de comparaison 'aujourd'hui --> projections' pour les indicateurs ayant un équivalent historique et cartes simples pour les indicateurs propres aux projections (jours à risque feu, jours >35°C).

## Fonctionnalité retirée 
Une section de comparaison entre deux communes (radar chart) a été implémentée puis retirée (peu d'intérêt de comparer des communes proches en Alsace, et un bug d'affichage lié au chargement de Chart.js n'a pas été entièrement résolu avant la décision de la retirer). A reconsidérer sous une autre forme si utile un jour (comparer à une ville plus éloignée, d'une autre région par exemple, ou à la moyenne nationale de l'étape 1). 

## Déploiement GitHub + Vercel : 
1. Tout le dossier (structure complète, sous dossiers data et scripts) sont déposés sur un repo Github.
2. Sur Vercel.com : add new --> Project, sélectionner le repo --> deploy
3. Chaque 'git push' déclenche un redéploiement automatique.

## Pistes d'évolution possibles : 
- Etendre au-delà de l'Alsace
- Repenser une comparaison entre communes
- Ajouter un indicateur de risque de feu de forêt en historique



