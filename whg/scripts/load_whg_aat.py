"""
load_whg_aat.py

Loads whg/data/feature-types-AAT_20230609.tsv into the whg_aat_types
reference table in topurbi. Used by the transform script to filter
alcedo featuretype_aat codes to only those WHG supports.
"""

import os, sys, io
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from db_utils import db_connect

DATA_IN = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data",
                 "feature-types-AAT_20230609.tsv")
)

DDL = """
DROP TABLE IF EXISTS whg_aat_types;
CREATE TABLE whg_aat_types (
    parent    INTEGER,
    aat_id    INTEGER PRIMARY KEY,
    term      TEXT,
    term_full TEXT,
    note      TEXT
);
"""

def main():
    df = pd.read_csv(DATA_IN, sep="\t", dtype=str)
    df.columns = ["parent", "aat_id", "term", "term_full", "note"]

    # Drop category heading rows (no aat_id)
    df = df[df["aat_id"].notna() & (df["aat_id"].str.strip() != "")].copy()
    df["aat_id"] = df["aat_id"].astype(int)
    df["parent"] = pd.to_numeric(df["parent"], errors="coerce").astype("Int64")
    # Keep first occurrence of any duplicate aat_id
    df = df.drop_duplicates(subset="aat_id")

    conn = db_connect()
    conn.autocommit = True

    print("Creating whg_aat_types ...")
    conn.execute(DDL)

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep=r"\N")
    buf.seek(0)

    with conn.cursor() as cur:
        with cur.copy(r"COPY whg_aat_types FROM STDIN WITH (FORMAT csv, NULL '\N')") as copy:
            copy.write(buf.read())

    count = conn.execute("SELECT COUNT(*) FROM whg_aat_types").fetchone()[0]
    print(f"Loaded {count} rows into whg_aat_types")
    conn.close()

if __name__ == "__main__":
    main()
