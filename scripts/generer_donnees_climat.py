# -*- coding: utf-8 -*-
"""
Génère le fichier data/<ville>.json attendu par le site, à partir :
  (A) de données journalières brutes Météo-France (colonnes AAAAMMJJ, TX, TN)
  (B) ou de stats annuelles déjà calculées par ton pipeline existant

Utilisation typique (à adapter dans le bloc __main__ tout en bas) :

    df = pd.read_csv(r"C:\...\strasbourg_quotidien.csv", sep=";")
    stats = calculer_stats_annuelles(
        df,
        col_date="AAAAMMJJ",
        col_tx="TX",
        col_tn="TN",
        periode_reference=(1976, 2005),
    )
    exporter_json(stats, ville="Strasbourg", station="Strasbourg-Entzheim",
                  periode_reference="1976-2005", chemin_sortie="../data/strasbourg.json")

Si tu as DÉJÀ un DataFrame de stats annuelles (une ligne par année, une colonne
par indicateur), saute calculer_stats_annuelles() et va directement à
exporter_json_depuis_stats_existantes() — voir plus bas.
"""

import json
import pandas as pd
import numpy as np


# ----------------------------------------------------------------------
# CAS A : tu pars de données journalières brutes
# ----------------------------------------------------------------------
def calculer_stats_annuelles(df, col_date="AAAAMMJJ", col_tx="TX", col_tn="TN",
                              periode_reference=(1976, 2005)):
    """
    df : DataFrame journalier avec au minimum une colonne date (format AAAAMMJJ,
         ex 19550101) et les colonnes de température max (TX) et min (TN) en °C.

    Retourne un DataFrame avec une ligne par année et les colonnes :
    annee, tx_moy, tn_moy, jours_chauds_25, jours_chauds_30,
    nuits_tropicales, jours_gel, jours_vague_chaleur
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df[col_date], format="%Y%m%d")
    df["annee"] = df["date"].dt.year
    df["tm"] = (df[col_tx] + df[col_tn]) / 2

    # --- seuil de vague de chaleur : centile 95 de TM sur la période de référence ---
    ref = df[(df["annee"] >= periode_reference[0]) & (df["annee"] <= periode_reference[1])]
    seuil_centile = ref.groupby(ref["date"].dt.dayofyear)["tm"].quantile(0.95)
    df["seuil_jour"] = df["date"].dt.dayofyear.map(seuil_centile)
    df["jour_chaud_ref"] = df["tm"] > df["seuil_jour"]

    # une "vague de chaleur" = un jour appartenant à une série d'au moins 3 jours
    # consécutifs au-dessus du seuil (méthode DRIAS simplifiée)
    def compter_jours_vague(sous_df):
        sous_df = sous_df.sort_values("date")
        est_chaud = sous_df["jour_chaud_ref"].values
        total = 0
        run = 0
        for v in est_chaud:
            if v:
                run += 1
            else:
                if run >= 3:
                    total += run
                run = 0
        if run >= 3:
            total += run
        return total

    lignes = []
    for annee, groupe in df.groupby("annee"):
        ete = groupe[groupe["date"].dt.month.isin([6, 7, 8])]
        lignes.append({
            "annee": int(annee),
            "tx_moy": round(groupe[col_tx].mean(), 2),
            "tn_moy": round(groupe[col_tn].mean(), 2),
            "ete_tm_moy": round(ete["tm"].mean(), 2) if len(ete) else None,
            "jours_chauds_25": int((groupe[col_tx] >= 25).sum()),
            "jours_chauds_30": int((groupe[col_tx] >= 30).sum()),
            "nuits_tropicales": int((groupe[col_tn] >= 20).sum()),
            "jours_gel": int((groupe[col_tn] < 0).sum()),
            "jours_vague_chaleur": compter_jours_vague(groupe),
        })

    return pd.DataFrame(lignes).sort_values("annee").reset_index(drop=True)


# ----------------------------------------------------------------------
# CAS B : tu as déjà un DataFrame de stats annuelles (ton pipeline existant)
# ----------------------------------------------------------------------
def adapter_stats_existantes(df, mapping_colonnes):
    """
    Si tes colonnes ne s'appellent pas exactement comme le schéma attendu,
    passe un dict de correspondance, ex :

    mapping_colonnes = {
        "year": "annee",
        "txmoy": "tx_moy",
        "tnmoy": "tn_moy",
        "nb_j_chauds25": "jours_chauds_25",
        "nb_j_chauds30": "jours_chauds_30",
        "nb_nuits_trop": "nuits_tropicales",
        "nb_j_gel": "jours_gel",
        "nb_j_canicule": "jours_vague_chaleur",
    }
    """
    df2 = df.rename(columns=mapping_colonnes)
    colonnes_requises = ["annee", "tx_moy", "tn_moy", "jours_chauds_25",
                          "jours_chauds_30", "nuits_tropicales", "jours_gel",
                          "jours_vague_chaleur"]
    manquantes = [c for c in colonnes_requises if c not in df2.columns]
    if manquantes:
        raise ValueError(f"Colonnes manquantes après mapping : {manquantes}")

    # ete_tm_moy est optionnelle (indicateur "vedette" été) : si absente, on la
    # laisse à None, le site désactivera simplement la section été.
    if "ete_tm_moy" not in df2.columns:
        df2["ete_tm_moy"] = None

    colonnes_attendues = colonnes_requises[:3] + ["ete_tm_moy"] + colonnes_requises[3:]
    return df2[colonnes_attendues].sort_values("annee").reset_index(drop=True)


# ----------------------------------------------------------------------
# Export JSON commun aux deux cas
# ----------------------------------------------------------------------
def exporter_json(stats_df, station, periode_reference, chemin_sortie):
    payload = {
        "station": station,
        "periode_reference": periode_reference,
        "source": "Météo-France",
        "projections": None,
        "annees": stats_df.to_dict(orient="records"),
    }
    with open(chemin_sortie, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"✅ {chemin_sortie} généré ({len(stats_df)} années, {stats_df['annee'].min()}-{stats_df['annee'].max()})")


def ajouter_station_dans_index(chemin_communes_json, station_id, station_nom, fichier_relatif):
    """Ajoute/actualise une station dans la liste 'stations' de data/communes.json.
    Ne touche pas à la liste 'communes' (rattachement commune -> station), que tu
    complètes toi-même à la main selon les communes que tu veux proposer."""
    with open(chemin_communes_json, "r", encoding="utf-8") as f:
        index = json.load(f)

    entree = {"id": station_id, "nom": station_nom, "fichier": fichier_relatif}
    index["stations"] = [s for s in index["stations"] if s["id"] != station_id]
    index["stations"].append(entree)
    index["stations"].sort(key=lambda s: s["nom"])

    with open(chemin_communes_json, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"✅ data/communes.json mis à jour ({len(index['stations'])} stations). "
          f"Pense à ajouter les communes rattachées à '{station_id}' dans la liste 'communes'.")


# ----------------------------------------------------------------------
if __name__ == "__main__":
    # ============ EXEMPLE — adapte ces lignes à ta situation ============

    # --- Cas A : données journalières brutes ---
    # df_brut = pd.read_csv(r"C:\Users\PaulineJoly\...\entzheim_quotidien.csv", sep=";")
    # stats = calculer_stats_annuelles(df_brut, periode_reference=(1976, 2005))
    # exporter_json(stats, "Strasbourg-Entzheim", "1976-2005", "../data/entzheim.json")
    # ajouter_station_dans_index("../data/communes.json", "entzheim",
    #                            "Strasbourg-Entzheim", "data/entzheim.json")

    # --- Cas B : stats annuelles déjà calculées par ton pipeline existant ---
    # df_stats = pd.read_csv(r"C:\...\marignane_stats_annuelles.csv")
    # stats = adapter_stats_existantes(df_stats, mapping_colonnes={...})
    # exporter_json(stats, "Marignane", "1976-2005", "../data/marignane.json")
    # ajouter_station_dans_index("../data/communes.json", "marignane",
    #                            "Marignane", "data/marignane.json")

    print("Décommente et adapte le bloc correspondant à ton cas (A ou B) ci-dessus.")
