"""
nation_ccode_audit.py

Derives WHG `ccodes` (ISO 3166-1 alpha-2) for each row in Alcedo_structured.csv.

Strategy:
  - Non-Spain Nation values map directly to a modern ISO code.
  - Nation=Spain entries use `prov-group` to derive one or more ccodes,
    since "Spain" in this dataset means former Spanish colonial territory
    across all of Latin America.

Multiple ccodes are semicolon-delimited per LP-TSV spec.

Outputs to whg/output/:
  nation_ccode_map.csv   — distinct (Nation, prov-group) combos with assigned ccodes
  nation_audit.txt       — summary counts
"""

import os
import pandas as pd

ROOT    = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_IN = os.path.join(ROOT, "UpdateDataWorkflow", "csv", "Alcedo_structured.csv")
OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))

# ── Direct Nation → ccode (non-Spain) ────────────────────────────────────────
# These are unambiguous modern-state assignments made by the TopUrbi team.
NATION_CCODE = {
    "USA":         "US",
    "Brasil":      "BR",
    "Britain":     "GB",
    "France":      "FR",
    "Netherlands": "NL",
    "Portugal":    "PT",
    "Denmark":     "DK",
    # No ccode derivable from Nation alone — fall through to prov-group lookup:
    "-":           None,
    "Ambiguous":   None,
    "unknown":     None,
}

# ── prov-group → ccode for non-Spain Nation values ───────────────────────────
# Ambiguous/unknown Nation entries where prov-group is still informative.
AMBIGUOUS_PROVGROUP_CCODE = {
    "Luisiana":        "US",
    "Canada":          "CA",
    "Caribe":          "CU;DO;HT;PR;JM",
    "Cayenne":         "GF",
    "Coahuila-Texas":  "MX;US",
    "Cumana":          "VE",
    "Florida":         "US",
    "Guayana":         "VE;GY;SR;GF",
    # Middleground / Subarctis / unknown: genuinely unresolvable
}

# ── prov-group → ccodes (Nation=Spain entries) ────────────────────────────────
# Colonial administrative groupings mapped to modern ISO codes.
# Semicolon-separated where a prov-group spans multiple modern states.
PROVGROUP_CCODE = {
    # Mexico and Central America
    "Mexico":                   "MX",
    "Nueva España":             "MX",
    "Puebla":                   "MX",
    "Oaxaca":                   "MX",
    "Michoacan":                "MX",
    "Nueva Galicia":            "MX",
    "Sinaloa-Sonora":           "MX",
    "Nueva Vizcaya":            "MX",
    "Chiapas":                  "MX",
    "Nuevo Leon-Santander":     "MX",
    "Chiloe":                   "CL",   # island province of Chile
    "Yucatan-Peten":            "MX;GT",
    "Coahuila-Texas":           "MX;US",
    "California":               "MX",   # Baja California; Alta = US but most entries are Baja
    "Nuevo Mexico":             "US;MX",
    "Nuevo México":             "US;MX",
    "Guatemala":                "GT",
    "Honduras":                 "HN",
    "Nicaragua-Costa Rica":     "NI;CR",
    "Luisiana":                 "US",
    "Florida":                  "US",
    "Georgia-Carolinas":        "US",

    # Caribbean
    "Caribe":                   "CU;DO;HT;PR;JM",
    "Santo Domingo":            "DO;HT",
    "Cuba":                     "CU",
    "Isla Margarita":           "VE",
    "British Caribbean":        "JM;BB;GD",
    "French Caribbean":         "MQ;GP",

    # Northern South America / Venezuela / Colombia
    "Venezuela":                "VE",
    "Cumana":                   "VE",
    "Maracaibo":                "VE",
    "Guayana":                  "VE;GY;SR;GF",
    "Llanos":                   "CO;VE",
    "Nuevo Reyno de Granada":   "CO",
    "Nuevo Reino de Granada":   "CO",
    "Cartagena":                "CO",
    "Santa Marta":              "CO",
    "Popayan":                  "CO",
    "Antioquia":                "CO",
    "Neiva":                    "CO",
    "Mariquita":                "CO",
    "Tunja":                    "CO",
    "Choco":                    "CO",
    "Tierra Firme":             "PA;CO",
    "Surinam":                  "SR",

    # Ecuador / Peru / Bolivia
    "Quito":                    "EC",
    "Maynas":                   "PE;EC",
    "Ocopa":                    "PE",
    "Peru norte":               "PE",
    "Peru sur":                 "PE",
    "Collao":                   "PE;BO",
    "Charcas":                  "BO",
    "Santa Cruz de la Sierra":  "BO",

    # Southern cone
    "Chile":                    "CL",
    "Araucanos":                "CL;AR",
    "Cuyo":                     "AR;CL",
    "Tucuman":                  "AR",
    "Rio de la Plata":          "AR;UY",
    "Patagonia":                "AR;CL",
    "Chaco":                    "AR;BO;PY",
    "Paraguay":                 "PY",

    # Ambiguous / unresolvable
    "Middleground":             None,
    "-":                        None,
    "unknown":                  None,
}


def get_ccode(row):
    nation = str(row.get("Nation", "")).strip()
    provgroup = str(row.get("prov-group", "")).strip()
    if nation == "Spain":
        return PROVGROUP_CCODE.get(provgroup)
    direct = NATION_CCODE.get(nation)
    if direct is not None:
        return direct
    # Nation is "-", "Ambiguous", or "unknown" — try prov-group
    return AMBIGUOUS_PROVGROUP_CCODE.get(provgroup)


def main():
    df = pd.read_csv(DATA_IN, sep="|", low_memory=False)
    total = len(df)

    df["ccode"] = df.apply(get_ccode, axis=1)

    # ── Build combo summary table ─────────────────────────────────────────────
    combos = (
        df.groupby(["Nation", "prov-group", "ccode"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["Nation", "count"], ascending=[True, False])
    )
    out_csv = os.path.join(OUT_DIR, "nation_ccode_map.csv")
    combos.to_csv(out_csv, index=False)
    print(f"Written: {out_csv}")

    # ── Audit summary ─────────────────────────────────────────────────────────
    resolved   = df["ccode"].notna().sum()
    unresolved = df["ccode"].isna().sum()

    lines = [
        "Alcedo Nation / prov-group → WHG ccode audit",
        f"Source: {DATA_IN}",
        f"{'─' * 50}",
        f"Total rows:              {total:>7}",
        f"  ccode resolved:        {resolved:>7}",
        f"  ccode unresolved:      {unresolved:>7}",
        "",
        "── Resolved by ccode ───────────────────────────",
    ]
    for ccode, grp in df[df["ccode"].notna()].groupby("ccode"):
        lines.append(f"  {ccode:<15} {len(grp):>7}")

    unres = df[df["ccode"].isna()]
    if len(unres):
        lines += [
            "",
            "── Unresolved (Nation / prov-group combos) ─────",
        ]
        for (nat, pg), grp in unres.groupby(["Nation", "prov-group"], dropna=False):
            lines.append(f"  {str(nat):<15} {str(pg):<30} {len(grp):>6}")

    summary = "\n".join(lines)
    print("\n" + summary)

    out_txt = os.path.join(OUT_DIR, "nation_audit.txt")
    with open(out_txt, "w") as f:
        f.write(summary + "\n")
    print(f"\nWritten: {out_txt}")


if __name__ == "__main__":
    main()
