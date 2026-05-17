import gzip
import logging
import shutil
import urllib.request
from pathlib import Path

import pyarrow.json as pj
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

OPENPARL_BASE = "https://files.openparldata.ch/exports"
FILES = ["persons", "memberships"]


def ensure_ndjson(name: str) -> Path:
    ndjson_path = RAW_DIR / f"{name}.ndjson"
    gz_path = RAW_DIR / f"{name}.ndjson.gz"

    if ndjson_path.exists():
        logger.info(f"  {ndjson_path.name} already present")
        return ndjson_path

    if not gz_path.exists():
        url = f"{OPENPARL_BASE}/{name}.ndjson.gz"
        logger.info(f"  downloading {url}")
        urllib.request.urlretrieve(url, gz_path)
        logger.info(f"  saved {gz_path.name} ({gz_path.stat().st_size / 1e6:.1f} MB)")

    logger.info(f"  decompressing {gz_path.name} -> {ndjson_path.name}")
    with gzip.open(gz_path, "rb") as f_in, open(ndjson_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    return ndjson_path


def ndjson_to_parquet(name: str, ndjson_path: Path) -> Path:
    out_path = PROCESSED_DIR / f"{name}_clean.parquet"
    logger.info(f"  converting -> {out_path.name}")
    table = pj.read_json(ndjson_path)
    pq.write_table(table, out_path)
    logger.info(f"  wrote {table.num_rows:,} records")
    return out_path


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Fetching {len(FILES)} export(s) from {OPENPARL_BASE}")
    for name in FILES:
        logger.info(f"[{name}]")
        ndjson = ensure_ndjson(name)
        ndjson_to_parquet(name, ndjson)


if __name__ == "__main__":
    main()
