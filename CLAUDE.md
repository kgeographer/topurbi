# CLAUDE.md — TopUrbi / Alcedo → WHG

## What this repo is

A clone of [TopUrbi](https://github.com/topurbi) — the digitization project for Antonio de Alcedo's
*Diccionario geográfico-histórico de las Indias Occidentales ó América* (1786–1789), 19,305 entries
covering place names across Spanish colonial America. Digitization was led by Werner Stangl under a
French research institute; Carmen Brando is the institutional "keeper" of the data (CC-by licensed).

Karl Grossner (this user) built [World Historical Gazetteer (WHG)](https://whgazetteer.org) over
seven years and is now facilitating the accession of Alcedo into WHG. The original repo files are
untouched; all of Karl's work lives in the `whg/` folder.

**Karl's GitHub repo** (his work only, no TopUrbi source files):
https://github.com/kgeographer/topurbi
- Local remote name: `github`
- Push new work: `git push github lptsv:main`

**License:** CC BY-NC 4.0. The NC restriction needs to be confirmed as compatible with WHG.
ANR requires citation at record level: "ANR TopUrbi — Topographie de l'urbanisation impériale
hispanique (Projet-ANR-21-CE27-0023)".

**Data currency warning:** This GitHub clone is OUTDATED per Carmen Brando (email 23 March 2026).
Authoritative current data lives in HumaNum GitLab:
- Main repo: https://gitlab.huma-num.fr/plateforme-geomatique-et-hn/topurbi-project
- TEI gazetteer index: https://gitlab.huma-num.fr/plateforme-geomatique-et-hn/topurbi-data/-/tree/main/auxiliary
Verify whether this supersedes `alcedo_og` before producing a final LP-TSV export.

---

## Key contacts

| Person | Role |
|--------|------|
| Karl Grossner | This user; WHG founder, Alcedo liaison |
| Stephen Gadd | WHG dev contractor, U Pittsburgh / ISHI |
| Ruth Mostern | ISHI director, U Pittsburgh; WHG institutional owner |
| Palak (surname TBD) | WHG acquisition coordinator (copied on email) |
| Werner Stangl | Alcedo digitizer; completed 2-yr contract, now departed |
| Carmen Brando | French institutional keeper of TopUrbi / ANR TopUrbi project |
| Jean-Paul Zuñiga | TopUrbi PI (ANR project) |
| Gimena del Rio Riande | Separate Alcedo effort (from English translation) — potential coordination |

---

## Database

PostgreSQL at `localhost:5435`, database `topurbi`. Credentials in `.env`.

| Table | Rows | Description |
|-------|------|-------------|
| `alcedo_og` | 19,305 | Pristine source load — never modified |
| `alcedo_clean` | 19,305 | Normalized + PostGIS `geom` + `ccodes` columns added |
| `featuretype_fclass` | ~190 | Alcedo featuretype → GeoNames fclass (A/H/L/P/R/S/T) |
| `whg_aat_types` | 176 | WHG's supported Getty AAT concept subset |
| `admin0` | — | World country polygons with `iso_a2` codes (external load) |
| `alcedo_candidates` | 17,467 | LP-TSV-ready candidate set (see pipeline) |

---

## Source data

`UpdateDataWorkflow/csv/Alcedo_structured.csv` — pipe-delimited, 19,305 rows, 66 columns.
Also present: AGOL exports by majortype, `Alcedo_geo.csv`, meta tables.

---

## Pipeline (whg/docs/pipeline.md for detail)

| Step | Script | Output |
|------|--------|--------|
| 1 | `load_alcedo_og.py` | `alcedo_og` — pristine load |
| 2 | `make_alcedo_clean.py` | `alcedo_clean` — normalized + geom + ccodes |
| 3a | `featuretype_audit.py` | `featuretype_fclass` — type→fclass mapping |
| 3b | `load_whg_aat.py` | `whg_aat_types` — WHG AAT subset |
| 3c | `load_hgis_territorio_geoms.py` | territorio polygon geometries (reference) |
| 4 | `make_alcedo_candidates.py` | `alcedo_candidates` — 17,467 LP-TSV-ready rows |
| 5 | **(TODO)** export script | `whg/data/alcedo_lptsv.tsv` |

Steps 1–4 are complete. Step 5 is the immediate next task.

---

## LP-TSV field status in `alcedo_candidates`

| Field | Status |
|-------|--------|
| `id` | ✓ from `entry_id` |
| `title` | ✓ from `normname` |
| `ccodes` | ✓ for ~16,743; ~724 NULL (dummy/unlocated, no admin0 match) |
| `fclasses` | ✓ mapped from `featuretype_fclass` |
| `lat`, `lon` | ✓ (~10k are dummy/NULL coords for unlocated entries) |
| `start`, `end` | ✓ fixed 1786/1789 |
| `types` | ✓ verbatim Alcedo `featuretype` as sourceLabel |
| `links` | Partial: 181 gn:/tgn: links; ~7,566 HGIS-Indias links BLOCKED (see issues) |
| `approximation` | ✓ derived from `conf_loc_verbal` |
| `description` | NULL — needs first-sentence extractor from `content` |
| `geowkt` | NULL — polygon geometry deferred |

---

## Open issues (before LP-TSV export)

1. **`indias:` alias** — not in LP-TSV validation schema (`schema_lptsv_v0.4.json`). Affects ~348
   distrito + ~7,218 lugar records with HGIS-Indias matches. Need to raise with Stephen Gadd:
   add `indias:` to schema, or confirm full-URL workaround.
2. **~724 records with no `ccodes`** — fall outside admin0 polygons even with 10 km buffer.
   Accept NULL or do per-record manual lookup.
3. **`description` field NULL** — a first-sentence extractor from `content` column would help.
4. **Territory polygon geometry** — 348 Alcedo district entries match HGIS-Indias territorios
   with polygon geometry; deferred (provenance concern — geometry comes from Stangl's Indias
   work, not Alcedo itself).

---

## Immediate next steps

1. Write LP-TSV export script (`whg/scripts/export_lptsv.py` → `whg/data/alcedo_lptsv.tsv`)
2. Validate against WHG's `schema_lptsv_v0.4.json` format checker
3. Send Stephen Gadd the data + context; discuss `indias:` alias and his new pipeline approach
4. Decide on `ccodes` NULLs and `description` strategy before or after initial send

---

## WHG LP-TSV format notes

- Schema: `schema_lptsv_v0.4.json`; validator script TBD (ask Stephen)
- Recognized `links` prefixes: `bnf|cerl|dbp|gn|gnd|gov|loc|pl|tgn|viaf|wd|wp`
- `ccodes` is near-required — acts as spatial constraint during reconciliation
- `approximation` values: `geo:sfWithin` (zonal/dummy), `crm:P189_approximates` (sufficient),
  NULL (well-placed/exact)
- `start`/`end`: integer years; fixed at 1786/1789 for all Alcedo records

---

## LLM-assisted geocoding (longer term)

~10,000 unlocated/dummy entries could be partially geocoded by:
1. LLM extracts anchor place name + bearing + distance from `content` text
2. Resolve anchor against located entries in `alcedo_clean` (conf_loc ≤ 3)
3. Triangulate candidate point; query WHG API / GeoNames centred on it
4. Write scored candidates to a review table for human triage

Highest-yield entries: those with `has_loc_info` in (distancia, direccion, situado, curso, nacimiento).

---

## Branch

Current work: `lptsv` branch.
