#!/usr/bin/env python3
"""Turn each release's CSV into a typed GeoParquet, for the Hub viewer and DuckDB.

The type of a column comes from its name, never from inference: DuckDB's
inferrer stops at row 138,884 of 25.1, where gwnoa holds '2;200;900'. Ids,
counts and deaths are BIGINT, latitude and longitude DOUBLE, date_start and
date_end TIMESTAMP, active_year INTEGER (the codebooks' 1 and 0; the CSVs of
25.1 and 26.1 write true and false, read as 1 and 0); everything else stays the text of
the CSV, including gwnoa and gwnob, which can hold lists. A column this rule
does not know, as older releases may have, is kept as text. A value that does
not fit its type stops the run instead of being rounded or nulled.

A point geometry is added from longitude and latitude (WGS 84). Rows are
sorted by country_id, date_start and id, and the file is written without
bloom filters, which DuckDB reads for every row group a filter touches.

    uv run python scripts/03_export_parquet.py
"""

import csv
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "parquet"
WORK = ROOT / "data" / "work"
RELEASES = ROOT / "scripts" / "RELEASES.json"

INTEGERS = {
    "id", "year", "type_of_violence", "number_of_sources", "where_prec", "priogrid_gid",
    "country_id", "event_clarity", "date_prec", "best", "high", "low",
}  # fmt: skip
INTEGER_PATTERNS = (r".*_dset_id", r".*_new_id", r"deaths_.*")


def column_type(name: str) -> str:
    if name in INTEGERS or any(re.fullmatch(p, name) for p in INTEGER_PATTERNS):
        return "BIGINT"
    if name in ("latitude", "longitude"):
        return "DOUBLE"
    if name in ("date_start", "date_end"):
        return "TIMESTAMP"
    if name == "active_year":
        return "INTEGER"
    return "VARCHAR"


def _expr(path: Path, name: str) -> str:
    c, t = f'"{name}"', column_type(name)
    if t == "VARCHAR":
        return c
    if t == "BIGINT":
        ok, what = f"regexp_full_match({c}, '-?[0-9]+')", "an integer"
    elif t == "DOUBLE":
        ok, what = f"try_cast({c} as double) is not null", "a number"
    elif t == "TIMESTAMP":
        ok, what = (
            f"regexp_full_match({c}, '[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}( [0-9:.]+)?')",
            "a timestamp",
        )
    else:
        # The codebooks define 1 and 0; the CSVs of 25.1 and 26.1 write true and false.
        return (
            f"case when {c} is null then null when {c} in ('1', 'true') then 1 "
            f"when {c} in ('0', 'false') then 0 "
            f"else error('{path.name}: {name} is not 1, 0, true or false: ' || {c}) end"
        )
    return (
        f"case when {c} is null then null when {ok} then cast({c} as {t}) "
        f"else error('{path.name}: {name} is not {what}: ' || {c}) end"
    )


def select_sql(con, path: Path) -> str:
    src = f"read_csv('{path}', header = true, all_varchar = true, strict_mode = true)"
    names = con.sql(f"select * from {src} limit 0").columns
    cols = [f'{_expr(path, n)} as "{n}"' for n in names]
    cols.append(
        "case when latitude is null or longitude is null then null "
        "else st_point(cast(longitude as double), cast(latitude as double)) end as geometry"
    )
    return f"select {', '.join(cols)} from {src}"


def csv_rows(path: Path) -> int:
    """Records counted by the csv module; quoted fields hold line breaks."""
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def main() -> int:
    import duckdb

    releases = json.loads(RELEASES.read_text())
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    for version, r in releases.items():
        zpath = RAW / version / Path(r["csv_zip"]).name
        work = WORK / version
        work.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath) as z:
            z.extract(r["member"], work)  # CRC checked by zipfile on read
        src = work / r["member"]
        expected = csv_rows(src)
        out = OUT / version
        out.mkdir(parents=True, exist_ok=True)
        p = out / "ged.parquet"
        con.execute(
            f"copy ({select_sql(con, src)} order by country_id, date_start, id) to '{p}' "
            "(format parquet, compression zstd, row_group_size 50000, write_bloom_filter false)"
        )
        got = con.sql(f"select count(*) from '{p}'").fetchone()[0]
        if got != expected:
            raise SystemExit(f"{version}: {got} rows written, the CSV has {expected}")
        src.unlink()
        print(f"{version}: {got:,} rows, {p.stat().st_size:,} bytes", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
