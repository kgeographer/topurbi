"""
load_hgis_territorio_geoms.py

For the 348 Alcedo district entries that have HGIS-Indias territorio matches,
fetches the polygon geometry from the local whgv3beta snapshot and stores it
in topurbi for use as geowkt in LP-TSV export.

src_id is replicated on place_geom with a 1-to-1 correspondence to places.id,
so we can query place_geom directly by src_id without joining through places.

Geometry selection logic (per src_id):
  1. Prefer the place_geom whose timespan covers Alcedo's writing period
     (start ≤ 1789 AND end ≥ 1786).
  2. If multiple qualify, take the one with the latest start year.
  3. If none qualify, fall back to the geom with smallest temporal
     distance from the window [1786, 1789].

Cross-database: reads from whgv3beta, writes to topurbi.
"""

import os, sys
import psycopg
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

ALCEDO_START = 1786
ALCEDO_END   = 1789

DDL = """
DROP TABLE IF EXISTS hgis_territorio_geoms;
CREATE TABLE hgis_territorio_geoms (
    entry_id    TEXT PRIMARY KEY,
    src_id      TEXT NOT NULL,
    geom_start  INTEGER,
    geom_end    INTEGER,
    geom_wkt    TEXT
);
"""


def db_conn(dbname):
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=dbname,
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )


def temporal_distance(start, end):
    """Distance from [start, end] to [1786, 1789]. Returns 0 if overlapping."""
    if start is None or end is None:
        return 9999
    if start <= ALCEDO_END and end >= ALCEDO_START:
        return 0
    return min(abs(start - ALCEDO_END), abs(end - ALCEDO_START))


def best_geom(rows):
    """rows: list of (geom_start, geom_end, wkt). Returns best-matching row."""
    overlapping = [
        (s, e, w) for s, e, w in rows
        if s is not None and e is not None
        and s <= ALCEDO_END and e >= ALCEDO_START
    ]
    if overlapping:
        return max(overlapping, key=lambda r: r[0])  # latest start wins
    return min(rows, key=lambda r: temporal_distance(r[0], r[1]))


def main():
    whg = db_conn("whgv3beta")
    top = db_conn("topurbi")
    top.autocommit = True

    # ── Fetch Alcedo territorio entries ──────────────────────────────────────
    alcedo_rows = top.execute("""
        SELECT entry_id, gazetteermatch
        FROM alcedo_clean
        WHERE idno_resource = 'HGIS-Indias'
          AND majortype = 'district'
          AND gazetteermatch ~ '^[A-Z]'
    """).fetchall()

    src_id_to_entry = {row[1]: row[0] for row in alcedo_rows}
    print(f"Alcedo territorio entries: {len(src_id_to_entry)}")

    # ── Fetch all matching place_geom rows from whgv3beta ───────────────────
    whg_rows = whg.execute(
        """
        SELECT
            src_id,
            (jsonb->'when'->'timespans'->0->'start'->>'in')::int AS geom_start,
            (jsonb->'when'->'timespans'->0->'end'->>'in')::int   AS geom_end,
            ST_AsText(geom)                                        AS wkt
        FROM place_geom
        WHERE src_id = ANY(%s)
          AND geom IS NOT NULL
        """,
        (list(src_id_to_entry.keys()),),
    ).fetchall()

    print(f"place_geom rows fetched from whgv3beta: {len(whg_rows)}")

    # Group by src_id
    grouped: dict[str, list] = {}
    for src_id, g_start, g_end, wkt in whg_rows:
        grouped.setdefault(src_id, []).append((g_start, g_end, wkt))

    # ── Create output table ──────────────────────────────────────────────────
    top.execute(DDL)

    inserted = 0
    no_geom  = []
    for src_id, entry_id in src_id_to_entry.items():
        if src_id not in grouped:
            no_geom.append((entry_id, src_id))
            continue

        g_start, g_end, wkt = best_geom(grouped[src_id])
        top.execute(
            """
            INSERT INTO hgis_territorio_geoms
                (entry_id, src_id, geom_start, geom_end, geom_wkt)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (entry_id, src_id, g_start, g_end, wkt),
        )
        inserted += 1

    print(f"Inserted: {inserted}")
    if no_geom:
        print(f"No geometry found for {len(no_geom)} src_ids:")
        for eid, sid in no_geom:
            print(f"  {eid}  {sid}")

    # ── Temporal selection summary ────────────────────────────────────────────
    stats = top.execute("""
        SELECT
            COUNT(*) FILTER (WHERE geom_start <= 1789 AND geom_end >= 1786) AS overlap,
            COUNT(*) FILTER (WHERE geom_start > 1789 OR geom_end < 1786)    AS fallback,
            COUNT(*) FILTER (WHERE geom_start IS NULL)                       AS no_when
        FROM hgis_territorio_geoms
    """).fetchone()
    print(f"Temporal selection — overlap: {stats[0]}, fallback: {stats[1]}, no_when: {stats[2]}")

    whg.close()
    top.close()


if __name__ == "__main__":
    main()
