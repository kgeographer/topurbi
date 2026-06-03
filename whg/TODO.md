# WHG Ingest — TODO

Tasks in rough priority order. Scope depends on available time/funding.

---

## Immediate / in progress

- [ ] Decide on empty columns — drop `alcedo_location_qual`, `alcedo_name_qual`, `majortype_literal`, `pop_*` from transform, or carry as nulls
- [ ] Build `alcedo_transform` table: apply fclass and ccode mappings, filter excluded rows (doublette, Referral, Term, Correction), add derived columns ready for LP-TSV export
- [ ] Write LP-TSV export script → `whg/data/alcedo_lptsv.tsv`
- [ ] Validate LP-TSV against WHG's format checker before upload

---

## Data quality / enrichment

- [ ] Resolve the ~60 geographic entries still missing ccodes (Polynesia, Middleground, etc.) — per-record lookup
- [ ] First-sentence extractor for `description` field (from `content`)
- [ ] Map `gazetteermatch` IDs to proper URIs for `matches` field: `gn:{id}` for GeoNames (177), `tgn:{id}` for Getty-TGN (4); investigate whether HGIS-Indias has dereferenceable URIs
- [ ] **ISSUE — `indias:` alias not in LP-TSV validation schema** (`schema_lptsv_v0.4.json` allows only `bnf|cerl|dbp|gn|gnd|gov|loc|pl|tgn|viaf|wd|wp`). Alias is defined in `aliases.js` but omission likely means full URL in `matches` would not trigger automatch during reconciliation. Check `place_related.jsonb` in whgv3beta to confirm how stored match URIs drive automatch, then raise with Stephen Gadd: either add `indias:` to schema, or confirm full-URL workaround. This affects ~348 distrito and ~7,218 lugar matches from HGIS-Indias.
- [ ] Consider whether `historical`, `doubtful`, `fantastical` flags should surface in `description` or a dedicated note field

---

## Unlocated place geocoding (LLM-assisted)

A pipeline to generate candidate coordinates for the ~10,000 unlocated/dummy entries:

1. **Parse spatial language** — LLM extracts anchor place names, bearing, and distance from `content` text; highest-yield entries are those with `has_loc_info` in (`distancia`, `direccion`, `situado`, `curso`, `nacimiento`)
2. **Resolve anchors** — match extracted anchor names against located entries in `alcedo_clean` (conf_loc ≤ 3) to get real coordinates
3. **Triangulate candidate point** — bearing + distance (legua → km conversion, ~4.2 km, region-dependent) from anchor(s)
4. **Spatial name search** — query WHG API and/or GeoNames centred on candidate point + radius; rank results by name similarity × proximity
5. **Review table** — write candidates with confidence scores to a new DB table for human triage
6. **Back-door option** — if `indias:` alias added to WHG (request to Stephen Gadd), the 7,218 HGIS-Indias matches could be used for automated reconciliation

Key improvement over prior GeoNames work: spatial language parsing provides a coordinate *before* name search, making the proximity filter far more discriminating.

---

## Longer term / funding-dependent

- [ ] Full LP-TSV upload to WHG and reconciliation review
- [ ] AAT type mapping — map Alcedo featuretype vocabulary to WHG's 176-concept AAT subset (desirable but not required for initial ingest)
- [ ] Population data — `pop_*` fields are empty; Alcedo mentions population figures in text; LLM extraction could populate these
- [ ] TEI full-text — obtain the annotated volume files (`Alcedo_vol1-5.xml`) from Werner Stangl; these would enable richer NER-based extraction and a more complete digital edition integration
- [ ] Explore broader LLM uses against `content`: entity extraction, relationship mapping, automated translation of entries for English-language access
