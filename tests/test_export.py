import importlib.util
from pathlib import Path

import duckdb
import pytest

_spec = importlib.util.spec_from_file_location(
    "export", Path(__file__).parents[1] / "scripts" / "03_export_parquet.py"
)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


@pytest.mark.parametrize(
    ("name", "sql"),
    [
        ("id", "BIGINT"),
        ("deaths_civilians", "BIGINT"),
        ("side_b_dset_id", "BIGINT"),
        ("conflict_new_id", "BIGINT"),
        ("best", "BIGINT"),
        ("latitude", "DOUBLE"),
        ("date_start", "TIMESTAMP"),
        ("active_year", "INTEGER"),
        ("gwnoa", "VARCHAR"),
        ("gwnob", "VARCHAR"),
        ("relid", "VARCHAR"),
        ("source_headline", "VARCHAR"),
        ("a_column_from_an_old_release", "VARCHAR"),
    ],
)
def test_column_type(name, sql):
    assert m.column_type(name) == sql


def _rel(tmp_path, text):
    f = tmp_path / "g.csv"
    f.write_text(text, encoding="utf-8")
    con = duckdb.connect()
    con.execute("install spatial; load spatial")
    return con.sql(m.select_sql(con, f))


HEADER = "id,relid,active_year,latitude,longitude,date_start,gwnoa,best\n"


def test_values_are_typed_and_text_stays_text(tmp_path):
    rel = _rel(
        tmp_path, HEADER + '1,SYR-2015,true,34.75,43.65,2015-02-12 00:00:00.000,"2;200;900",6\n'
    )
    row = dict(zip(rel.columns, rel.fetchone(), strict=True))
    assert row["id"] == 1 and row["best"] == 6 and row["active_year"] == 1
    assert row["gwnoa"] == "2;200;900" and row["relid"] == "SYR-2015"
    assert str(row["date_start"]) == "2015-02-12 00:00:00"
    assert rel.select("st_astext(geometry)").fetchone() == ("POINT (43.65 34.75)",)


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("1,R,true,34.75,43.65,2015-02-12 00:00:00.000,652,6.5\n", "best is not an integer: 6.5"),
        (
            "1,R,yes,34.75,43.65,2015-02-12 00:00:00.000,652,6\n",
            "active_year is not 1, 0, true or false: yes",
        ),
        ("1,R,true,north,43.65,2015-02-12 00:00:00.000,652,6\n", "latitude is not a number: north"),
        ("1,R,true,34.75,43.65,12/02/2015,652,6\n", "date_start is not a timestamp: 12/02/2015"),
    ],
)
def test_a_value_that_does_not_fit_stops_the_run(tmp_path, line, message):
    with pytest.raises(duckdb.Error, match=message):
        _rel(tmp_path, HEADER + line).fetchall()


@pytest.mark.parametrize(("value", "want"), [("1", 1), ("0", 0), ("true", 1), ("false", 0)])
def test_active_year_is_the_codebook_integer(tmp_path, value, want):
    # The codebooks define 1 and 0; the CSVs of 25.1 and 26.1 write true and false.
    rel = _rel(tmp_path, HEADER + f"1,R,{value},34.75,43.65,2015-02-12 00:00:00.000,652,6\n")
    assert rel.select("active_year").fetchone() == (want,)


def test_a_date_without_a_time_is_read(tmp_path):
    # 19.1 writes date_start as 2019-01-01, later releases with a time of day.
    rel = _rel(tmp_path, HEADER + "1,R,1,34.75,43.65,2019-01-01,652,6\n")
    assert str(rel.select("date_start").fetchone()[0]) == "2019-01-01 00:00:00"
