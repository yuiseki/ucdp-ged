# ucdp-ged

Dataset: https://huggingface.co/datasets/yuiseki/ucdp-ged

The UCDP Georeferenced Event Dataset, one subset per release, as the Uppsala
Conflict Data Program published it, with a typed GeoParquet beside it, and
the code that fetches, checks and converts it. This repository holds the
code; the data is on the Hub.

## Where things are

```
scripts/RELEASES.json         the releases taken: page, zip, codebook, CSV member
scripts/01_download.py        the zip and codebook of each release, against Content-Length
scripts/02_verify.py          checks each release with DuckDB before anything is uploaded
scripts/03_export_parquet.py  CSV -> GeoParquet, typed by column name
src/publish.py                pushes the data and its card to the Hub
tests/                        the type rule, and values that must stop the build

data/README.md                the dataset card. Uploaded as-is; declare a new release's subset here
data/LICENSE                  CC BY 4.0, the citation condition, and what the Parquet changes
data/provenance.yaml          the releases, their counts, the checks, what was done
data/raw/<version>/           generated: UCDP's zip and codebook, and MANIFEST.json
data/parquet/<version>/       generated: ged.parquet
```

## Running it

```sh
uv run python scripts/01_download.py
uv run python scripts/03_export_parquet.py
uv run python scripts/02_verify.py
uv run python src/publish.py          # dry run; --push to upload
uv run pytest
```

## Adding a release

Add it to `RELEASES.json` (the current release is on
https://ucdp.uu.se/downloads/, older ones on its `olddw.html`), its expected
row count to `EXPECTED_ROWS` in `02_verify.py`, and its subset and citations
to `data/README.md`; `src/publish.py` refuses to upload a card that does
not declare every release. A column the type rule does not know becomes
text, and a value that does not fit a known type stops the build, so the
first run of a new release says what differs.

Releases 19.1 to 26.1 are taken: 19.1 is the oldest on the archive page with
a codebook. 19.1 has 42 columns and leaves Syria out; 25.1 and 26.1 write
`active_year` as true and false where the others write 1 and 0.

## Three traps

**Type inference stops on gwnoa.** It holds lists like `2;200;900`; an
inferrer that saw only integers fails at row 138,884 of 25.1. Types come from
the column names here.

**The CSV has line breaks inside quoted fields.** `wc -l` overcounts. Rows
are counted with the csv module.

**Bloom filters cost a request per row group over HTTP.** The Parquet is
written without them.

## Licence

The code here is MIT. The data it fetches is CC BY 4.0 from UCDP, on
condition that the publications listed with each release are cited; see
`data/README.md`.
