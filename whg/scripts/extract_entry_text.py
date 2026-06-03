"""
extract_entry_text.py

Parse Alcedo_vol_1-5.xml from _topurbi-data/data/ and extract the
plain-text entry sense (dictionary body) for every <entry> element.

Outputs:
  DB table  alcedo_entry_text  — all entries; joins to alcedo_candidates on entry_id
  TSV file  whg/data/alcedo_entry_text.tsv  — same, without sense_xml

Culling note:
  alcedo_og / alcedo_clean  = 19,305 rows (no rows removed between them)
  alcedo_candidates         = 17,467 rows (excludes Terms, Referrals,
                              Corrections, doublettes, one fclass-excluded)
  This table stores all 19,305 TEI entries; the FK relationship to
  alcedo_candidates is resolved at query time: JOIN ON entry_id = id.
"""

import os, sys, re, csv
from pathlib import Path
from lxml import etree
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()

TEI    = "http://www.tei-c.org/ns/1.0"
T      = f"{{{TEI}}}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

VOL_DIR = Path("/Users/karlg/Documents/repos/_topurbi-data/data")
TSV_OUT = Path(__file__).parent.parent / "data" / "alcedo_entry_text.tsv"

DDL = """
DROP TABLE IF EXISTS alcedo_entry_text;
CREATE TABLE alcedo_entry_text (
    entry_id   TEXT PRIMARY KEY,   -- joins to alcedo_candidates.id
    volume     SMALLINT,
    entrytype  TEXT,
    majortype  TEXT,
    form_lemma TEXT,
    sense_text TEXT,               -- plain text, tags stripped
    sense_xml  TEXT                -- raw <sense> XML preserved for future use
);
"""

INSERT = """
INSERT INTO alcedo_entry_text
    (entry_id, volume, entrytype, majortype, form_lemma, sense_text, sense_xml)
VALUES
    (%(entry_id)s, %(volume)s, %(entrytype)s, %(majortype)s,
     %(form_lemma)s, %(sense_text)s, %(sense_xml)s)
ON CONFLICT DO NOTHING
"""


def normalize(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_sense(entry):
    """Return (sense_text, sense_xml) from <sense>, or (None, None)."""
    sense_el = entry.find(f"{T}sense")
    if sense_el is None:
        return None, None
    text = normalize("".join(sense_el.itertext()))
    xml  = etree.tostring(sense_el, encoding="unicode")
    return text, xml


def extract_lemma(entry):
    """Return plain text of <orth type='lemma'>, or None."""
    for orth in entry.findall(f".//{T}orth"):
        if orth.get("type") == "lemma":
            return normalize("".join(orth.itertext()))
    return None


def parse_volume(vol_num):
    path = VOL_DIR / f"Alcedo_vol_{vol_num}.xml"
    print(f"  Parsing vol {vol_num} ({path.name}) ...", end=" ", flush=True)
    tree  = etree.parse(str(path))
    rows  = []
    for entry in tree.findall(f".//{T}entry"):
        eid = entry.get(XML_ID)
        if not eid:
            continue
        fs = {f.get("name"): f.get("fVal")
              for f in entry.findall(f"{T}fs/{T}f")}
        sense_text, sense_xml = extract_sense(entry)
        rows.append({
            "entry_id":   eid,
            "volume":     vol_num,
            "entrytype":  fs.get("entrytype"),
            "majortype":  fs.get("majortype"),
            "form_lemma": extract_lemma(entry),
            "sense_text": sense_text,
            "sense_xml":  sense_xml,
        })
    print(f"{len(rows):,} entries")
    return rows


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

    print("Creating alcedo_entry_text ...")
    conn.execute(DDL)

    all_rows = []
    for vol in range(1, 6):
        all_rows.extend(parse_volume(vol))

    print(f"\nTotal entries: {len(all_rows):,}")

    print("Inserting into DB ...")
    with conn.cursor() as cur:
        cur.executemany(INSERT, all_rows)
    print(f"Done. {len(all_rows):,} rows in alcedo_entry_text.")

    # Coverage against candidates
    stats = conn.execute("""
        SELECT
            COUNT(*)                                           AS total,
            COUNT(*) FILTER (WHERE entry_id IN
                (SELECT id FROM alcedo_candidates))            AS in_candidates,
            COUNT(*) FILTER (WHERE sense_text IS NOT NULL)     AS has_sense,
            COUNT(*) FILTER (WHERE sense_text IS NULL)         AS no_sense
        FROM alcedo_entry_text
    """).fetchone()
    print(f"\nCoverage:")
    print(f"  total entries:        {stats['total']:>7,}")
    print(f"  in alcedo_candidates: {stats['in_candidates']:>7,}")
    print(f"  has sense text:       {stats['has_sense']:>7,}")
    print(f"  no sense text:        {stats['no_sense']:>7,}")

    # TSV (omit sense_xml — too large/noisy for a flat file)
    print(f"\nWriting TSV: {TSV_OUT} ...")
    TSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(TSV_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(["entry_id", "volume", "entrytype", "majortype",
                    "form_lemma", "sense_text"])
        for r in all_rows:
            w.writerow([r["entry_id"], r["volume"], r["entrytype"],
                        r["majortype"], r["form_lemma"], r["sense_text"]])
    print("Done.")

    conn.close()


if __name__ == "__main__":
    main()
