[README.md](https://github.com/user-attachments/files/29789842/README.md)
# Le climat a-t-il changé depuis ta naissance ? (Alsace)

Site statique en format "scrollytelling" : une phrase à trous (année de
naissance + commune) déclenche un récit qui se construit au scroll,
comparant la **période de référence personnelle** (30 ans centrés sur la
naissance) à une **période actuelle** de 30 ans — fixe (1994-2023) pour les
stations à très long historique, ou glissante (30 dernières années
disponibles) pour les autres.

Couverture actuelle : Alsace uniquement (Bas-Rhin + Haut-Rhin), 36 stations
Météo-France, 64 communes rattachées.

## Structure

```
index.html                                    → le site (HTML + CSS + JS, un seul fichier)
data/communes.json                            → correspondance commune → station
data/<station>.json                           → stats annuelles par station (36 fichiers)
scripts/generer_toutes_stations.py            → génère les stats depuis un fichier
                                                 Météo-France départemental brut (Q_67_.../Q_68_...)
scripts/fusionner_sqr.py                       → génère les mêmes stats mais à partir des
                                                 Séries Quotidiennes de Référence (SQR),
                                                 homogénéisées, pour les stations qui en disposent
scripts/diagnostic_stations_temperature.py     → vérifie la complétude TX d'une station
scripts/diagnostic_sqr.py / diagnostic_sqr_v2.py → inspecte la structure des dossiers SQR
```

## Deux sources de données possibles, une même sortie

Le site ne fait aucune différence entre les deux : les deux scripts
produisent le même format JSON, avec un champ `"comparaison"` qui indique
au site quelle période "actuelle" utiliser pour cette station.

- **`generer_toutes_stations.py`** : à partir d'un fichier Météo-France
  "quotidien" brut téléchargé sur meteo.data.gouv.fr (un fichier par
  département, toutes les stations dedans). Simple à obtenir, mais certaines
  stations sont fragmentées en plusieurs identités (ex. `STATTMATTEN` /
  `STATTMATTEN SA`) à cause de changements de capteur ou de site.

- **`fusionner_sqr.py`** : à partir des **Séries Quotidiennes de Référence**
  (SQR) de Météo-France — des séries homogénéisées et "aboutées" (Météo-France
  recolle les ruptures dues aux changements de station). Meilleure qualité,
  mais ne couvre qu'une sélection restreinte de stations de référence
  (téléchargeable sur meteo.data.gouv.fr, un dossier de fichiers CSV par
  paramètre TX/TN, un fichier par station).

  ⚠️ Les fichiers SQR n'ont pas toujours TX et TN toutes les deux pour une
  même station (ex. Colmar-INRAE a du TX mais pas de TN en SQR) — dans ce
  cas, `fusionner_sqr.py` ignore cette station et on garde sa version issue
  de `generer_toutes_stations.py`.

  Actuellement, 5 stations utilisent les données SQR (Strasbourg-Botanique,
  Strasbourg-Entzheim, Mulhouse, Bâle-Mulhouse, Colmar-Meyenheim) ; les
  autres utilisent les données brutes départementales.

## Classification automatique : "fixe" ou "variable"

Chaque station est classée automatiquement selon la qualité de son historique :

- **`fixe`** : couvre bien (≥80% de jours avec TX valide) à la fois
  1976-2005 (référence climatologique) et 1994-2023 (référence actuelle).
  Comparaison la plus rigoureuse — identique pour toutes les stations "fixe".
- **`variable`** : ne couvre pas les deux périodes fixes, mais a ≥80% de
  complétude sur l'ensemble de son historique (≥20 ans). Le site utilise
  alors les 30 dernières années disponibles **pour cette station précisément**
  (donc cette borne varie d'une station à l'autre).
- Toute autre station (trop peu de données, ou poste pluviométrique sans
  thermomètre) est ignorée.

## Format d'un fichier data/<station>.json

```json
{
  "station": "Strasbourg-Entzheim",
  "periode_reference": "1976-2005",
  "source": "Météo-France (SQR - séries quotidiennes de référence, homogénéisées)",
  "comparaison": { "type": "fixe", "debut": 1994, "fin": 2023 },
  "projections": null,
  "annees": [
    {
      "annee": 1955,
      "tx_moy": 14.3,
      "tn_moy": 5.9,
      "ete_tm_moy": 18.6,
      "jours_chauds_25": 16,
      "jours_chauds_30": 2,
      "nuits_tropicales": 1,
      "jours_gel": 44,
      "jours_vague_chaleur": 0
    }
  ]
}
```

Pour une station "variable", `"comparaison"` vaut `{ "type": "variable" }`
(pas de `debut`/`fin`, calculés dynamiquement par le site).

## Format de data/communes.json

```json
{
  "communes": [
    { "commune": "Schiltigheim", "station_id": "strasbourg-botanique", "distance_km": 3 }
  ],
  "stations": [
    { "id": "strasbourg-botanique", "nom": "Strasbourg-Botanique", "fichier": "data/strasbourg-botanique.json" }
  ]
}
```

## Ajouter une commune ou une station

- **Commune déjà couverte par une station existante** : ajoute une ligne
  dans `communes.json` (liste `communes`) avec le bon `station_id`.
- **Nouvelle station** : génère son JSON avec l'un des deux scripts
  ci-dessus, ajoute-la dans la liste `stations`, puis rattache les communes
  concernées dans la liste `communes`.

Aucune modification d'`index.html` n'est nécessaire dans les deux cas.

## Déploiement GitHub + Vercel

1. Pousse tout le dossier (structure complète, avec les sous-dossiers
   `data/` et `scripts/`) sur un repo GitHub — utilise GitHub Desktop plutôt
   que le glisser-déposer web si tu as plusieurs dizaines de fichiers, le
   glisser-déposer web ne gère pas toujours bien les sous-dossiers.
2. Sur vercel.com : "Add New… → Project" → sélectionne le repo → "Deploy"
   (site statique, aucune configuration nécessaire).
3. Chaque `git push` déclenche un redéploiement automatique.

## Pistes d'évolution possibles

- Étendre au-delà de l'Alsace avec la même méthode (un fichier départemental
  Météo-France + `generer_toutes_stations.py`).
- Utiliser SAFRAN (réanalyse Météo-France, grille 8km, couvre toute la
  France sans dépendre de la présence d'une station) pour éliminer le
  compromis fixe/variable — piste explorée mais pas encore implémentée,
  format plus technique (NetCDF) que les CSV utilisés ici.
- Ajouter les projections climatiques futures (DRIAS) — le champ
  `"projections"` est déjà prévu dans le schéma, actuellement à `null`.
- Comparaison entre deux communes (déjà implémentée, étape 7 du site).
