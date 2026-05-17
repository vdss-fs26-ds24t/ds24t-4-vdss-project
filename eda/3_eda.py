import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
FIG_DIR = OUTPUT_DIR / "figs"

sns.set_theme(style="whitegrid")

NUMERIC_TYPES = ["int8", "int16", "int32", "int64", "float16", "float32", "float64"]


def _top_values(s: pd.Series, k: int = 3) -> str:
    vc = s.value_counts(dropna=True).head(k)
    return "; ".join(f"{str(v)[:40]} ({n})" for v, n in vc.items())


def build_catalogue(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, col in enumerate(df.columns, start=1):
        s = df[col]
        is_num = str(s.dtype) in NUMERIC_TYPES
        row = {
            "index": i,
            "column": col,
            "dtype": str(s.dtype),
            "n_missing": int(s.isna().sum()),
            "pct_missing": round(s.isna().mean() * 100, 2),
            "n_unique": int(s.nunique(dropna=True)),
        }
        if is_num and s.notna().any():
            row["min"] = round(float(s.min()), 3)
            row["median"] = round(float(s.median()), 3)
            row["max"] = round(float(s.max()), 3)
            row["mean"] = round(float(s.mean()), 3)
            row["top_values"] = ""
        else:
            row["min"] = ""
            row["median"] = ""
            row["max"] = ""
            row["mean"] = ""
            row["top_values"] = _top_values(s) if s.notna().any() else ""
        rows.append(row)
    return pd.DataFrame(rows)


def dump_catalogue(name: str, df: pd.DataFrame):
    logger.info(f"[{name}] {len(df):,} rows x {len(df.columns)} cols")
    build_catalogue(df).to_csv(OUTPUT_DIR / f"catalogue_{name}.csv", index=False)


def figure_birthday_coverage_by_decade(persons_che: pd.DataFrame):
    p = persons_che.copy()
    p["birth_year"] = pd.to_datetime(p["birthday"], errors="coerce").dt.year
    p_valid = p[p["birth_year"].between(1800, 2020)]
    by_dec = (p_valid["birth_year"] // 10 * 10).value_counts().sort_index()

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(by_dec.index.astype(int), by_dec.values, width=8, color="#1f4e79")
    ax.set_xlabel("Geburtsjahrzent")
    ax.set_ylabel("Anzahl CHE-Personen")
    ax.set_title("Geburtsdatum-Abdeckung der CHE-Personen pro Jahrzent")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "birthday_coverage.png", dpi=120)
    plt.close(fig)


def figure_membership_types(memberships_che: pd.DataFrame):
    counts = memberships_che["type_harmonized_de"].value_counts()
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(counts.index[::-1], counts.values[::-1], color="#e07b3a")
    ax.set_xlabel("Anzahl Mitgliedschaften")
    ax.set_title("CHE-Mitgliedschaften nach Typ (type_harmonized_de)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "membership_types.png", dpi=120)
    plt.close(fig)


def figure_entry_age_distribution(politicians: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(politicians["entry_age"].dropna(), bins=40, color="#1f4e79", edgecolor="white")
    ax.set_xlabel("Eintrittsalter (Jahre)")
    ax.set_ylabel("Anzahl Personen")
    ax.set_title("Verteilung des Eintrittsalters über alle Bundespolitiker:innen (1850-2025)")
    plt.tight_layout()
    fig.savefig(FIG_DIR / "entry_age_distribution.png", dpi=120)
    plt.close(fig)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    persons_raw = pd.read_parquet(PROCESSED_DIR / "persons_clean.parquet")
    memberships_raw = pd.read_parquet(PROCESSED_DIR / "memberships_clean.parquet")
    persons_che = persons_raw[persons_raw["body_key"] == "CHE"].copy()
    memberships_che = memberships_raw[memberships_raw["body_key"] == "CHE"].copy()

    dump_catalogue("persons_clean_CHE", persons_che)
    dump_catalogue("memberships_clean_CHE", memberships_che)

    for name in ["politicians", "parliament_memberships", "parliament_yearly"]:
        df = pd.read_parquet(PROCESSED_DIR / f"{name}.parquet")
        dump_catalogue(name, df)

    figure_birthday_coverage_by_decade(persons_che)
    figure_membership_types(memberships_che)
    politicians = pd.read_parquet(PROCESSED_DIR / "politicians.parquet")
    figure_entry_age_distribution(politicians)

    logger.info(f"Done. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
