# -*- coding: utf-8 -*-
"""
Version SANS AUCUNE DÉPENDANCE EXTERNE (ni pandas, ni numpy) — tout est fait
avec les modules standards de Python, déjà inclus avec IDLE. Rien à installer.

Transforme un fichier journalier Météo-France brut (AAAAMMJJ;...;TN;...;TX;...)
en data/entzheim.json pour le site.

MARCHE À SUIVRE DANS IDLE :
1. File > Open > sélectionne ce fichier.
2. Vérifie la ligne CHEMIN_FICHIER ci-dessous (même dossier que ton CSV, ou
   chemin complet).
3. Run > Run Module (ou F5).
4. Regarde la fenêtre Python Shell qui s'ouvre : elle affiche les colonnes
   détectées, puis le résultat final.
"""

import csv
import json
from datetime import date
from collections import defaultdict

# ----------------------------------------------------------------------
# 1) CONFIGURATION — adapte si besoin
# ----------------------------------------------------------------------
CHEMIN_FICHIER = "Q_67_previous-1950-2024_RR-T-Vent.csv"
SEPARATEUR = ";"          # essaie "," si le fichier ne se découpe pas bien
PERIODE_REF = (1976, 2005)

# ----------------------------------------------------------------------
# 2) LECTURE DU FICHIER
# ----------------------------------------------------------------------
def vers_nombre(valeur):
    """Convertit une valeur texte en nombre, ou None si vide/invalide."""
    if valeur is None or valeur.strip() == "":
        return None
    try:
        return float(valeur.replace(",", "."))  # au cas où décimales avec virgule
    except ValueError:
        return None

print(f"Lecture de {CHEMIN_FICHIER} ...")
with open(CHEMIN_FICHIER, encoding="utf-8", errors="replace") as f:
    lecteur = csv.DictReader(f, delimiter=SEPARATEUR)
    colonnes = lecteur.fieldnames
    print("Colonnes détectées :", colonnes)
    # 👉 Vérifie ici que AAAAMMJJ, TX, TN apparaissent bien séparément.
    #    Si tu vois une seule grosse colonne, change SEPARATEUR ci-dessus.

    lignes_brutes = list(lecteur)

print(f"{len(lignes_brutes)} lignes lues.")
print("Aperçu de la première ligne :", lignes_brutes[0] if lignes_brutes else "AUCUNE")

# ----------------------------------------------------------------------
# 3) TRANSFORMATION : une entrée par jour, avec les champs utiles
# ----------------------------------------------------------------------
jours = []
for ligne in lignes_brutes:
    brut = ligne.get("AAAAMMJJ", "").strip()
    if len(brut) != 8:
        continue
    try:
        d = date(int(brut[0:4]), int(brut[4:6]), int(brut[6:8]))
    except ValueError:
        continue

    tx = vers_nombre(ligne.get("TX"))
    tn = vers_nombre(ligne.get("TN"))
    tm = vers_nombre(ligne.get("TM"))
    if tm is None and tx is not None and tn is not None:
        tm = (tx + tn) / 2

    jours.append({
        "date": d,
        "annee": d.year,
        "mois": d.month,
        "jour_annee": d.timetuple().tm_yday,
        "tx": tx,
        "tn": tn,
        "tm": tm,
    })

print(f"{len(jours)} jours exploitables après nettoyage.")

# ----------------------------------------------------------------------
# 4) SEUIL DE VAGUE DE CHALEUR : centile 95 de TM par jour de l'année,
#    calculé sur la période de référence (méthode DRIAS simplifiée)
# ----------------------------------------------------------------------
def centile_95(valeurs):
    valeurs = sorted(v for v in valeurs if v is not None)
    if not valeurs:
        return None
    index = round(0.95 * (len(valeurs) - 1))
    return valeurs[index]

valeurs_par_jour_annee = defaultdict(list)
for j in jours:
    if PERIODE_REF[0] <= j["annee"] <= PERIODE_REF[1]:
        valeurs_par_jour_annee[j["jour_annee"]].append(j["tm"])

seuil_par_jour_annee = {
    jour_annee: centile_95(valeurs)
    for jour_annee, valeurs in valeurs_par_jour_annee.items()
}

for j in jours:
    seuil = seuil_par_jour_annee.get(j["jour_annee"])
    j["jour_chaud_ref"] = (seuil is not None and j["tm"] is not None and j["tm"] > seuil)

# ----------------------------------------------------------------------
# 5) AGRÉGATION ANNUELLE
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# 6) EXPORT JSON
# ----------------------------------------------------------------------
payload = {
    "station": "Strasbourg-Entzheim",
    "periode_reference": f"{PERIODE_REF[0]}-{PERIODE_REF[1]}",
    "source": "Météo-France",
    "projections": None,
    "annees": annees_stats,
}

with open("entzheim.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"\n✅ entzheim.json généré : {len(annees_stats)} années "
      f"({annees_stats[0]['annee']}–{annees_stats[-1]['annee']})")
print("   Déplace ce fichier dans data/entzheim.json à la racine du projet.")
