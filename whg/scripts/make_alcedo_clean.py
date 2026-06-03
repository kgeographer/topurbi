"""
make_alcedo_clean.py

Creates alcedo_clean from alcedo_og with the following normalisations:

  Whitespace (TRIM):
    district, alcedo_province, alcedo_region, observation

  Capitalisation / spelling:
    conf_loc_verbal  : 'Sufficient' → 'sufficient'
                       'auto'       → 'automatic'
    majortype        : 'Referral'   → 'referral'   (aligns with other lowercase values)
    resolutionstage  : 'manual_qgis' → 'manual-qgis'  (hyphen is dominant form)

All other columns are carried over unchanged.
alcedo_og is never modified.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from db_utils import db_connect

SQL = """
DROP TABLE IF EXISTS alcedo_clean;
CREATE TABLE alcedo_clean AS
SELECT
    entry_id,
    lemma,
    normname,
    corresp_entry,
    subentry,
    doublette,
    historical,
    doubtful,
    fantastical,
    dot_on_map,
    special_info,
    entrytype,

    CASE majortype
        WHEN 'Referral' THEN 'referral'
        ELSE majortype
    END AS majortype,

    featuretype,
    featuretype_aat,
    nation,
    region,
    prov_group,
    province,
    TRIM(district)          AS district,
    partido,
    historical_alc,
    fantastical_alc,
    nation_alc,

    CASE resolutionstage
        WHEN 'manual_qgis' THEN 'manual-qgis'
        ELSE resolutionstage
    END AS resolutionstage,

    falsematch,
    gazetteermatch,
    conf_identity,
    lat,
    lon,
    conf_loc,

    CASE conf_loc_verbal
        WHEN 'Sufficient' THEN 'sufficient'
        WHEN 'auto'       THEN 'automatic'
        ELSE conf_loc_verbal
    END AS conf_loc_verbal,

    TRIM(observation)       AS observation,
    source,
    alcedo_location_qual,
    alcedo_name_qual,
    alcedo_identity_qual,
    alcedo_featuretype_qual,
    alcedo_province_qual,
    relative_province,
    has_loc_info,
    reviewer,
    review_method,
    auto,
    nombre_estandar,
    random,
    bad_category,
    featuretype_literal_aat,
    featuretype_literal,
    idno_base,
    volume,
    TRIM(alcedo_province)   AS alcedo_province,
    TRIM(alcedo_region)     AS alcedo_region,
    majortype_literal,
    page,
    facs,
    placeid,
    content,
    flag,
    class,
    idno_resource,
    name_flat,
    pop_number,
    pop_year,
    pop_unit,
    pop_source
FROM alcedo_og;
"""


def main():
    conn = db_connect()
    conn.autocommit = True
    print("Creating alcedo_clean ...")
    conn.execute(SQL)
    count = conn.execute("SELECT COUNT(*) FROM alcedo_clean").fetchone()[0]
    print(f"alcedo_clean: {count:,} rows")
    conn.close()


if __name__ == "__main__":
    main()
