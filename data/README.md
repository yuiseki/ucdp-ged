---
license: cc-by-4.0
language:
- en
task_categories:
- tabular-classification
- tabular-regression
- time-series-forecasting
tags:
- conflict
- political-violence
- ucdp
- geospatial
- geoparquet
size_categories:
- 100K<n<1M
configs:
- config_name: '26.1'
  data_files: parquet/26.1/ged.parquet
  default: true
- config_name: '25.1'
  data_files: parquet/25.1/ged.parquet
---

# ucdp-ged

The UCDP Georeferenced Event Dataset: every event of organised violence the
Uppsala Conflict Data Program has recorded since 1989, one row each, with
where it happened, when, who the sides were, and how many died. One subset
per release, as UCDP published it, with a typed GeoParquet beside it.

CC BY 4.0, on condition that the publications UCDP lists are cited (see
Licence).

## Releases

UCDP publishes one release a year and moves the previous one to an archive
page. Analyses are to state the release they used, so each release is its
own subset, named by its version, and a new one is added beside the others.

| subset | events | period | countries | zip | codebook |
|---|---:|---|---:|---|---|
| `26.1` | 417,968 | 1989-01-01 to 2025-12-31 | 126 | `raw/26.1/ged261-csv.zip` | `raw/26.1/ged261.pdf` |
| `25.1` | 385,918 | 1989-01-01 to 2024-12-31 | 124 | `raw/25.1/ged251-csv.zip` | `raw/25.1/ged251.pdf` |

The zips and codebooks are UCDP's own files, byte for byte; each release's
`MANIFEST.json` gives their URLs, sizes, sha256 and Last-Modified. The two
releases have the same 49 columns. Monthly candidate releases are not here.

## Columns and types

The meaning of every column is in the release's codebook. In the Parquet the
type comes from the column's name, never from inference:

| columns | type |
|---|---|
| `id`, `year`, `type_of_violence`, `*_dset_id`, `*_new_id`, `number_of_sources`, `where_prec`, `priogrid_gid`, `country_id`, `event_clarity`, `date_prec`, `deaths_*`, `best`, `high`, `low` | BIGINT |
| `latitude`, `longitude` | DOUBLE |
| `date_start`, `date_end` | TIMESTAMP |
| `active_year` | BOOLEAN |
| everything else, including `gwnoa` and `gwnob` | the text of the CSV |
| `geometry` | added here: a point from longitude and latitude (WGS 84) |

`gwnoa` holds lists such as `2;200;900`. A type inferrer that sees integers
in its first rows takes it for a number and stops at row 138,884 of 25.1.

`type_of_violence` is 1 state-based conflict, 2 non-state conflict, 3
one-sided violence. `best` is UCDP's best estimate of deaths and equals the
sum of the four `deaths_*` columns; `low` and `high` are its low and high
estimates. They do not always bracket `best`: 5,075 rows of 26.1 and 4,967 of 25.1 break
`low <= best <= high`. The codebook explains this only for events of
`event_clarity` 2, so check the order before using them as an interval.

```sql
-- DuckDB, straight off the Hub: deaths by year and type of violence, release 26.1
SELECT year, type_of_violence, sum(best) AS deaths
FROM 'hf://datasets/yuiseki/ucdp-ged/parquet/26.1/ged.parquet'
GROUP BY ALL ORDER BY ALL;
```

## Checked before upload

`scripts/02_verify.py` in the source repository checks each release with
DuckDB: every id once; every column of the type its name gives; GeoParquet
1.0.0 with a point on every row; a filter on the geometry and a filter on the
coordinates return the same events; the totals of `best` and
`deaths_civilians` and the counts by type of violence equal those counted
from the CSV in the zip with Python's csv module (26.1: 4,257,891 and
1,570,458); a DuckDB without the spatial extension opens the file.

## Things to know

The `source_*` columns quote news reports: the outlet, the date and the
headline. They are empty for 97,496 rows of 26.1, most of them before 2013.
UCDP distributes them under the same licence as the rest; whether the
headlines themselves are UCDP's to license was not checked.

HDX carries country extracts of UCDP data labelled `cc-by-igo`. This dataset
follows UCDP's own download page, which says CC BY 4.0.

## Licence

UCDP's download page (https://ucdp.uu.se/downloads/, read on 2026-10-02):

> All datasets are free of charge and licensed under CC BY 4.0

and, after a dash in the original,

> you are free to use and redistribute them provided you cite the relevant
> publications listed with each dataset.

Cite for release 26.1, as the download page lists:

- Davies, Shawn, Therése Pettersson and Magnus Öberg (2026). Organized
  violence 1989–2025, and violent political protests. Journal of Peace
  Research. https://doi.org/10.1093/jopres/xjag046
- Sundberg, Ralph and Erik Melander (2013). Introducing the UCDP Georeferenced
  Event Dataset. Journal of Peace Research 50(4): 523-532.
  https://doi.org/10.1177/0022343313484347

Cite for release 25.1, as its download page listed:

- Davies, S., Pettersson, T., Sollenberg, M., and Öberg, M. (2025). Organized
  violence 1989–2024, and the challenges of identifying civilian victims.
  Journal of Peace Research 62(4). https://doi.org/10.1177/00223433251345636
- Sundberg and Melander (2013), as above.

When appropriate, also the codebook of the release (Högbladh, Stina,
"UCDP GED Codebook version 26.1", 2026, or "version 25.1", 2025, Department
of Peace and Conflict Research, Uppsala University).

The zips and codebooks are UCDP's, unchanged. The Parquet is made from them;
`LICENSE` beside this file says what was done.
