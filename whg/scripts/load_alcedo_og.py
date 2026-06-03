"""
load_alcedo_og.py

Creates and populates the alcedo_og table in the topurbi database.

alcedo_og is the pristine source — exact structure of Alcedo_structured.csv.
All transforms and derived datasets write to separate, aptly-named tables.

Column names with hyphens (dot-on-map, prov-group) are normalised to
underscores (dot_on_map, prov_group) for SQL compatibility; all values
are otherwise unchanged.
"""

import os
import sys
import io
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from db_utils import db_connect

DATA_IN = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..",
                 "UpdateDataWorkflow", "csv", "Alcedo_structured.csv")
)

# ── Column type mapping ───────────────────────────────────────────────────────
# Pandas infers most types correctly; we declare the PostgreSQL DDL explicitly.

BOOL_COLS  = {"subentry", "doublette", "historical", "doubtful", "fantastical",
              "dot_on_map", "falsematch", "bad_category", "relative_province"}
INT_COLS   = {"auto", "random", "volume"}
FLOAT_COLS = {"featuretype_aat", "lat", "lon", "conf_loc",
              "alcedo_location_qual", "alcedo_name_qual",
              "featuretype_literal_aat", "majortype_literal",
              "pop_number", "pop_year", "pop_unit", "pop_source"}

def pg_type(col: str) -> str:
    c = col.lower()
    if c in BOOL_COLS:   return "BOOLEAN"
    if c in INT_COLS:    return "INTEGER"
    if c in FLOAT_COLS:  return "DOUBLE PRECISION"
    return "TEXT"


DDL_CREATE = """
DROP TABLE IF EXISTS alcedo_og;
CREATE TABLE alcedo_og (
    entry_id                TEXT,
    lemma                   TEXT,
    normname                TEXT,
    corresp_entry           TEXT,
    subentry                BOOLEAN,
    doublette               BOOLEAN,
    historical              BOOLEAN,
    doubtful                BOOLEAN,
    fantastical             BOOLEAN,
    dot_on_map              BOOLEAN,
    special_info            TEXT,
    entrytype               TEXT,
    majortype               TEXT,
    featuretype             TEXT,
    featuretype_aat         DOUBLE PRECISION,
    nation                  TEXT,
    region                  TEXT,
    prov_group              TEXT,
    province                TEXT,
    district                TEXT,
    partido                 TEXT,
    historical_alc          TEXT,
    fantastical_alc         TEXT,
    nation_alc              TEXT,
    resolutionstage         TEXT,
    falsematch              BOOLEAN,
    gazetteermatch          TEXT,
    conf_identity           TEXT,
    lat                     DOUBLE PRECISION,
    lon                     DOUBLE PRECISION,
    conf_loc                DOUBLE PRECISION,
    observation             TEXT,
    source                  TEXT,
    alcedo_location_qual    DOUBLE PRECISION,
    alcedo_name_qual        DOUBLE PRECISION,
    alcedo_identity_qual    TEXT,
    alcedo_featuretype_qual TEXT,
    alcedo_province_qual    TEXT,
    relative_province       BOOLEAN,
    has_loc_info            TEXT,
    reviewer                TEXT,
    review_method           TEXT,
    auto                    INTEGER,
    nombre_estandar         TEXT,
    random                  INTEGER,
    bad_category            BOOLEAN,
    featuretype_literal_aat DOUBLE PRECISION,
    featuretype_literal     TEXT,
    idno_base               TEXT,
    volume                  INTEGER,
    conf_loc_verbal         TEXT,
    alcedo_province         TEXT,
    alcedo_region           TEXT,
    majortype_literal       DOUBLE PRECISION,
    page                    TEXT,
    facs                    TEXT,
    placeid                 TEXT,
    content                 TEXT,
    flag                    TEXT,
    class                   TEXT,
    idno_resource           TEXT,
    name_flat               TEXT,
    pop_number              DOUBLE PRECISION,
    pop_year                DOUBLE PRECISION,
    pop_unit                DOUBLE PRECISION,
    pop_source              DOUBLE PRECISION
);
"""


def load():
    print(f"Reading {DATA_IN} ...")
    df = pd.read_csv(DATA_IN, sep="|", low_memory=False, dtype=str)

    # Normalise column names: lowercase, hyphens → underscores
    df.columns = [c.lower().replace("-", "_") for c in df.columns]

    # Replace pandas NA/NaN string with None (→ NULL via COPY)
    df = df.where(df.notna(), None)

    conn = db_connect()
    conn.autocommit = True

    print("Creating table alcedo_og ...")
    conn.execute(DDL_CREATE)

    # Stream via COPY (binary CSV in memory — fast for 19k rows)
    cols = list(df.columns)
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)

    copy_sql = f"COPY alcedo_og ({', '.join(cols)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')"
    with conn.cursor() as cur:
        with cur.copy(copy_sql) as copy:
            copy.write(buf.read())

    count = conn.execute("SELECT COUNT(*) FROM alcedo_og").fetchone()[0]
    print(f"Loaded {count:,} rows into alcedo_og.")
    conn.close()


if __name__ == "__main__":
    load()
