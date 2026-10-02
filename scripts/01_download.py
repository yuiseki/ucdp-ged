#!/usr/bin/env python3
"""Fetch the CSV zip and the codebook of every release in scripts/RELEASES.json.

UCDP publishes one GED release a year at ucdp.uu.se/downloads/ and moves
older ones to downloads/olddw.html; monthly candidate releases are not
taken. A release is added by adding a line to RELEASES.json. Each file is
kept as served, under data/raw/<version>/, and is accepted only if it has the
Content-Length the server states; data/raw/<version>/MANIFEST.json records
its URL, size, sha256 and Last-Modified. A file already there with a manifest
entry is not fetched again.

    uv run python scripts/01_download.py
"""

import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RELEASES = ROOT / "scripts" / "RELEASES.json"
UA = "ucdp-ged/1 (+https://github.com/yuiseki/ucdp-ged)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str, dest: Path) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
        length = int(r.headers["Content-Length"])
        lm = r.headers.get("Last-Modified", "")
    got = tmp.stat().st_size
    if got != length:
        tmp.unlink()
        raise SystemExit(f"{url}: got {got} bytes, the server stated {length}")
    tmp.replace(dest)
    return {"url": url, "bytes": length, "sha256": sha256(dest), "last_modified": lm}


def main() -> int:
    for version, r in json.loads(RELEASES.read_text()).items():
        d = RAW / version
        d.mkdir(parents=True, exist_ok=True)
        mpath = d / "MANIFEST.json"
        manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
        for key in ("csv_zip", "codebook"):
            name = Path(r[key]).name
            if name in manifest and (d / name).exists():
                continue
            manifest[name] = fetch(r[key], d / name)
            print(
                f"{version}/{name}: {manifest[name]['bytes']:,} bytes, {manifest[name]['last_modified']}"
            )
        mpath.write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
