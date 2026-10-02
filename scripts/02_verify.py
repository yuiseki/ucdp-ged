#!/usr/bin/env python3
"""Check every release: its files are the ones fetched, and DuckDB reads its Parquet right.

For each release:
  - the zip and the codebook have the sha256 in MANIFEST.json
  - the Parquet has the pinned number of rows and every id once
  - every column has the type column_type gives its name
  - the GeoParquet metadata names a Point geometry, and every row has one
  - a spatial filter on the geometry returns what a filter on latitude and
    longitude returns
  - the totals of best, deaths_civilians and the rows by type of violence
    equal those counted from the CSV inside the zip with the csv module, so
    the conversion lost or changed nothing
  - a plain DuckDB without the spatial extension opens the file
  - no row group carries a bloom filter
"""

import collections
import csv
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PQ = ROOT / "data" / "parquet"
RELEASES = ROOT / "scripts" / "RELEASES.json"
EXPECTED_ROWS = {"26.1": 417968, "25.1": 385918}
# two boxes to compare a filter on the geometry with one on the coordinates; the
# second takes in Japan and its surroundings (26.1 has two events there, both
# in Primorsky Krai, Russia)
BOXES = {"Syria": (35.7, 32.3, 42.4, 37.4), "Japan and around": (122.9, 24.0, 146.0, 45.6)}

_spec = importlib.util.spec_from_file_location("export", ROOT / "scripts" / "03_export_parquet.py")
export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def from_csv(zpath: Path, member: str) -> dict:
    best = civ = 0
    by_type: collections.Counter = collections.Counter()
    with zipfile.ZipFile(zpath) as z, z.open(member) as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", newline="")):
            best += int(row["best"])
            civ += int(row["deaths_civilians"])
            by_type[int(row["type_of_violence"])] += 1
    return {"best": best, "civilians": civ, "by_type": dict(sorted(by_type.items()))}


def main() -> int:
    failures = []

    def check(ok: bool, what: str) -> None:
        print(("ok    " if ok else "FAIL  ") + what)
        if not ok:
            failures.append(what)

    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    for version, r in json.loads(RELEASES.read_text()).items():
        d = RAW / version
        manifest = json.loads((d / "MANIFEST.json").read_text())
        bad = [n for n, m in manifest.items() if sha256(d / n) != m["sha256"]]
        check(not bad, f"{version}: zip and codebook match MANIFEST.json")

        p = PQ / version / "ged.parquet"
        rows, ids = con.sql(f"select count(*), count(distinct id) from '{p}'").fetchone()
        check(rows == EXPECTED_ROWS[version], f"{version}: {rows:,} rows")
        check(ids == rows, f"{version}: every id once")

        types = dict(
            con.sql(
                f"select column_name, column_type from (describe select * from '{p}')"
            ).fetchall()
        )
        wrong = {c: t for c, t in types.items() if c != "geometry" and t != export.column_type(c)}
        check(not wrong, f"{version}: every column has its type ({wrong or 'all as named'})")

        geo = json.loads(con.sql(
            f"select decode(value) from parquet_kv_metadata('{p}') where decode(key) = 'geo'"
        ).fetchone()[0])  # fmt: skip
        g = geo["columns"]["geometry"]
        check(g["geometry_types"] == ["Point"], f"{version}: GeoParquet {geo['version']}, Point")
        nulls = con.sql(f"select count(*) - count(geometry) from '{p}'").fetchone()[0]
        check(nulls == 0, f"{version}: every row has a point")

        for place, (w, s, e, n) in BOXES.items():
            by_geom, by_coords = con.sql(
                f"select count(*) filter (where st_intersects(geometry, st_makeenvelope({w}, {s}, {e}, {n}))), "
                f"count(*) filter (where longitude between {w} and {e} and latitude between {s} and {n}) "
                f"from '{p}'"
            ).fetchone()
            check(
                by_geom == by_coords,
                f"{version}: {place} box, {by_geom:,} events by geometry and by coordinates",
            )

        want = from_csv(d / Path(r["csv_zip"]).name, r["member"])
        best, civ = con.sql(f"select sum(best), sum(deaths_civilians) from '{p}'").fetchone()
        by_type = dict(
            con.sql(
                f"select type_of_violence, count(*) from '{p}' group by 1 order by 1"
            ).fetchall()
        )
        check((best, civ, by_type) == (want["best"], want["civilians"], want["by_type"]),
              f"{version}: best {best:,}, civilians {civ:,}, by type {by_type} as in the CSV")  # fmt: skip

        plain = duckdb.connect()
        n = plain.sql(f"select count(*) from '{p}' where country = 'Syria'").fetchone()[0]
        check(n > 0, f"{version}: a DuckDB without spatial opens it ({n:,} Syrian events)")

        bloom = con.sql(
            f"select count(*) filter (where bloom_filter_offset is not null) from parquet_metadata('{p}')"
        ).fetchone()[0]
        check(bloom == 0, f"{version}: no bloom filters")

    if failures:
        print(f"\n{len(failures)} checks failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
