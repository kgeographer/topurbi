"""
make_alcedo_candidates.py

Builds alcedo_candidates — a staging table of all records viable for
LP-TSV upload, with columns named to match LP-TSV field names where
applicable, plus extra columns for review.

Inclusion criteria:
  - majortype IN (settlement, natural_feature, district, human_group, structure)
  - doublette = false
  - entrytype NOT IN (Term, Referral, Correction)
  - featuretype maps to an included fclass in featuretype_fclass

LP-TSV columns (named exactly):
  id, title, ccodes, fclasses, lat, lon, start, end,
  types, links, description, geowkt, approximation

Extra review columns:
  lemma, majortype, featuretype, aat_identifier, aat_label,
  conf_loc_verbal, conf_loc, nation, gazetteermatch, idno_resource,
  historical, doubtful, fantastical, geom
"""

import os, sys
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

# conf_loc_verbal → LP-TSV approximation value
APPROX_MAP = {
    "exact":                        None,
    "well_placed":                  None,
    "sufficient":                   "crm:P189_approximates",
    "automatic":                    "crm:P189_approximates",
    "zonal":                        "geo:sfWithin",
    "broad_area":                   "geo:sfWithin",
    "provincial dummy coordinates": "geo:sfWithin",
    "regional dummy coordinates":   "geo:sfWithin",
    "unlocated":                    "geo:sfWithin",
    "unspecified":                  "geo:sfWithin",
}

DDL = """
DROP TABLE IF EXISTS alcedo_candidates;
CREATE TABLE alcedo_candidates (

    -- LP-TSV fields (named exactly)
    id              TEXT PRIMARY KEY,
    title           TEXT,
    ccodes          TEXT,
    fclasses        TEXT,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    start           INTEGER,
    "end"           INTEGER,
    types           TEXT,           -- sourceLabel (verbatim featuretype)
    links           TEXT,           -- gn:/tgn: match URIs where available
    description     TEXT,           -- NULL pending first-sentence extractor
    geowkt          TEXT,           -- NULL for initial upload (points only)
    approximation   TEXT,           -- derived from conf_loc_verbal

    -- Review / audit columns
    lemma           TEXT,           -- original all-caps headword
    majortype       TEXT,
    featuretype     TEXT,
    aat_identifier  TEXT,           -- aat:XXXXXXX if WHG-supported
    aat_label       TEXT,           -- WHG term for that AAT concept
    conf_loc_verbal TEXT,
    conf_loc        DOUBLE PRECISION,
    nation          TEXT,
    gazetteermatch  TEXT,
    idno_resource   TEXT,
    historical      BOOLEAN,
    doubtful        BOOLEAN,
    fantastical     BOOLEAN,
    geom            GEOMETRY(Point, 4326)
);
"""


def build_links(row):
    """Convert gazetteermatch + source to LP-TSV links value (gn: or tgn: only)."""
    gm  = (row["gazetteermatch"] or "").strip()
    src = (row["idno_resource"]  or "").strip()
    if not gm or not src:
        return None
    if src.lower() == "geonames" and gm.isdigit():
        return f"gn:{gm}"
    if src.lower() in ("tgn", "getty-tgn") and gm.isdigit():
        return f"tgn:{gm}"
    # HGIS-Indias: alias not yet in LP-TSV schema — omit for now
    return None


def build_approx(row):
    clv = (row["conf_loc_verbal"] or "").strip()
    return APPROX_MAP.get(clv)


def main():
    conn = psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        row_factory=psycopg.rows.dict_row,
    )
    conn.autocommit = True

    print("Creating alcedo_candidates ...")
    conn.execute(DDL)

    rows = conn.execute("""
        SELECT
            ac.entry_id,
            ac.normname,
            ac.lemma,
            ac.ccodes,
            ff.fclass          AS fclasses,
            ac.lat,
            ac.lon,
            ac.featuretype,
            CASE
                WHEN wa.aat_id IS NOT NULL THEN 'aat:' || wa.aat_id::text
            END                AS aat_identifier,
            wa.term            AS aat_label,
            ac.conf_loc_verbal,
            ac.conf_loc,
            ac.majortype,
            ac.nation,
            ac.gazetteermatch,
            ac.idno_resource,
            ac.historical,
            ac.doubtful,
            ac.fantastical,
            ac.geom
        FROM alcedo_clean ac
        JOIN featuretype_fclass ff
            ON ac.featuretype = ff.featuretype AND ff.status = 'include'
        LEFT JOIN whg_aat_types wa
            ON ac.featuretype_aat::int = wa.aat_id
        WHERE ac.majortype IN (
                'settlement', 'natural_feature', 'district',
                'human_group', 'structure')
          AND ac.doublette = false
          AND ac.entrytype NOT IN ('Term', 'Referral', 'Correction')
    """).fetchall()

    print(f"Candidate rows fetched: {len(rows):,}")

    insert_sql = """
        INSERT INTO alcedo_candidates (
            id, title, ccodes, fclasses, lat, lon, start, "end",
            types, links, description, geowkt, approximation,
            lemma, majortype, featuretype, aat_identifier, aat_label,
            conf_loc_verbal, conf_loc, nation,
            gazetteermatch, idno_resource, historical, doubtful, fantastical,
            geom
        ) VALUES (
            %(entry_id)s, %(normname)s, %(ccodes)s, %(fclasses)s,
            %(lat)s, %(lon)s, 1786, 1789,
            %(featuretype)s, %(links)s, NULL, NULL, %(approximation)s,
            %(lemma)s, %(majortype)s, %(featuretype)s,
            %(aat_identifier)s, %(aat_label)s,
            %(conf_loc_verbal)s, %(conf_loc)s, %(nation)s,
            %(gazetteermatch)s, %(idno_resource)s,
            %(historical)s, %(doubtful)s, %(fantastical)s,
            %(geom)s
        )
    """

    with conn.cursor() as cur:
        cur.executemany(insert_sql, [
            {**row, "links": build_links(row), "approximation": build_approx(row)}
            for row in rows
        ])

    count = conn.execute("SELECT COUNT(*) FROM alcedo_candidates").fetchone()["count"]
    print(f"alcedo_candidates: {count:,} rows")

    print()
    print("fclasses breakdown:")
    for r in conn.execute(
        "SELECT fclasses, COUNT(*) FROM alcedo_candidates GROUP BY fclasses ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"  {r['fclasses']:>3}  {r['count']:>6,}")

    print()
    print("approximation breakdown:")
    for r in conn.execute(
        "SELECT approximation, COUNT(*) FROM alcedo_candidates GROUP BY approximation ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"  {str(r['approximation']):40}  {r['count']:>6,}")

    print()
    r = conn.execute("""
        SELECT
            COUNT(*) FILTER (WHERE links IS NOT NULL) AS has_links,
            COUNT(*) FILTER (WHERE links IS NULL)     AS no_links
        FROM alcedo_candidates
    """).fetchone()
    print(f"links coverage:  has: {r['has_links']:,}   no: {r['no_links']:,}")

    conn.close()


if __name__ == "__main__":
    main()
