# VDSS Gruppe 4

Diese Projekt beantwortet die Hypothese "Politiker werden immer älter" für das Schweizer Bundesparlament zwischen 1850 und 2025, mit den offiziellen Personen- und Mitgliedschaftsdaten von [OpenParlData](https://openparldata.ch/).

## Live

- **Interaktives Dashboard:** [vdss.cboss.dev/streamlit](https://vdss.cboss.dev/streamlit)
- **Dokumentation:** [vdss.cboss.dev](https://vdss.cboss.dev) (Projekt Charta, Datenbericht, Visualisierungsdesign, Evaluation, Deployment)
- **Datenquelle:** [files.openparldata.ch/exports/](https://files.openparldata.ch/exports/) (NDJSON-Exporte)

## Schnellstart

```bash
uv sync
uv run python eda/1_gather_data.py
uv run python eda/2_etl_politicians.py
uv run python eda/3_eda.py
uv run streamlit run deployment/app.py
```

## Projektstruktur

| Phase | Ordner | Dokumentation |
|---|---|---|
| Projekt-Verständnis | `-` | `docs/project_charta.qmd` |
| Datenbeschaffung und EDA | `eda/` | `docs/data_report.qmd` |
| Visualisierungsdesign | `deployment/` (Streamlit-Code) | `docs/viz_design_report.qmd` |
| Evaluation | `-` | `docs/evaluation.qmd` |
| Deployment | `deployment/` (Dockerfile, app) | `docs/deployment.qmd` |

```
.
├── eda/                    # ETL- und EDA-Skripte (Phase 1 und 2)
│   ├── 1_gather_data.py    # Download und Parquet-Konvertierung
│   ├── 2_etl_politicians.py# Join Personen × Parlamentsmitgliedschaften
│   ├── 3_eda.py            # Datenkataloge und Sanity-Plots nach eda/output/
│   └── output/             # generierte Catalogues und Figuren
├── data/
│   ├── raw/                # NDJSON-Exporte (nicht versioniert)
│   └── processed/          # Parquet-Dateien (nicht versioniert)
├── deployment/
│   ├── app.py              # Streamlit-Dashboard
│   ├── Dockerfile          # Container für /streamlit-Pfad
│   └── requirements.txt    # Minimal-Subset für den Container
├── docs/                   # Quarto-Projekt, gerendert nach docs/build/
│   ├── _quarto.yml
│   ├── *.qmd               # sechs Dokumentationsseiten
│   ├── refs.bib            # IEEE-Bibliographie
│   └── ieee.csl
├── pyproject.toml
├── uv.lock
└── README.md
```

## Datensatz

Zwei OpenParlData-Exporte:

- `persons.ndjson` (~24'000 Einträge): biografische Daten aller je erfassten Mandatsträger:innen auf Bundes- und Kantonsebene.
- `memberships.ndjson` (~248'000 Einträge): Mitgliedschaften in Gremien (Räte, Kommissionen, Fraktionen, Parteien) mit Beginn- und Enddatum.

Nach Filterung auf Bundesebene (`body_key == "CHE"`), gültige Geburtsdaten und Parlamentssitze in Nationalrat oder Ständerat verbleiben **3'546 Bundespolitiker:innen** mit **5'399 Mandaten** über 175 Jahre.

Detaillierter Datenkatalog in `eda/output/catalogue_*.csv` oder rendert im [Datenbericht](https://vdss.cboss.dev/data_report.html).

## Reproduzierbarkeit

Die gesamte Pipeline ist deterministisch und reproduzierbar:

- Dependencies gepinnt via `uv.lock`.
- Rohdaten via `urllib.request` direkt von OpenParlData heruntergeladen; bei vorhandenen lokalen Dateien wird übersprungen.
- ETL-Skript filtert deterministisch und schreibt Parquet-Outputs nach `data/processed/`.
- Quarto-Dokumentation rendert mit `freeze: auto`; gecachte Resultate liegen in `docs/_freeze/`.
- GitHub Actions Workflow (`.github/workflows/publish.yml`) publiziert bei jedem Push auf `main`.

## Python-Umgebung mit uv

[uv installieren](https://docs.astral.sh/uv/getting-started/installation/), dann:

```bash
uv sync
uv run python <script.py>
```

## Quarto-Dokumentation

```bash
uv run quarto preview docs    # lokale Vorschau mit Hot Reload
uv run quarto render docs     # Build nach docs/build/
```

Die rendering-Logik nutzt eingebettete `{python}`-Codeblöcke (siehe `data_report.qmd`), die Datenkataloge und Visualisierungen zur Render-Zeit aus den Parquets erzeugen. `freeze: auto` sorgt dafür, dass GitHub Actions ohne Python-Setup deployen kann.

## Team

- **Christian Bosshard** (boschr02@students.zhaw.ch)
- **Enea D. Fedel** (fedelene@students.zhaw.ch)

Begleitung: **Manuel Dömer** (technisch), **Wibke Weber** (visuelle Kommunikation).
