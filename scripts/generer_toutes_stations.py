# -*- coding: utf-8 -*-
"""
Un fichier Météo-France "départemental" (ex. Q_67_previous-1950-2024_RR-T-Vent.csv)
contient TOUTES les stations du département, pas une seule. Ce script les
détecte automatiquement et génère un data/<station>.json pour chacune.

Sans dépendance externe (aucun pip/conda requis) — modules standards seulement.

MARCHE À SUIVRE :
1. Vérifie CHEMIN_FICHIER ci-dessous.
2. Lance le script (IDLE : F5, ou Jupyter : Shift+Entrée).
3. Il affiche d'abord la liste des stations trouvées avec leur période de
   données disponible — regarde si celles qui t'intéressent y sont.
4. Il génère ensuite un fichier JSON par station dans le dossier courant.
"""

import csv
import json
import re
from datetime import date
from collections import defaultdict

CHEMIN_FICHIER = r"./METEO_FRANCE/Q_67_previous-1950-2024_RR-T-Vent.csv"
SEPARATEUR = ";"
PERIODE_REF = (1976, 2005)       # période de référence fixe (climatologie "ancienne")
PERIODE_ACTUELLE = (1994, 2023)  # période de comparaison fixe ("aujourd'hui"), pour les
                                  # stations à historique long (catégorie "fixe")
SEUIL_COMPLETUDE = 0.80          # seuil de complétude TX (80%) utilisé dans les deux catégories
MIN_ANNEES_VARIABLE = 20         # nb minimum d'années pour la catégorie "variable"

# Deux catégories de stations retenues :
# - "fixe"     : couvre bien 1976-2005 ET 1994-2023 (>=80% TX chacune) -> comparaison
#                identique pour toutes ces stations, la plus rigoureuse.
# - "variable" : ne couvre pas les deux périodes fixes, mais a >=80% de TX sur
#                l'ensemble de son historique (>= MIN_ANNEES_VARIABLE ans) -> le site
#                utilisera alors les 30 dernières années DE CETTE STATION comme période
#                de comparaison (moins rigoureux, mais permet d'avoir une station proche
#                dans plus d'endroits).

# ----------------------------------------------------------------------
def vers_nombre(valeur):
    if valeur is None or str(valeur).strip() == "":
        return None
    try:
        return float(str(valeur).replace(",", "."))
    except ValueError:
        return None

def slugifier(nom):
    """'STRASBOURG-ENTZHEIM' -> 'strasbourg-entzheim' (utilisable comme nom de fichier/id)"""
    nom = nom.strip().lower()
    nom = re.sub(r"[^a-z0-9]+", "-", nom)
    return nom.strip("-")

def centile_95(valeurs):
    valeurs = sorted(v for v in valeurs if v is not None)
    if not valeurs:
        return None
    index = round(0.95 * (len(valeurs) - 1))
    return valeurs[index]

def moyenne(valeurs):
    valeurs = [v for v in valeurs if v is not None]
    return round(sum(valeurs) / len(valeurs), 2) if valeurs else None

def compter_jours_vague(jours_annee):
    jours_annee = sorted(jours_annee, key=lambda j: j["date"])
    total, run = 0, 0
    for j in jours_annee:
        if j["jour_chaud_ref"]:
            run += 1
        else:
            if run >= 3:
                total += run
            run = 0
    if run >= 3:
        total += run
    return total

# ----------------------------------------------------------------------
# 1) LECTURE + regroupement par station
# ----------------------------------------------------------------------
print(f"Lecture de {CHEMIN_FICHIER} ...")
with open(CHEMIN_FICHIER, encoding="utf-8", errors="replace") as f:
    lecteur = csv.DictReader(f, delimiter=SEPARATEUR)
    colonnes = lecteur.fieldnames
    print("Colonnes détectées :", colonnes)
    lignes_brutes = list(lecteur)

print(f"{len(lignes_brutes)} lignes lues.\n")

# Colonnes habituelles Météo-France : NUM_POSTE, NOM_USUEL identifient la station
jours_par_station = defaultdict(list)

for ligne in lignes_brutes:
    brut = ligne.get("AAAAMMJJ", "").strip()
    if len(brut) != 8:
        continue
    try:
        d = date(int(brut[0:4]), int(brut[4:6]), int(brut[6:8]))
    except ValueError:
        continue

    nom_station = (ligne.get("NOM_USUEL") or ligne.get("NUM_POSTE") or "STATION_INCONNUE").strip()

    tx = vers_nombre(ligne.get("TX"))
    tn = vers_nombre(ligne.get("TN"))
    tm = vers_nombre(ligne.get("TM"))
    if tm is None and tx is not None and tn is not None:
        tm = (tx + tn) / 2

    jours_par_station[nom_station].append({
        "date": d, "annee": d.year, "mois": d.month,
        "jour_annee": d.timetuple().tm_yday,
        "tx": tx, "tn": tn, "tm": tm,
    })

# ----------------------------------------------------------------------
# 2) APERÇU DES STATIONS TROUVÉES
# ----------------------------------------------------------------------
print("="*70)
print("STATIONS TROUVÉES DANS CE FICHIER")
print("="*70)
stations_retenues = {}  # nom_station -> "fixe" | "variable"
for nom_station, jours in sorted(jours_par_station.items()):
    annees = sorted(set(j["annee"] for j in jours))
    nb_annees = len(annees)

    def completude_periode(jours, debut, fin):
        sous = [j for j in jours if debut <= j["annee"] <= fin]
        if not sous:
            return 0.0
        return sum(1 for j in sous if j["tx"] is not None) / len(sous)

    completude_ref = completude_periode(jours, *PERIODE_REF)
    completude_actuelle = completude_periode(jours, *PERIODE_ACTUELLE)
    couvre_ref = annees[0] <= PERIODE_REF[0]
    couvre_actuelle = annees[-1] >= PERIODE_ACTUELLE[1]
    est_fixe = couvre_ref and completude_ref >= SEUIL_COMPLETUDE and couvre_actuelle and completude_actuelle >= SEUIL_COMPLETUDE

    nb_tx_valides = sum(1 for j in jours if j["tx"] is not None)
    completude_globale = nb_tx_valides / len(jours) if jours else 0
    est_variable = (not est_fixe) and nb_annees >= MIN_ANNEES_VARIABLE and completude_globale >= SEUIL_COMPLETUDE

    if est_fixe:
        stations_retenues[nom_station] = "fixe"
        marque = "  ✅ FIXE (1994-2023 pour toutes les communes de cette station)"
    elif est_variable:
        stations_retenues[nom_station] = "variable"
        marque = f"  ✅ VARIABLE (complétude globale {completude_globale*100:.0f}%, période propre à cette station)"
    else:
        marque = f"  (ignorée — réf={completude_ref*100:.0f}%, actuelle={completude_actuelle*100:.0f}%, globale={completude_globale*100:.0f}%)"

    print(f"- {nom_station:35s} {annees[0]}-{annees[-1]}  ({nb_annees} années){marque}")

nb_fixe = sum(1 for v in stations_retenues.values() if v == "fixe")
nb_variable = sum(1 for v in stations_retenues.values() if v == "variable")
print(f"\n{len(stations_retenues)} station(s) seront traitées : {nb_fixe} en catégorie 'fixe', {nb_variable} en catégorie 'variable'.\n")

# ----------------------------------------------------------------------
# 3) TRAITEMENT DE CHAQUE STATION RETENUE
# ----------------------------------------------------------------------
recap = []
for nom_station, categorie in stations_retenues.items():
    jours = jours_par_station[nom_station]

    # seuil vague de chaleur (centile 95 sur période de référence, par station)
    valeurs_par_jour_annee = defaultdict(list)
    for j in jours:
        if PERIODE_REF[0] <= j["annee"] <= PERIODE_REF[1]:
            valeurs_par_jour_annee[j["jour_annee"]].append(j["tm"])
    seuil_par_jour_annee = {ja: centile_95(v) for ja, v in valeurs_par_jour_annee.items()}
    for j in jours:
        seuil = seuil_par_jour_annee.get(j["jour_annee"])
        j["jour_chaud_ref"] = (seuil is not None and j["tm"] is not None and j["tm"] > seuil)

    jours_par_annee = defaultdict(list)
    for j in jours:
        jours_par_annee[j["annee"]].append(j)

    annees_stats = []
    for annee in sorted(jours_par_annee):
        jours_annee = jours_par_annee[annee]
        ete = [j for j in jours_annee if j["mois"] in (6, 7, 8)]
        annees_stats.append({
            "annee": annee,
            "tx_moy": moyenne([j["tx"] for j in jours_annee]),
            "tn_moy": moyenne([j["tn"] for j in jours_annee]),
            "ete_tm_moy": moyenne([j["tm"] for j in ete]),
            "jours_chauds_25": sum(1 for j in jours_annee if j["tx"] is not None and j["tx"] >= 25),
            "jours_chauds_30": sum(1 for j in jours_annee if j["tx"] is not None and j["tx"] >= 30),
            "nuits_tropicales": sum(1 for j in jours_annee if j["tn"] is not None and j["tn"] >= 20),
            "jours_gel": sum(1 for j in jours_annee if j["tn"] is not None and j["tn"] < 0),
            "jours_vague_chaleur": compter_jours_vague(jours_annee),
        })

    slug = slugifier(nom_station)
    comparaison = (
        {"type": "fixe", "debut": PERIODE_ACTUELLE[0], "fin": PERIODE_ACTUELLE[1]}
        if categorie == "fixe"
        else {"type": "variable"}
    )
    payload = {
        "station": nom_station.title(),
        "periode_reference": f"{PERIODE_REF[0]}-{PERIODE_REF[1]}",
        "source": "Météo-France",
        "comparaison": comparaison,
        "projections": None,
        "annees": annees_stats,
    }
    nom_fichier = f"{slug}.json"
    with open(nom_fichier, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    recap.append((nom_station, slug, nom_fichier, len(annees_stats), categorie))
    print(f"✅ {nom_fichier} généré ({len(annees_stats)} années, {categorie}) — id à utiliser dans communes.json : \"{slug}\"")

print("\n" + "="*70)
print("RÉCAPITULATIF — à reporter dans data/communes.json (liste 'stations')")
print("="*70)
for nom_station, slug, nom_fichier, n, categorie in recap:
    print(f'{{ "id": "{slug}", "nom": "{nom_station.title()}", "fichier": "data/{nom_fichier}" }}  // {categorie}')
