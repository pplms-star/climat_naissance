# -*- coding: utf-8 -*-
"""
Fusionne les Séries Quotidiennes de Référence (SQR) TX + TN, station par
station, en JSON au format attendu par le site. Ne traite que les stations
qui ont à la fois un fichier TX et un fichier TN (les autres, comme
Colmar-INRAE qui n'a pas de TN homogénéisée, gardent leur version basée sur
les données brutes générée précédemment par generer_toutes_stations.py).

Format des fichiers SQR : quelques lignes d'en-tête commençant par '#'
(NUM_POSTE, NOM_USUEL, période couverte...), puis des lignes
AAAAMMJJ;VALEUR;Q_SQR (Q_SQR=1 : donnée homogénéisée officielle ;
Q_SQR=0 : donnée brute utilisée pour prolonger la série au-delà de la
période officiellement homogénéisée).
"""

import csv
import json
import re
import os
from datetime import date
from collections import defaultdict

DOSSIER_TX = r"./SQR_TX"
DOSSIER_TN = r"./SQR_TN"
PERIODE_REF = (1976, 2005)
PERIODE_ACTUELLE = (1994, 2023)
SEUIL_COMPLETUDE = 0.80
MIN_ANNEES_VARIABLE = 20

# ----------------------------------------------------------------------
def slugifier(nom):
    nom = nom.strip().lower()
    nom = re.sub(r"[^a-z0-9]+", "-", nom)
    return nom.strip("-")

def departement_depuis_num_poste(num_poste):
    return str(num_poste).strip().zfill(8)[:2]

def lire_fichier_sqr(chemin):
    """Retourne (num_poste, nom_usuel, {date: valeur})."""
    meta = {}
    valeurs = {}
    with open(chemin, encoding="utf-8", errors="replace") as f:
        lignes = f.readlines()

    debut_donnees = 0
    for i, ligne in enumerate(lignes):
        ligne = ligne.rstrip("\n")
        if ligne.startswith("#"):
            if "=" in ligne:
                cle, _, valeur = ligne.lstrip("# ").partition("=")
                meta[cle.strip()] = valeur.strip()
        else:
            debut_donnees = i
            break

    lecteur = csv.DictReader(lignes[debut_donnees:], delimiter=";")
    for ligne in lecteur:
        brut = ligne.get("AAAAMMJJ", "").strip()
        if len(brut) != 8:
            continue
        try:
            d = date(int(brut[0:4]), int(brut[4:6]), int(brut[6:8]))
        except ValueError:
            continue
        v = ligne.get("VALEUR", "").strip()
        if v == "":
            continue
        try:
            valeurs[d] = float(v.replace(",", "."))
        except ValueError:
            continue

    return meta.get("NUM_POSTE", ""), meta.get("NOM_USUEL", "STATION_INCONNUE"), valeurs

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
# 1) Indexer les fichiers TX et TN par NUM_POSTE (dept 67/68 seulement)
# ----------------------------------------------------------------------
def indexer_dossier(dossier):
    index = {}
    for nom_fichier in os.listdir(dossier):
        if not nom_fichier.lower().endswith(".csv"):
            continue
        chemin = os.path.join(dossier, nom_fichier)
        num_poste, nom_usuel, valeurs = lire_fichier_sqr(chemin)
        if departement_depuis_num_poste(num_poste) in ("67", "68"):
            index[num_poste] = (nom_usuel, valeurs)
    return index

print("Indexation des fichiers TX...")
index_tx = indexer_dossier(DOSSIER_TX)
print(f"  {len(index_tx)} station(s) alsacienne(s) en TX")

print("Indexation des fichiers TN...")
index_tn = indexer_dossier(DOSSIER_TN)
print(f"  {len(index_tn)} station(s) alsacienne(s) en TN")

communes_communes = set(index_tx) & set(index_tn)
print(f"\n{len(communes_communes)} station(s) avec TX + TN disponibles : "
      f"{[index_tx[n][0] for n in communes_communes]}")
manquantes_tn = set(index_tx) - set(index_tn)
if manquantes_tn:
    print(f"⚠️ Stations avec TX mais SANS TN (non traitées ici, gardent leur "
          f"version 'données brutes' précédente) : {[index_tx[n][0] for n in manquantes_tn]}")

# ----------------------------------------------------------------------
# 2) Fusionner TX+TN par station et générer les JSON
# ----------------------------------------------------------------------
recap = []
for num_poste in communes_communes:
    nom_station, valeurs_tx = index_tx[num_poste]
    _, valeurs_tn = index_tn[num_poste]

    toutes_dates = sorted(set(valeurs_tx) | set(valeurs_tn))
    jours = []
    for d in toutes_dates:
        tx = valeurs_tx.get(d)
        tn = valeurs_tn.get(d)
        tm = (tx + tn) / 2 if (tx is not None and tn is not None) else None
        jours.append({
            "date": d, "annee": d.year, "mois": d.month,
            "jour_annee": d.timetuple().tm_yday,
            "tx": tx, "tn": tn, "tm": tm,
        })

    annees = sorted(set(j["annee"] for j in jours))

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
    est_variable = (not est_fixe) and len(annees) >= MIN_ANNEES_VARIABLE and completude_globale >= SEUIL_COMPLETUDE

    if not (est_fixe or est_variable):
        print(f"⚠️ {nom_station} : complétude insuffisante même en SQR ({completude_globale*100:.0f}%), ignorée")
        continue

    # seuil vague de chaleur
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
        if est_fixe else {"type": "variable"}
    )
    payload = {
        "station": nom_station.title(),
        "periode_reference": f"{PERIODE_REF[0]}-{PERIODE_REF[1]}",
        "source": "Météo-France (SQR - séries quotidiennes de référence, homogénéisées)",
        "comparaison": comparaison,
        "projections": None,
        "annees": annees_stats,
    }
    nom_fichier = f"{slug}.json"
    with open(nom_fichier, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    categorie = "fixe" if est_fixe else "variable"
    recap.append((nom_station, slug, nom_fichier, len(annees_stats), categorie))
    print(f"✅ {nom_fichier} généré ({len(annees_stats)} années, {categorie}, SQR) — id : \"{slug}\"")

print("\n" + "="*70)
print("RÉCAPITULATIF — à reporter dans data/communes.json (liste 'stations')")
print("="*70)
for nom_station, slug, nom_fichier, n, categorie in recap:
    print(f'{{ "id": "{slug}", "nom": "{nom_station.title()}", "fichier": "data/{nom_fichier}" }}  // {categorie}, SQR')
