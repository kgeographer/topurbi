"""
export_lptsv.py

Export alcedo_candidates to WHG LP-TSV format.

Usage:
  python export_lptsv.py                  # full export → alcedo_lptsv.tsv
  python export_lptsv.py --sample 500     # 500 well-located records → alcedo_sample_500.tsv

LP-TSV spec: tab-delimited, one place per row.
Empty string for NULL fields. Random seed fixed for reproducibility of sample.
"""

import os, sys, csv, argparse
from pathlib import Path
import psycopg
import psycopg.rows
from dotenv import load_dotenv

load_dotenv()

OUT_DIR = Path(__file__).parent.parent / "data"

COLUMNS = [
    "id", "title", "title_source", "title_uri",
    "ccodes", "fclasses", "types",
    "lat", "lon", "geowkt",
    "start", "end",
    "links", "description", "approximation",
]

# conf_loc_verbal values considered meaningfully located
LOCATED = ("well_placed", "exact", "sufficient", "automatic")

QUERY_FULL = """
SELECT
    id, title,
    ccodes, fclasses, types,
    lat, lon,
    start, "end",
    links, description, approximation,
    conf_loc_verbal
FROM alcedo_candidates
ORDER BY id
"""

QUERY_SAMPLE = """
SELECT
    id, title,
    ccodes, fclasses, types,
    lat, lon,
    start, "end",
    links, description, approximation,
    conf_loc_verbal
FROM alcedo_candidates
WHERE conf_loc_verbal = ANY(%(located)s)
  AND lat IS NOT NULL AND lon IS NOT NULL
ORDER BY RANDOM()
LIMIT %(limit)s
"""


def truncate_desc(text, limit=500):
    if not text or len(text) <= limit:
        return text or ""
    cut = text[:limit]
    dot = cut.rfind(".")
    return (cut[:dot + 1] if dot > limit // 2 else cut) + "..."


def row_to_tsv(row, truncate=False):
    return [
        row["id"],
        row["title"],
        "",                             # title_source — not applicable for Alcedo
        "",                             # title_uri
        row["ccodes"]      or "",
        row["fclasses"]    or "",
        row["types"]       or "",
        f"{row['lat']:.6f}"  if row["lat"]  is not None else "",
        f"{row['lon']:.6f}"  if row["lon"]  is not None else "",
        "",                             # geowkt — points only for initial upload
        row["start"]       if row["start"] is not None else "",
        row["end"]         if row["end"]   is not None else "",
        row["links"]       or "",
        truncate_desc(row["description"]) if truncate else (row["description"] or ""),
        row["approximation"] or "",
    ]


def write_lptsv(rows, outpath, truncate=False):
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        w.writerow(COLUMNS)
        for row in rows:
            w.writerow(row_to_tsv(row, truncate=truncate))


def summarise(rows, label):
    n         = len(rows)
    has_links = sum(1 for r in rows if r["links"])
    has_desc  = sum(1 for r in rows if r["description"])
    has_cc    = sum(1 for r in rows if r["ccodes"])
    fclass_ct = {}
    for r in rows:
        fclass_ct[r["fclasses"]] = fclass_ct.get(r["fclasses"], 0) + 1

    print(f"\n{label}: {n:,} rows")
    print(f"  ccodes:      {has_cc:>6,} / {n:,}")
    print(f"  links:       {has_links:>6,} / {n:,}")
    print(f"  description: {has_desc:>6,} / {n:,}")
    print(f"  fclasses:    " +
          "  ".join(f"{k}:{v:,}" for k, v in sorted(fclass_ct.items())))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, metavar="N",
                        help="Export N well-located records (random sample)")
    args = parser.parse_args()

    conn = psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        row_factory=psycopg.rows.dict_row,
    )

    if args.sample:
        outpath = OUT_DIR / f"alcedo_sample_{args.sample}.tsv"
        print(f"Querying {args.sample} well-located records (random) ...")
        rows = conn.execute(QUERY_SAMPLE,
                            {"located": list(LOCATED),
                             "limit": args.sample}).fetchall()
        write_lptsv(rows, outpath, truncate=True)
    else:
        outpath = OUT_DIR / f"alcedo_lptsv.tsv"
        print("Querying full candidate set ...")
        rows = conn.execute(QUERY_FULL).fetchall()
        write_lptsv(rows, outpath, truncate=False)
    summarise(rows, outpath.name)
    print(f"\nWrote → {outpath}")

    conn.close()


if __name__ == "__main__":
    main()
