import logging
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PERSONS_PATH = PROCESSED_DIR / "persons_clean.parquet"
MEMBERSHIPS_PATH = PROCESSED_DIR / "memberships_clean.parquet"

# Cutoffs
MIN_BIRTH_YEAR = 1800
MAX_BIRTH_YEAR = 2015
TODAY = pd.Timestamp.today().normalize()
YEAR_RANGE = range(1850, TODAY.year + 1)


def main():
    missing = [p for p in (PERSONS_PATH, MEMBERSHIPS_PATH) if not p.exists()]
    if missing:
        logger.error("Missing input parquet(s): %s", ", ".join(str(p.name) for p in missing))
        logger.error("Run `uv run python eda/1_gather_data.py` first to download and cache the NDJSON exports.")
        sys.exit(1)

    logger.info("Loading persons and memberships...")
    persons = pd.read_parquet(PERSONS_PATH)
    memberships = pd.read_parquet(MEMBERSHIPS_PATH)

    # federal
    persons = persons[persons["body_key"] == "CHE"].copy()
    memberships = memberships[memberships["body_key"] == "CHE"].copy()

    # convert & filter
    persons["birthday"] = pd.to_datetime(persons["birthday"], errors="coerce")
    persons = persons[persons["birthday"].notna()]
    persons = persons[
        (persons["birthday"].dt.year >= MIN_BIRTH_YEAR)
        & (persons["birthday"].dt.year <= MAX_BIRTH_YEAR)
    ]
    logger.info(f"Federal persons with valid birthday: {len(persons):,}")

    # membership, parliament only
    parl = memberships[memberships["type_harmonized_de"] == "Parlament (Legislativrat)"].copy()
    parl = parl[parl["group_name_de"].isin(["Nationalrat", "Ständerat"])]
    parl["begin_date"] = pd.to_datetime(parl["begin_date"], errors="coerce")
    parl["end_date"] = pd.to_datetime(parl["end_date"], errors="coerce")
    parl = parl[parl["begin_date"].notna()]
    # filter nonsense dates
    parl.loc[parl["end_date"].dt.year > TODAY.year + 5, "end_date"] = pd.NaT
    parl.loc[parl["end_date"].dt.year < 1848, "end_date"] = pd.NaT

    # active members get end_date of today
    parl["end_date_eff"] = parl["end_date"].fillna(TODAY)

    # Standardize chamber
    parl["chamber"] = parl["group_name_de"].map(
        {"Nationalrat": "Nationalrat", "Ständerat": "Ständerat"}
    )
    logger.info(f"NR/SR memberships: {len(parl):,}")

    # join
    parl = parl.merge(
        persons[["id", "firstname", "lastname", "birthday", "gender",
                 "party_de", "party_harmonized_de", "electoral_district_de"]],
        left_on="person_id", right_on="id", how="inner", suffixes=("", "_person"),
    )
    logger.info(f"Memberships after join with persons (with birthday): {len(parl):,}")

    parl["entry_age"] = ((parl["begin_date"] - parl["birthday"]).dt.days / 365.25).round(2)
    parl["exit_age"] = ((parl["end_date_eff"] - parl["birthday"]).dt.days / 365.25).round(2)
    parl["duration_years"] = ((parl["end_date_eff"] - parl["begin_date"]).dt.days / 365.25).round(2)
    parl["is_active"] = parl["end_date"].isna()

    # save memberships
    memberships_out = parl[[
        "person_id", "firstname", "lastname", "birthday", "gender",
        "party_de", "party_harmonized_de", "electoral_district_de",
        "chamber", "begin_date", "end_date", "end_date_eff",
        "entry_age", "exit_age", "duration_years", "is_active",
    ]].copy()
    memberships_out.to_parquet(PROCESSED_DIR / "parliament_memberships.parquet", index=False)
    logger.info(f"Saved parliament_memberships.parquet: {len(memberships_out):,}")

    # summary on person level
    person_summary = (
        parl.groupby("person_id")
        .agg(
            firstname=("firstname", "first"),
            lastname=("lastname", "first"),
            birthday=("birthday", "first"),
            gender=("gender", "first"),
            party_de=("party_de", "last"),
            party_harmonized_de=("party_harmonized_de", "last"),
            canton=("electoral_district_de", "last"),
            first_entry_date=("begin_date", "min"),
            last_seat_end=("end_date_eff", "max"),
            entry_age=("entry_age", "min"),
            total_tenure_years=("duration_years", "sum"),
            num_memberships=("chamber", "count"),
            chambers=("chamber", lambda s: ",".join(sorted(set(s)))),
            currently_active=("is_active", "any"),
        )
        .reset_index()
    )

    person_summary["age_today"] = (
        (TODAY - person_summary["birthday"]).dt.days / 365.25
    ).round(1)
    person_summary.to_parquet(PROCESSED_DIR / "politicians.parquet", index=False)
    logger.info(f"Saved politicians.parquet: {len(person_summary):,}")

    # yearly snapshots
    snapshots = []
    for year in YEAR_RANGE:
        ref = pd.Timestamp(year=year, month=7, day=1)
        in_office = parl[(parl["begin_date"] <= ref) & (parl["end_date_eff"] >= ref)].copy()
        if in_office.empty:
            continue
        in_office["age"] = ((ref - in_office["birthday"]).dt.days / 365.25).round(2)
        snap = in_office[[
            "person_id", "firstname", "lastname", "chamber", "gender",
            "party_de", "party_harmonized_de", "age",
        ]].copy()
        snap["year"] = year
        snapshots.append(snap)

    yearly = pd.concat(snapshots, ignore_index=True)
    yearly.to_parquet(PROCESSED_DIR / "parliament_yearly.parquet", index=False)
    logger.info(
        f"Saved parliament_yearly.parquet: {len(yearly):,} (years "
        f"{yearly['year'].min()}–{yearly['year'].max()})"
    )


if __name__ == "__main__":
    main()
