# Alcedo → WHG Ingest Pipeline

Documents the steps taken to transform the Alcedo structured data into
a set of records ready for upload to World Historical Gazetteer (WHG)
as an LP-TSV dataset.

All scripts are in `whg/scripts/`. All intermediate tables live in the
`topurbi` PostgreSQL database (localhost:5435).

---

## Source data

**`UpdateDataWorkflow/csv/Alcedo_structured.csv`**
Pipe-delimited export of the TopUrbi working database. 19,305 rows,
66 columns. Each row is one entry from Alcedo's *Diccionario geográfico-
histórico de las Indias Occidentales* (1786–1789), structured by Werner
Stangl's team. Columns cover identity, geography, location quality,
editorial flags, TEI references, and population placeholders.

---

## Step 1 — Load pristine source (`alcedo_og`)

**Script:** `load_alcedo_og.py`
**Result:** table `alcedo_og`, 19,305 rows

- Reads CSV with pandas; normalises column names to lowercase with
  underscores (e.g. `dot-on-map` → `dot_on_map`).
- Declares explicit PostgreSQL types (BOOLEAN, INTEGER, DOUBLE PRECISION,
  TEXT) for all 66 columns.
- Bulk-loads via psycopg COPY.
- `alcedo_og` is the pristine reference and is never modified.

---

## Step 2 — Normalise to `alcedo_clean`

**Script:** `make_alcedo_clean.py`
**Result:** table `alcedo_clean`, 19,305 rows

Applies the following normalizations (all verified against the raw data
before inclusion):

| Column | Change |
|--------|--------|
| `district`, `alcedo_province`, `alcedo_region`, `observation` | TRIM whitespace |
| `conf_loc_verbal` | `'Sufficient'` → `'sufficient'`; `'auto'` → `'automatic'` |
| `majortype` | `'Referral'` → `'referral'` (aligns with other lowercase values) |
| `resolutionstage` | `'manual_qgis'` → `'manual-qgis'` (hyphen is dominant form) |

`alcedo_og` is the SELECT source; `alcedo_clean` is a new table.

### 2a — Add geometry column

A PostGIS `GEOMETRY(Point, 4326)` column `geom` was added to `alcedo_clean`,
generated from the existing `lon`/`lat` columns via `ST_SetSRID(ST_MakePoint(...))`.
Rows with NULL coordinates receive NULL geometry (~10,000 unlocated entries).

### 2b — Add `ccodes` column

`ccodes` (ISO 3166-1 alpha-2 modern country codes, semicolon-delimited for
records spanning multiple countries) is a near-required field in WHG LP-TSV:
it acts as a spatial constraint during reconciliation, critical for Spanish
America where place names repeat across the continent.

Populated via spatial lookup against the `admin0` world country polygon table
(column `iso_a2`):

1. **Primary:** `ST_Within(alcedo_clean.geom, admin0.geom)` — point falls
   inside a country polygon.
2. **Fallback:** `ST_DWithin` with a 10 km buffer (geography cast) for points
   near borders or coast that fall just outside a polygon.
3. Records with dummy or NULL coordinates that still lack a ccode (~724)
   remain NULL pending manual review.

Note: `ccodes` reflects modern geography, not 18th-century colonial power.
A point in what is now Mexico gets `MX` regardless of whether Alcedo
attributed it to 'España' or 'Nueva España'.

---

## Step 3 — Reference tables

### `featuretype_fclass`

Maps Alcedo's 190+ `featuretype` vocabulary to GeoNames single-letter
feature class codes (A/H/L/P/R/S/T), which are required by WHG LP-TSV
as `fclasses`.

- Initial mapping produced by `featuretype_audit.py`, which surveyed all
  distinct featuretype values and assigned fclasses based on semantic
  interpretation.
- Extended interactively: ambiguous or missing types reviewed against
  entry `content` text to confirm the correct class.
- Final status values: `include` (mapped fclass) or `exclude` (vocabulary/
  metadata terms with no geographic referent).

Key decisions:
- All named water features (H) and landforms (T) are included — they
  represent genuine gazetteer records valuable to WHG.
- Human groups / named societies (L) are included; confirmed against
  D-PLACE dataset handling in WHG (`aat:300387171`, "cultural group").
- `Mote`, `Term`, `Referral`, `Correction`, `Elipse`, botanical/zoological
  types excluded.
- `Cabeza` → T (headland, not capital); `Caida` → H (river drop, not
  landform); `Pedazo`/`Parte` → L (coastal/island sections as regions);
  `Pasage` → H (water passage, confirmed from entry content).

### `whg_aat_types`

**Script:** `load_whg_aat.py`

WHG's supported subset of 176 Getty AAT concepts for feature types, loaded
from `whg/data/feature-types-AAT_20230609.tsv`. Used to populate the
`aat_identifier` field in `alcedo_candidates` where Alcedo's `featuretype_aat`
value matches a WHG-supported AAT ID. Coverage: ~97% of non-duplicate
Toponym records have a supported AAT value.

### `admin0`

World country polygons with `iso_a2` codes, added externally. Used only
for the `ccodes` spatial lookup in Step 2b.

---

## Step 4 — Build candidate set (`alcedo_candidates`)

**Script:** `make_alcedo_candidates.py`
**Result:** table `alcedo_candidates`, 17,467 rows

### Inclusion filter

| Criterion | Effect |
|-----------|--------|
| `majortype IN (settlement, natural_feature, district, human_group, structure)` | Excludes editorial entry types |
| `doublette = false` | Excludes ~1,270 duplicate entries flagged by Stangl |
| `entrytype NOT IN ('Term', 'Referral', 'Correction')` | Excludes non-geographic entries |
| `featuretype_fclass.status = 'include'` | Excludes featuretypes with no geographic referent |

Of 19,305 source rows, 17,467 (90.5%) pass all criteria.

### fclasses distribution

| fclass | Count | GeoNames category |
|--------|------:|-------------------|
| P | 9,406 | Populated places |
| H | 4,546 | Hydrographic features |
| T | 2,181 | Mountains, hills, landforms |
| A | 661 | Administrative divisions |
| L | 511 | Parks, areas, regions (incl. human groups) |
| S | 160 | Spots, buildings, farms |
| R | 2 | Roads, railroads |

### LP-TSV columns populated

| Column | Source | Notes |
|--------|--------|-------|
| `id` | `entry_id` | Alcedo's own record identifier |
| `title` | `normname` | Mixed-case normalised name with diacritics |
| `ccodes` | `ccodes` | From spatial lookup (Step 2b) |
| `fclasses` | `featuretype_fclass` | Mapped GeoNames feature class |
| `lat`, `lon` | `lat`, `lon` | As assigned by Stangl's geocoding |
| `start`, `end` | — | Fixed: 1786 / 1789 (Alcedo's writing period) |
| `types` | `featuretype` | Verbatim Alcedo term (sourceLabel in LP-TSV) |
| `links` | `gazetteermatch` | `gn:` or `tgn:` where source is GeoNames/TGN (181 records); HGIS-Indias matches omitted pending resolution of `indias:` alias issue in WHG LP-TSV schema |
| `approximation` | `conf_loc_verbal` | `geo:sfWithin` for dummy/zonal/broad coordinates; `crm:P189_approximates` for sufficient/automatic; NULL for well-placed/exact |
| `description` | — | NULL — pending first-sentence extractor from `content` |
| `geowkt` | — | NULL — points only for initial upload |

### Review columns retained

`lemma` (original all-caps headword), `majortype`, `featuretype`,
`aat_identifier`, `aat_label`, `conf_loc_verbal`, `conf_loc`, `nation`,
`gazetteermatch`, `idno_resource`, `historical`, `doubtful`, `fantastical`,
`geom` (PostGIS point for visualisation).

---

## Open issues before LP-TSV export

1. **`indias:` alias** — not in LP-TSV validation schema; ~348 distrito and
   ~7,218 lugar HGIS-Indias matches cannot yet be expressed as `links` values.
   GitHub issue filed; awaiting response from Stephen Gadd (WHG).
2. **~724 records with no `ccodes`** — points with dummy or NULL coordinates
   that fall outside any admin0 polygon even with 10 km buffer. Require
   per-record review or acceptance of NULL.
3. **`description` field** — NULL throughout. A first-sentence extractor
   from the `content` column would populate this usefully.
4. **A-class territorio polygons** — the 348 Alcedo district entries with
   HGIS-Indias territorio matches could carry polygon geometry (`geowkt`).
   Decision deferred: polygon geometry derives from Werner Stangl's separate
   Indias work, not from Alcedo itself; attaching it to the Alcedo upload
   would misrepresent provenance. WHG reconciliation will link these records
   to the existing Indias territorios after upload.
