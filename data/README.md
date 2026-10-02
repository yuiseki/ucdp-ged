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
- config_name: '24.1'
  data_files: parquet/24.1/ged.parquet
- config_name: '23.1'
  data_files: parquet/23.1/ged.parquet
- config_name: '22.1'
  data_files: parquet/22.1/ged.parquet
- config_name: '21.1'
  data_files: parquet/21.1/ged.parquet
- config_name: '20.1'
  data_files: parquet/20.1/ged.parquet
- config_name: '19.1'
  data_files: parquet/19.1/ged.parquet
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
| `24.1` | 349,733 | 1989-01-01 to 2023-12-31 | 124 | `raw/24.1/ged241-csv.zip` | `raw/24.1/ged241.pdf` |
| `23.1` | 316,818 | 1989-01-01 to 2022-12-31 | 124 | `raw/23.1/ged231-csv.zip` | `raw/23.1/ged231.pdf` |
| `22.1` | 293,634 | 1989-01-01 to 2021-12-31 | 123 | `raw/22.1/ged221-csv.zip` | `raw/22.1/ged221.pdf` |
| `21.1` | 261,864 | 1989-01-01 to 2020-12-31 | 123 | `raw/21.1/ged211-csv.zip` | `raw/21.1/ged211.pdf` |
| `20.1` | 225,385 | 1989-01-01 to 2019-12-31 | 122 | `raw/20.1/ged201-csv.zip` | `raw/20.1/ged201.pdf` |
| `19.1` | 152,616 | 1989-01-01 to 2018-12-31, without Syria | 120 | `raw/19.1/ged191-csv.zip` | `raw/19.1/ged191.pdf` |

The period is that of `date_start`. In 22.1 three events that began in late
December 2021 end in January 2022.

The zips and codebooks are UCDP's own files, byte for byte; each release's
`MANIFEST.json` gives their URLs, sizes, sha256 and Last-Modified. Releases
20.1 to 26.1 have the same 49 columns. 19.1 is the oldest release here
because it is the oldest with a codebook on UCDP's archive page, so every
column of every release is explained. Monthly candidate releases are not
here.

19.1 differs from the rest:

- It leaves Syria out. Its codebook: "Data for Syria is not included in
  19.1 version – a separate release V 652.1601.1911 was released for the
  period 2016-01-01 to 2019-11-30 on 2019-12-17." That separate release is
  not here.
- It has 42 columns. It lacks `relid`, `code_status`, `conflict_dset_id`,
  `dyad_dset_id`, `side_a_dset_id`, `side_b_dset_id` and
  `where_description`.
- Its CSV writes `date_start` and `date_end` as a date without a time; they
  are midnight in the Parquet, as in the other releases.

## Columns and types

The meaning of every column is in the release's codebook. In the Parquet the
type comes from the column's name, never from inference:

| columns | type |
|---|---|
| `id`, `year`, `type_of_violence`, `*_dset_id`, `*_new_id`, `number_of_sources`, `where_prec`, `priogrid_gid`, `country_id`, `event_clarity`, `date_prec`, `deaths_*`, `best`, `high`, `low` | BIGINT |
| `latitude`, `longitude` | DOUBLE |
| `date_start`, `date_end` | TIMESTAMP |
| `active_year` | INTEGER, 1 or 0 |
| everything else, including `gwnoa` and `gwnob` | the text of the CSV |
| `geometry` | added here: a point from longitude and latitude (WGS 84) |

`active_year` is 1 when the event belongs to an active conflict, dyad or
actor year, and 0 otherwise, as every codebook defines it. The CSVs of 19.1
to 24.1 write 1 and 0; those of 25.1 and 26.1 write `true` and `false`,
which are read here as 1 and 0, so the column means the same in every
release. (Until 2026-10-02 this dataset held 25.1 and 26.1 only, with
`active_year` as BOOLEAN.)

`gwnoa` holds lists such as `2;200;900`. A type inferrer that sees integers
in its first rows takes it for a number and stops at row 138,884 of 25.1.

`type_of_violence` is 1 state-based conflict, 2 non-state conflict, 3
one-sided violence. `best` is UCDP's best estimate of deaths and equals the
sum of the four `deaths_*` columns; `low` and `high` are its low and high
estimates. They do not always bracket `best`: 5,075 rows of 26.1, 4,967 of 25.1 and
2,506 of 19.1 break `low <= best <= high`. The codebook explains this only for events of
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
from the CSV in the zip with Python's csv module; a DuckDB without the
spatial extension opens the file; no row group has a bloom filter.

| release | `best` | `deaths_civilians` | type 1 | type 2 | type 3 |
|---|---:|---:|---:|---:|---:|
| 26.1 | 4,257,891 | 1,570,458 | 292,121 | 61,451 | 64,396 |
| 25.1 | 3,957,143 | 1,474,095 | 271,331 | 54,982 | 59,605 |
| 24.1 | 3,791,599 | 1,426,646 | 246,119 | 49,046 | 54,568 |
| 23.1 | 3,357,346 | 1,370,447 | 227,509 | 40,642 | 48,667 |
| 22.1 | 2,861,164 | 1,092,263 | 213,689 | 35,665 | 44,280 |
| 21.1 | 2,690,686 | 1,045,569 | 192,769 | 29,005 | 40,090 |
| 20.1 | 2,546,751 | 982,732 | 166,379 | 22,923 | 36,083 |
| 19.1 | 2,089,095 | 870,239 | 107,247 | 14,228 | 31,141 |

The releases are not one series cut at different years: UCDP revises past
events between releases, so the same year can have other totals in another
release. Outside Syria, 2010 has 6,008 events and 30,862 deaths (`best`) in
19.1, and 9,139 events and 34,898 deaths in 26.1; 1,908 events in both
releases have a different `best`.

## Things to know

The `source_*` columns quote news reports: the outlet, the date and the
headline. They are empty for 97,496 rows of 26.1, most of them before 2013 (and for
between 97,913 and 106,398 rows of the older releases).
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

Cite for releases 19.1 to 24.1, as the cover of each codebook asks ("please
always cite"); the archive page lists no publications for them:

- Sundberg and Melander (2013), as above.

For every release, when appropriate, also its codebook, as the cover asks:
Högbladh, Stina, year of the release, "UCDP GED Codebook version" and the
version, Department of Peace and Conflict Research, Uppsala University. For
example Högbladh, Stina (2026), "UCDP GED Codebook version 26.1", and
Högbladh, Stina (2019), "UCDP GED Codebook version 19.1". Always state the
version used.

The zips and codebooks are UCDP's, unchanged. The Parquet is made from them;
`LICENSE` beside this file says what was done.
