"""
featuretype_audit.py

Loads Alcedo_structured.csv, applies a featuretype → WHG fclass mapping,
and writes two files to whg/output/:

  featuretype_fclass.csv   — every distinct featuretype with its count,
                             assigned fclass, and a notes column for review
  audit_summary.txt        — row-count breakdown by fclass / exclude / unmapped
"""

import os
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_IN  = os.path.join(ROOT, "UpdateDataWorkflow", "csv", "Alcedo_structured.csv")
OUT_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))

# ── Featuretype → fclass mapping ──────────────────────────────────────────────
# WHG fclass codes:
#   A  Administrative entities (provinces, counties, kingdoms)
#   H  Water bodies (rivers, lakes, bays, straits)
#   L  Landscape / regions (indigenous nations, named territories)
#   P  Populated places (towns, villages, cities)
#   R  Roads / routes / bridges
#   S  Sites (forts, mines, churches, buildings)
#   T  Terrestrial landforms (mountains, islands, capes, valleys)
#
# None  → EXCLUDE from WHG ingest (non-geographic vocabulary or metadata noise)

FCLASS = {

    # ── Populated places (P) ─────────────────────────────────────────────────
    "Pueblo":                    "P",
    "Ciudad":                    "P",
    "Villa":                     "P",
    "Pueblo Cabecera":           "P",
    "Pueblo de Indios":          "P",
    "Pueblo Parroquia":          "P",
    "Pueblo Real de Minas":      "P",
    "Barrio":                    "P",
    "Capital":                   "P",
    "Pueblo Asiento de Minas":   "P",
    "Pueblo Capital":            "P",
    "Aldea":                     "P",
    "Pueblo Presidio":           "P",
    "Colonia":                   "P",
    "Población":                 "P",
    "Villa Presidio":            "P",
    "Pueblo Reducción":          "P",
    "Villa Capital":             "P",
    "Pueblo Establecimiento":    "P",
    "Pueblo Aldea":              "P",
    "Pueblo Puerto":             "P",
    "Pueblos":                   "P",
    "Establecimiento":           "P",
    "Villa Cabecera":            "P",
    "Ciudad Cabecera":           "P",
    "Presidio":                  "P",
    "Ciudad Puerto":             "P",
    "Ciudad Bahía":              "P",
    "Villa Real de Minas":       "P",
    "Villa Puerto":              "P",
    "Settlement":                "P",
    "Lugar":                     "P",
    "Rancho":                    "P",
    "Pueblo Misión":             "P",
    "Pueblo Fuerte":             "P",
    "Pueblo Fortaleza":          "P",
    "Pueblo Colonia":            "P",
    "Ciudad Colonia":            "P",
    "Ciudad Presidio":           "P",
    "Ciudades":                  "P",
    "Asiento de Minas":          "P",
    "Asiento":                   "P",
    "Ciudad Capital":            "P",
    "Villa Fuerte":              "P",
    "Puerto":                    "P",
    "Curato":                    "P",

    # ── Administrative (A) ───────────────────────────────────────────────────
    "Provincia":                 "A",
    "Condado":                   "A",
    "Jurisdicción":              "A",
    "Partido":                   "A",
    "Alcaldía mayor":            "A",
    "Reyno":                     "A",
    "País":                      "A",
    "Territorio":                "A",
    "Cantón":                    "A",
    "Distrito":                  "A",
    "República":                 "A",
    "Feudo":                     "A",
    "Parte del mundo":           "A",

    # ── Landscape / regions (L) ──────────────────────────────────────────────
    "Nación":                    "L",
    "Tribu":                     "L",
    "Selva":                     "L",
    "Desierto":                  "L",
    "Tierra":                    "L",

    # ── Water bodies (H) ─────────────────────────────────────────────────────
    "Rio":                       "H",
    "Río":                       "H",
    "Rios":                      "H",
    "Bahía":                     "H",
    "Laguna":                    "H",
    "Lagunas":                   "H",
    "Lago":                      "H",
    "Estrecho":                  "H",
    "Canal":                     "H",
    "Mar":                       "H",
    "Golfo":                     "H",
    "Ensenada":                  "H",
    "Ensenadas":                 "H",
    "Caleta":                    "H",
    "Brazo":                     "H",
    "Brazos":                    "H",
    "Boca":                      "H",
    "Barra":                     "H",
    "Angostura":                 "H",
    "Estrechura":                "H",
    "Abertura":                  "H",
    "Entrada":                   "H",
    "Caño":                      "H",
    "Estero":                    "H",
    "Arroyo":                    "H",
    "Manantiales":               "H",
    "Fuente":                    "H",
    "Raudal":                    "H",
    "Salto":                     "H",
    "Cascada":                   "H",
    "Confluente":                "H",
    "Torrente":                  "H",
    "Ciénega":                   "H",
    "Estanque":                  "H",
    "Remolino":                  "H",
    "Rada":                      "H",
    "Seno":                      "H",
    "Baxo":                      "H",
    "Baxos":                     "H",
    "Banco":                     "H",
    "Bancos":                    "H",
    "Aguaje":                    "H",
    "Salinas":                   "H",
    "Vado":                      "H",

    # ── Terrestrial landforms (T) ─────────────────────────────────────────────
    "Isla":                      "T",
    "Islas":                     "T",
    "Islote":                    "T",
    "Islotes":                   "T",
    "Isleta":                    "T",
    "Isletas":                   "T",
    "ISla":                      "T",
    "Cayo":                      "T",
    "Cayos":                     "T",
    "Archipiélago":              "T",
    "Monte":                     "T",
    "Montes":                    "T",
    "Montaña":                   "T",
    "Montañas":                  "T",
    "Cerro":                     "T",
    "Cerros":                    "T",
    "Sierra":                    "T",
    "Sierras":                   "T",
    "Cordillera":                "T",
    "Cordilleras":               "T",
    "Cadena de montañas":        "T",
    "Volcán":                    "T",
    "Valle":                     "T",
    "Valles":                    "T",
    "Llanura":                   "T",
    "Llanuras":                  "T",
    "Llano":                     "T",
    "Punta":                     "T",
    "Punta de tierra":           "T",
    "Punta de Tierra":           "T",
    "Cabo":                      "T",
    "Extremidad":                "T",
    "Promontorio":               "T",
    "Farallón":                  "T",
    "Peñasco":                   "T",
    "Peñascos":                  "T",
    "Peña":                      "T",
    "Peñas":                     "T",
    "Fila de peñas":             "T",
    "Murallón de peña":          "T",
    "Rocas":                     "T",
    "Morro":                     "T",
    "Páramo":                    "T",
    "Istmo":                     "T",
    "Península":                 "T",
    "Costa":                     "T",
    "Altos":                     "T",
    "Colinas":                   "T",
    "Terreno":                   "T",
    "Nueva tierra":              "T",
    "Cueva":                     "T",
    "Paso":                      "T",
    "Abra":                      "T",
    "Médanos":                   "T",
    "Bosque":                    "T",
    "Potreros":                  "T",
    "Playa":                     "T",
    "Playón":                    "T",
    "Atalaya":                   "T",

    # ── Sites / structures (S) ───────────────────────────────────────────────
    "Fuerte":                    "S",
    "Fuerte Presidio":           "S",
    "Fortaleza":                 "S",
    "Castillo":                  "S",
    "Torreón":                   "S",
    "Mina":                      "S",
    "Minas":                     "S",
    "Real de minas":             "S",
    "Santuario":                 "S",
    "Hermita":                   "S",
    "Colegio":                   "S",
    "Cruz":                      "S",
    "Obrage":                    "S",
    "Plantación":                "S",
    "Habitación":                "S",
    "Ramo":                      "S",

    # ── Roads / routes (R) ───────────────────────────────────────────────────
    "Puente":                    "R",
    "Camino":                    "R",

    # ── Stragglers (rare, added after first audit pass) ───────────────────────
    "Lengua de tierra":          "T",   # spit / tongue of land
    "Ciudad Condado":            "P",   # county seat
    "Placer de arena":           "T",   # sandbar / placer
    "Pántano":                   "H",   # marsh / swamp

    # ── Exclude — non-geographic vocabulary ──────────────────────────────────
    "Animal":                    None,
    "Botany":                    None,
    "Nutriment":                 None,
    "Social":                    None,
    "Pharmacy":                  None,
    "Produce":                   None,
    "Textiles":                  None,
    "Construction":              None,
    "Mineralogy":                None,
    "Climate":                   None,
    "Measurement":               None,
    "Activity":                  None,
    "Illness":                   None,

    # ── Exclude — metadata / catch-all ───────────────────────────────────────
    "placename":                 None,
    "Landmark":                  None,
    "Synonym":                   None,
    "Sinonimo":                  None,
    "-":                         None,
    "Term":                      None,
    "Referral":                  None,

    # ── Needs per-record review (too vague or dependent) ─────────────────────
    "Parte":                     None,
    "Pedazo":                    None,
    "Parage":                    None,
    "Cabeza":                    None,
    "Raza":                      None,
    "Casta":                     None,
    "Mote":                      None,
    "Pasage":                    None,
    "Caida":                     None,
    "Despoblado":                None,
    "Sitio":                     None,
    "Institution":               None,
    "Structure":                 None,
}

FCLASS_LABELS = {
    "A": "Administrative",
    "H": "Water body",
    "L": "Landscape / region",
    "P": "Populated place",
    "R": "Road / route",
    "S": "Site / structure",
    "T": "Terrestrial landform",
}


def main():
    df = pd.read_csv(DATA_IN, sep="|", low_memory=False)
    total = len(df)

    # ── Build featuretype summary table ───────────────────────────────────────
    counts = df["featuretype"].value_counts(dropna=False).reset_index()
    counts.columns = ["featuretype", "count"]
    counts["featuretype_str"] = counts["featuretype"].astype(str)
    counts["fclass"] = counts["featuretype_str"].map(FCLASS)
    counts["fclass_label"] = counts["fclass"].map(FCLASS_LABELS)
    counts["status"] = counts["fclass"].apply(
        lambda x: "include" if x is not None else "exclude"
    )
    # Flag truly unmapped (not in dict at all)
    counts["in_map"] = counts["featuretype_str"].isin(FCLASS)
    counts.loc[~counts["in_map"] & counts["featuretype_str"].notna(), "status"] = "unmapped"

    out_csv = os.path.join(OUT_DIR, "featuretype_fclass.csv")
    counts[["featuretype", "count", "fclass", "fclass_label", "status"]].to_csv(
        out_csv, index=False
    )
    print(f"Written: {out_csv}")

    # ── Audit summary ─────────────────────────────────────────────────────────
    df["fclass"] = df["featuretype"].astype(str).map(FCLASS)
    df["ft_status"] = df["featuretype"].astype(str).apply(
        lambda x: "include" if FCLASS.get(x) is not None
        else ("exclude" if x in FCLASS else "unmapped")
    )

    lines = [
        f"Alcedo featuretype → WHG fclass audit",
        f"Source: {DATA_IN}",
        f"{'─' * 50}",
        f"Total rows:          {total:>7}",
        "",
        "── Row counts by disposition ───────────────────",
    ]
    for status, grp in df.groupby("ft_status"):
        lines.append(f"  {status:<10} {len(grp):>7}")

    lines += [
        "",
        "── Included rows by fclass ─────────────────────",
    ]
    included = df[df["ft_status"] == "include"]
    for fc, grp in included.groupby("fclass"):
        label = FCLASS_LABELS.get(fc, "")
        lines.append(f"  {fc}  {label:<22} {len(grp):>7}")

    unmapped = df[df["ft_status"] == "unmapped"]
    if len(unmapped):
        lines += [
            "",
            "── Unmapped featuretype values (need adding to FCLASS dict) ──",
        ]
        for ft, cnt in unmapped["featuretype"].value_counts().items():
            lines.append(f"  {ft:<35} {cnt:>6}")

    summary = "\n".join(lines)
    print("\n" + summary)

    out_txt = os.path.join(OUT_DIR, "audit_summary.txt")
    with open(out_txt, "w") as f:
        f.write(summary + "\n")
    print(f"\nWritten: {out_txt}")


if __name__ == "__main__":
    main()
