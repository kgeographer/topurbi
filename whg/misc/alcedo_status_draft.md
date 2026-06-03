# Alcedo dataset — status for WHG accession
*Draft for Karl to send to Stephen Gadd and Palak Vashist*

---

Hi Stephen and Palak,

Following up on our June exchange — I've done a thorough pass on the Alcedo data and want to give
you a clear picture of what I have and where the open questions are, so we can decide on the best
pathway.

## The dataset

Antonio de Alcedo's *Diccionario geográfico-histórico de las Indias Occidentales ó América*
(1786–1789), digitized by Werner Stangl under the French ANR TopUrbi project (PI Jean-Paul Zúñiga;
Carmen Brando, technical lead). The source is Werner's TEI digital edition (5 volumes), now
complete. The data carries a **CC BY-NC 4.0** licence, with ANR requiring attribution at the record
level: *"ANR TopUrbi — Topographie de l'urbanisation impériale hispanique
(Projet-ANR-21-CE27-0023)"*. I want to flag the NC clause upfront — I assume it's compatible with
WHG's terms but worth confirming with Carmen.

## What I've prepared

Starting from the TEI-encoded volumes and Werner's structured CSV, I've built a pipeline that
produces a Postgres table (`alcedo_candidates`) with LP-TSV column names and 17,467 rows ready for
export. Here's the field-by-field picture:

| LP-TSV field | Status | Notes |
|---|---|---|
| `id` | ✓ 17,467 | Alcedo `entry_id` (e.g. `id_00005`) |
| `title` | ✓ 17,467 | Normalized name with diacritics |
| `fclasses` | ✓ 17,467 | Mapped from Alcedo's 190-term featuretype vocabulary |
| `types` | ✓ 17,467 | Verbatim Alcedo featuretype as `sourceLabel` |
| `aat_identifier` | ✓ 16,942 (97%) | WHG-supported Getty AAT IDs |
| `start` / `end` | ✓ all | Fixed 1786 / 1789 |
| `ccodes` | ✓ 16,743 · ✗ 724 | Spatial lookup against admin0 polygons; 724 unlocated entries fall outside all polygons even with 10 km buffer |
| `approximation` | ✓ all | Derived from Werner's location confidence field |
| `description` | ✓ 17,466 | Full Spanish entry text extracted from TEI `<sense>` elements |
| `links` | Partial — see below | |
| `geowkt` | ✗ | Deferred; point coordinates only for initial upload |

### fclasses distribution

| fclass | n | GeoNames category |
|---|---|---|
| P | 9,406 | Populated places |
| H | 4,546 | Hydrographic features |
| T | 2,181 | Landforms |
| A | 661 | Administrative divisions |
| L | 511 | Regions, human groups |
| S | 160 | Structures |
| R | 2 | Routes |

### Location confidence

Of the 17,467 candidates, **8,687 are reasonably located** (well-placed, sufficient, or
automatically geocoded). The remaining **8,780 carry dummy or provincial centroid coordinates** —
Werner's team placed these at a province centroid when the specific location was unknown.
All unlocated records have an `approximation` value of `geo:sfWithin` in the LP-TSV to flag this.

## The links question — and why it matters

This is where I need your input, Stephen.

The dataset has external match IDs for **7,218 records** sourced from Werner's *HGIS de las
Indias* — which, as you know, is already in WHG and has been reconciled. These are:

- **6,863 numeric IDs** → lugares (settlements, structures, natural features)
- **355 alphanumeric IDs** → territorios (administrative districts)

Those 6,688 that are in my candidate set represent direct bridges from Alcedo records to
already-reconciled WHG entries, and by extension to their Wikidata and GeoNames links — a
significant semi-automatic reconciliation win. They are expressed as `indias:` aliases in the
LP-TSV `links` field. The other 181 records have GeoNames (177) or Getty-TGN (4) matches.

## The description field

Werner produced TEI-annotated transcriptions of all five volumes. I've extracted the plain Spanish
entry text for all 17,467 candidates — average 294 characters, ranging from a single sentence
("Pueblo de la Isla de Cuba.") to full historical essays for major entries like *Peru* (~54k chars).
This is the same layer your GoW pipeline extracts from OCR; here it comes pre-structured and
TEI-encoded.

If WHG's `description` field has a length preference, I can truncate to first sentence or a char
limit at export time without losing anything — full text is stored in the DB.

## GoW pipeline relevance

I've been following the Gazetteer of the World work with great interest. Alcedo is structurally
the same class of source — an 18th-century descriptive gazetteer of a specific world region — but
arrives pre-processed: structured, geocoded (partially), TEI-annotated, and linked to HGIS. It
could be a useful test case or validation set for the OCR/LLM pipeline, and/or a candidate for
the same standalone-app treatment you've given GoW. I'm not pushing any particular pathway — 
I'd rather understand what would be most useful to you and the ISHI team and fit accordingly.

## Open questions for you

1. **CC BY-NC 4.0 compatibility** — is this a problem for WHG?
2. **Record-level attribution** — can the ANR citation string be carried as a dataset-level note,
   or does it need to appear on each record?
3. **Description length** — I've truncated to ~500 chars (sentence boundary) for the sample;
   happy to adjust or send full text if you prefer.
4. **Pathway** — LP-TSV ingest into main WHG, GoW-style standalone treatment, or both?
   I have a 500-record sample LP-TSV ready to upload whenever you say go.

Happy to jump on a call, share the data directly, or answer any questions here.

Cheers,
Karl

---
*Data prepared from: TopUrbi GitLab (gitlab.huma-num.fr/plateforme-geomatique-et-hn/topurbi-project),
TEI volumes in topurbi-data repo. Pipeline scripts in the whg/ folder of a local working clone.*
