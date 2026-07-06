# Le climat a-t-il changé depuis ta naissance ?

Site statique en format "scrollytelling" : une phrase à trous (année de
naissance + ville) déclenche un récit qui se construit au scroll, comparant
la **période de référence personnelle** de l'utilisateur·rice (30 ans
centrés sur sa naissance, calée sur les données disponibles) à la
**normale climatique actuelle** (les 30 dernières années disponibles,
1995–2023 avec les données livrées).

Inspiré du format de RTBF sur le même sujet
(a-quel-point-fait-il-plus-chaud-dans-votre-commune-depuis-votre-naissance-faites-le-test)
mad-lib en intro, sections qui se révèlent au scroll, nuage de points +
moyenne mobile 10 ans pour les indicateurs vedettes.

## Structure

```
index.html                          → le site (HTML + CSS + JS, un seul fichier)
data/communes.json                  → correspondance commune → station (menu déroulant)
data/"nom commune".json                  → stats annuelles par station
scripts/generer_donnees_climat.py   → script Python pour générer les vrais JSON par station
```


## Pourquoi "commune → station" et pas "ville → fichier" ?

Météo-France n'a une station températures que dans certaines communes. Pour proposer un choix réaliste de communes dans le
menu déroulant — y compris celles sans station — chaque commune est
rattachée dans `data/communes.json` à la **station la plus proche**, dont
les données sont utilisées comme approximation. Le site l'indique
honnêtement à l'utilisateur·rice ("il n'y a pas de station à X, on utilise
les relevés de Y, à Z km").

Une station peut couvrir plusieurs communes sans dupliquer aucune donnée :
ajouter une commune ne demande qu'une ligne dans `communes.json`, pas un
nouveau traitement de données.

## Générer les vraies données d'une station

1. Ouvre `scripts/generer_donnees_climat.py`.
2. Dans le bloc `if __name__ == "__main__":`, choisis ton cas :
   - **Cas A** : tu as des données journalières brutes (colonnes date, TX, TN)
     → utilise `calculer_stats_annuelles()`.
   - **Cas B** : tu as déjà des stats annuelles calculées par ton pipeline
     Strasbourg/Marseille existant → utilise `adapter_stats_existantes()`
     avec un `mapping_colonnes` qui fait correspondre tes noms de colonnes
     aux noms attendus (`annee`, `tx_moy`, `tn_moy`, `jours_chauds_25`,
     `jours_chauds_30`, `nuits_tropicales`, `jours_gel`, `jours_vague_chaleur`).
3. Lance le script : `python scripts/generer_donnees_climat.py`
   → ça écrit `data/<station>.json` et met à jour la liste `stations` de
   `data/communes.json`. Ensuite, ajoute à la main les communes que tu veux
   rattacher à cette station dans la liste `communes` du même fichier.

## Ajouter une commune

Deux cas :

- **La commune est déjà couverte par une station existante** (ex. tu veux
  ajouter Illkirch, déjà proche d'Entzheim) : ajoute juste une ligne dans
  la liste `communes` de `data/communes.json`, avec le `station_id` de la
  station la plus proche et la distance en km. Aucun traitement de données
  nécessaire.

- **Nouvelle station** (ex. Lyon-Bron) : génère son `data/<station>.json`
  avec le script (étape ci-dessus), qui ajoute automatiquement la station
  à la liste `stations`, puis ajoute les communes qui s'y rattachent dans
  la liste `communes`.

Aucune modification d'`index.html` n'est nécessaire dans les deux cas — le
menu déroulant se construit dynamiquement à partir de `communes.json`.

## Format attendu d'un fichier data/<station>.json

```json
{
  "station": "Strasbourg-Entzheim",
  "periode_reference": "1976-2005",
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

## Format attendu de data/communes.json

```json
{
  "communes": [
    { "commune": "Schiltigheim", "station_id": "entzheim", "distance_km": 15 }
  ],
  "stations": [
    { "id": "entzheim", "nom": "Strasbourg-Entzheim", "fichier": "data/entzheim.json" }
  ]
}
```

`ete_tm_moy` = moyenne de la température moyenne quotidienne ((Tx+Tn)/2) sur
juin-juillet-août. C'est l'indicateur "vedette" de la section été. Il est
optionnel : si absent (`null`), la section été affichera simplement des
valeurs manquantes — pense à le calculer si tu veux cette section complète.

`projections` est un champ **réservé pour plus tard** (scénarios climatiques
futurs, données DRIAS). Tant qu'il vaut `null`, le site affiche une section
"à venir" en placeholder. Le jour où tu auras ces données, il suffira de
remplir ce champ (structure à définir le moment venu) — `index.html` a déjà
un point d'accroche (`if(data.projections){...}`) pour construire cette
section sans toucher au reste du site.

## Déploiement sur GitHub + Vercel

1. **Créer le repo GitHub**
   ```
   cd projet-climat-naissance
   git init
   git add .
   git commit -m "Premier commit"
   ```
   Puis sur github.com : crée un nouveau repository (ex. `climat-naissance`),
   sans README/gitignore (tu les as déjà), et suis les instructions
   "…or push an existing repository from the command line" affichées sur
   GitHub pour relier ton dossier local et pousser (`git remote add origin …`
   puis `git push -u origin main`).

2. **Déployer sur Vercel**
   - Va sur vercel.com, connecte-toi avec ton compte GitHub.
   - "Add New… → Project", sélectionne le repo `climat-naissance`.
   - Aucune configuration nécessaire : c'est un site statique, Vercel le
     détecte automatiquement (pas de "Build command", pas de "Framework").
   - Clique "Deploy". Ton site est en ligne en quelques secondes, avec une
     URL du type `climat-naissance.vercel.app`.

3. **Mises à jour ultérieures**
   Chaque fois que tu ajoutes une commune ou une station, il suffit de :
   ```
   git add .
   git commit -m "Ajout de Lyon"
   git push
   ```
   Vercel redéploie automatiquement à chaque push.

## Pistes d'évolution possibles

- Renforcer le scrolytelling
- Comparer deux communes côte à côte.
- Ajouter les précipitations (jours de fortes pluies, sécheresse).
- Export du graphique en image (via `canvas.toDataURL()` sur les graphiques Chart.js).
