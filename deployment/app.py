import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# In Docker the build copies data/processed/ to /app/data/processed/ and sets VDSS_DATA_DIR
# for local development the relative path resolves correctly.
DATA_DIR = Path(os.environ.get("VDSS_DATA_DIR", Path(__file__).parent.parent / "data" / "processed"))

CHAMBER_COLORS = {"Nationalrat": "#1f4e79", "Ständerat": "#e07b3a"}
PARTY_COLORS = {
    "SVP": "#2E8B57",
    "SP": "#D62728",
    "FDP": "#1F77B4",
    "CVP / Mitte": "#FF8C00",
    "Grüne": "#6A8C2C",
    "GLP": "#9ACD32",
}

st.set_page_config(
    page_title="Werden Schweizer Bundespolitiker:innen immer älter?",
    layout="wide",
)

# load data
@st.cache_data
def load_politicians():
    return pd.read_parquet(DATA_DIR / "politicians.parquet")

@st.cache_data
def load_memberships():
    return pd.read_parquet(DATA_DIR / "parliament_memberships.parquet")

@st.cache_data
def load_yearly():
    return pd.read_parquet(DATA_DIR / "parliament_yearly.parquet")

@st.cache_data
def yearly_chamber_stats():
    y = load_yearly()
    out = (
        y.groupby(["year", "chamber"])["age"]
        .agg(median="median", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75), n="count")
        .reset_index()
    )
    return out


# Pages
def headline_page():
    st.title("Werden Bundespolitiker:innen immer älter?")
    st.markdown(
        "**Die Alltagsthese:** Das Schweizer Parlament wird zunehmend von älteren Personen dominiert. (NR = Nationalrat, SR = Ständerat)"
    )
    st.markdown("**Stimmt das?** Wir prüfen die These mit den Daten der Bundesversammlung von 1850 bis 2025.")

    y = load_yearly()
    stats = yearly_chamber_stats()

    # ── Headline metrics ──────────────────────────────────────────────────────
    latest_year = int(stats["year"].max())
    peak_decade_nr = (
        stats[stats["chamber"] == "Nationalrat"]
        .assign(decade=lambda d: (d["year"] // 10) * 10)
        .groupby("decade")["median"]
        .mean()
        .idxmax()
    )
    cur_nr = stats[(stats["year"] == latest_year) & (stats["chamber"] == "Nationalrat")]["median"].iloc[0]
    cur_sr = stats[(stats["year"] == latest_year) & (stats["chamber"] == "Ständerat")]["median"].iloc[0]
    decade_2020 = stats[(stats["year"] >= 2020) & (stats["chamber"] == "Nationalrat")]["median"].mean()
    decade_1950 = stats[(stats["year"] >= 1950) & (stats["year"] < 1960) & (stats["chamber"] == "Nationalrat")]["median"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"NR-Median {latest_year}", f"{cur_nr:.1f} J.")
    c2.metric(f"SR-Median {latest_year}", f"{cur_sr:.1f} J.")
    c3.metric("Peak-Jahrzent NR-Alterung", f"{peak_decade_nr}er")
    c4.metric("NR 2020er vs. 1950er", f"−{decade_1950 - decade_2020:.1f} J.", delta_color="inverse")

    # main chart
    st.subheader("Median-Alter der Bundesversammlung (1850–2025)")
    fig = go.Figure()
    for chamber, color in CHAMBER_COLORS.items():
        d = stats[stats["chamber"] == chamber].sort_values("year")
        # Percentile band
        fig.add_trace(go.Scatter(
            x=list(d["year"]) + list(d["year"][::-1]),
            y=list(d["q75"]) + list(d["q25"][::-1]),
            fill="toself",
            fillcolor=color,
            opacity=0.15,
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
            name=f"{chamber} 25-75 %",
        ))
        # Median line
        fig.add_trace(go.Scatter(
            x=d["year"], y=d["median"],
            mode="lines",
            name=f"{chamber} (Median)",
            line=dict(color=color, width=2.5),
            hovertemplate="%{x}: <b>%{y:.1f}</b> Jahre<extra>" + chamber + "</extra>",
        ))
    fig.update_layout(
        height=520,
        xaxis_title="Jahr",
        yaxis_title="Alter (Jahre)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(range=[35, 70])
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        f"""
**Befund:** Die Alltagsthese stimmt **nicht**, zumindest nicht für den Nationalrat.

- Der NR-Median erreichte seinen **Höhepunkt in den 1950er-Jahren** ({decade_1950:.1f} Jahre).
- Heute liegt er bei **{cur_nr:.1f} Jahren**, so tief wie seit über 100 Jahren nicht mehr.
- Der **Ständerat** ist konstant älter geblieben (~{cur_sr:.0f} Jahre) und der Abstand zum Nationalrat hat sich sogar vergrössert.
- Die wahre Alterung passierte im **19. Jahrhundert**: 1850 war der Nationalrat im Median 44 Jahre alt.

Die Erzählung "Politiker werden immer älter" ist also ein **gefühlter Trend**, kein gemessener.
"""
    )


def decomposition_page():
    st.title("Aufschlüsselung: Wer wird älter, oder eben nicht?")
    st.markdown(
        "Wenn der Trend nicht global ist, lohnt sich der Blick auf Teilgruppen: "
        "**Partei** und **Geschlecht**."
    )

    y = load_yearly()

    st.subheader("Median-Alter pro Partei über Zeit")

    PARTY_DISPLAY = {
        "Schweizerische Volkspartei": "SVP",
        "Sozialdemokratische Partei": "SP",
        "FDP.Die Liberalen": "FDP",
        "Christlichdemokratische Volkspartei der Schweiz": "CVP / Mitte",
        "Die Mitte": "CVP / Mitte",
        "Die Grünen": "Grüne",
        "Grünliberale Partei": "GLP",
    }
    MIN_MEMBERS_PER_YEAR = 5  # remove noisy single-digit medians

    party_data = y.dropna(subset=["party_harmonized_de"]).copy()
    party_data["Partei"] = party_data["party_harmonized_de"].map(PARTY_DISPLAY)
    party_data = party_data.dropna(subset=["Partei"])

    party_med = (
        party_data.groupby(["year", "Partei"])
        .agg(median_age=("age", "median"), n=("age", "size"))
        .reset_index()
    )
    party_med = party_med[party_med["n"] >= MIN_MEMBERS_PER_YEAR]
    party_med["Median-Alter"] = (
        party_med.sort_values("year")
        .groupby("Partei")["median_age"]
        .transform(lambda s: s.rolling(5, min_periods=1, center=True).mean())
    )

    party_order = ["SVP", "SP", "FDP", "CVP / Mitte", "Grüne", "GLP"]
    fig_party = px.line(
        party_med,
        x="year",
        y="Median-Alter",
        color="Partei",
        category_orders={"Partei": party_order},
        color_discrete_map=PARTY_COLORS,
        title="Median-Alter pro Partei (5-Jahre-Glättung)",
        labels={"year": "Jahr"},
    )
    fig_party.update_traces(line=dict(width=2.2))
    fig_party.update_layout(height=460, hovermode="x unified")
    fig_party.update_yaxes(range=[40, 65])

    st.plotly_chart(fig_party, use_container_width=True)

    st.markdown(
        "**Beobachtung:** Die sechs heute relevanten Parteien liegen meist zwischen "
        "50 und 60 Jahren. Grüne (seit 1979) und GLP (seit 2007) sind die jüngsten "
        "Fraktionen und drücken den Gesamtmedian nach unten."
    )

    # Gender
    st.subheader("Median-Alter nach Geschlecht (ab Einführung Frauenstimmrecht 1971)")
    g = y[y["gender"].isin(["m", "f"]) & (y["year"] >= 1971)].copy()
    g["Geschlecht"] = g["gender"].map({"m": "Männer", "f": "Frauen"})
    gender_med = (
        g.groupby(["year", "Geschlecht"])["age"]
        .median()
        .reset_index()
        .rename(columns={"age": "Median-Alter"})
    )

    fig_gender = px.line(
        gender_med,
        x="year",
        y="Median-Alter",
        color="Geschlecht",
        title="Median-Alter Männer vs. Frauen (NR + SR)",
        labels={"year": "Jahr"},
        color_discrete_map={"Männer": "#1f77b4", "Frauen": "#e377c2"},
    )

    fig_gender.update_layout(height=420, hovermode="x unified")
    fig_gender.update_yaxes(range=[35, 70])

    st.plotly_chart(fig_gender, use_container_width=True)

    st.markdown(
        "**Beobachtung:** Die Frauen, die seit 1971 ins Bundesparlament eintreten, "
        "sind im Schnitt etwas jünger als ihre männlichen Kolleg:innen. Der "
        "Abstand hat sich aber im Lauf der Zeit verkleinert."
    )


def mechanism_page():
    st.title("Mechanismus: Eintrittsalter vs. Amtsdauer")
    st.markdown(
        "Wenn sich das Median-Alter im Parlament ändert, kann das zwei Gründe haben: "
        "Leute steigen **jünger ein**, oder sie **bleiben länger**. "
        "Welcher Mechanismus wirkt in der Schweiz?"
    )

    p = load_politicians()
    p = p.copy()
    p["first_entry_year"] = pd.to_datetime(p["first_entry_date"]).dt.year
    p["entry_decade"] = (p["first_entry_year"] // 10) * 10

    # entry age
    st.subheader("Eintrittsalter pro Eintrittsjahrzent")
    by_decade = p[p["entry_decade"] >= 1880].copy()
    fig_entry = px.box(
        by_decade,
        x="entry_decade",
        y="entry_age",
        title="Verteilung des Eintrittsalters in der Bundesversammlung",
        labels={"entry_decade": "Jahrzent des ersten Eintritts", "entry_age": "Eintrittsalter"},
        color_discrete_sequence=["#1f4e79"],
    )

    fig_entry.update_layout(height=440, showlegend=False)
    fig_entry.update_yaxes(range=[20, 80])

    st.plotly_chart(fig_entry, use_container_width=True)

    median_entry = by_decade.groupby("entry_decade")["entry_age"].median().round(1)
    st.markdown(
        f"**Befund:** Das Eintrittsalter ist seit 1880 erstaunlich **stabil bei {median_entry.min():.0f}-{median_entry.max():.0f} Jahren**. "
        "Politiker:innen steigen heute nicht später ein als vor 100 Jahren."
    )

    # tenure
    st.subheader("Wie lange bleiben Parlamentarier:innen?")
    p_done = p[~p["currently_active"]].copy()
    fig_tenure = px.histogram(
        p_done,
        x="total_tenure_years",
        nbins=40,
        title="Verteilung der Gesamt-Mandatsdauer (abgeschlossene Karrieren)",
        labels={"total_tenure_years": "Mandatsdauer (Jahre)", "count": "Anzahl Personen"},
        color_discrete_sequence=["#e07b3a"],
    )

    fig_tenure.update_layout(height=400, showlegend=False, yaxis_title="Anzahl Personen")

    st.plotly_chart(fig_tenure, use_container_width=True)

    tenure_median = p_done["total_tenure_years"].median()
    tenure_p90 = p_done["total_tenure_years"].quantile(0.9)
    st.markdown(
        f"**Befund:** Die mediane Mandatsdauer beträgt **{tenure_median:.1f} Jahre**, "
        f"die obersten 10 % bleiben über **{tenure_p90:.1f} Jahre**. "
        "Die Verteilung ist rechtsschief; ganz wenige Politiker:innen amtieren extrem lange."
    )

    # tenure by decade
    st.subheader("Mandatsdauer im Verlauf des Eintrittsjahrzents")
    tenure_by_dec = p_done[p_done["entry_decade"] >= 1880].copy()
    tenure_med_dec = (
        tenure_by_dec.groupby("entry_decade")["total_tenure_years"]
        .agg(median="median", n="count")
        .reset_index()
    )
    fig_t = px.bar(
        tenure_med_dec,
        x="entry_decade",
        y="median",
        title="Mediane Mandatsdauer nach Eintrittsjahrzehnt",
        labels={"entry_decade": "Jahrzent des Eintritts", "median": "Mediane Mandatsdauer (Jahre)"},
        color_discrete_sequence=["#666"],
    )
    fig_t.update_layout(height=380)
    st.plotly_chart(fig_t, use_container_width=True)

    st.markdown(
        "**Befund:** Die Mandatsdauer schwankt zwischen den Jahrzehnten um die "
        "8-12 Jahre, ohne klaren langfristigen Trend nach oben oder unten. "
        "Auch hier: kein Hinweis darauf, dass Politiker:innen heute systematisch länger bleiben."
    )


def stories_page():
    st.title("Personen: Die Extreme")
    st.markdown("Statistiken werden konkreter, wenn man die Personen hinter den Zahlen kennt.")

    p = load_politicians()
    p = p.copy()
    p["name"] = (p["firstname"].fillna("") + " " + p["lastname"].fillna("")).str.strip()
    p["first_entry_year"] = pd.to_datetime(p["first_entry_date"]).dt.year

    # ── Top lists ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Jüngste je Gewählte")
        youngest = p.nsmallest(10, "entry_age")[["name", "party_de", "entry_age", "first_entry_year"]]
        youngest = youngest.rename(columns={
            "name": "Name", "party_de": "Partei",
            "entry_age": "Alter b. Eintritt", "first_entry_year": "Jahr",
        })
        youngest["Alter b. Eintritt"] = youngest["Alter b. Eintritt"].round(1)
        st.dataframe(youngest, hide_index=True, use_container_width=True)

    with col2:
        st.subheader("Älteste je Gewählte")
        oldest = p.nlargest(10, "entry_age")[["name", "party_de", "entry_age", "first_entry_year"]]
        oldest = oldest.rename(columns={
            "name": "Name", "party_de": "Partei",
            "entry_age": "Alter b. Eintritt", "first_entry_year": "Jahr",
        })
        oldest["Alter b. Eintritt"] = oldest["Alter b. Eintritt"].round(1)
        st.dataframe(oldest, hide_index=True, use_container_width=True)

    with col3:
        st.subheader("Längste Karrieren")
        longest = p.nlargest(10, "total_tenure_years")[["name", "party_de", "total_tenure_years", "first_entry_year"]]
        longest = longest.rename(columns={
            "name": "Name", "party_de": "Partei",
            "total_tenure_years": "Dauer (J.)", "first_entry_year": "Eintritt",
        })
        longest["Dauer (J.)"] = longest["Dauer (J.)"].round(1)
        st.dataframe(longest, hide_index=True, use_container_width=True)

    # current parliament age
    st.subheader("Wie alt ist das heutige Bundesparlament?")
    active = p[p["currently_active"]].copy()
    RAW_TO_DISPLAY = {
        "SVP": "SVP", "SP": "SP",
        "FDP-Liberale": "FDP", "FDP": "FDP",
        "M-E": "CVP / Mitte", "Die Mitte": "CVP / Mitte",
        "GRÜNE": "Grüne", "glp": "GLP",
    }
    active["Partei"] = active["party_de"].map(RAW_TO_DISPLAY).fillna("Andere")
    color_map = {**PARTY_COLORS, "Andere": "#999999"}
    fig = px.histogram(
        active,
        x="age_today",
        color="Partei",
        category_orders={"Partei": list(PARTY_COLORS.keys()) + ["Andere"]},
        color_discrete_map=color_map,
        nbins=25,
        title=f"Altersverteilung der aktiven Mandatsträger:innen (n = {len(active)})",
        labels={"age_today": "Alter heute (Jahre)"},
    )
    fig.update_layout(height=440, bargap=0.05)
    st.plotly_chart(fig, use_container_width=True)

    median_today = active["age_today"].median()
    st.markdown(
        f"**Median-Alter der aktiven Bundesversammlung heute: {median_today:.1f} Jahre.** "
        f"Die Verteilung reicht von **{active['age_today'].min():.0f}** "
        f"bis **{active['age_today'].max():.0f}** Jahren."
    )


# navigation
p_headline = st.Page(headline_page, title="Headline", default=True)
p_decomp = st.Page(decomposition_page, title="Aufschlüsselung")
p_mech = st.Page(mechanism_page, title="Mechanismus")
p_stories = st.Page(stories_page, title="Personen")

nav = st.navigation([p_headline, p_decomp, p_mech, p_stories], position="hidden")

with st.sidebar:
    st.markdown("### Werden Bundespolitiker:innen älter?")
    st.page_link(p_headline, label="1. Headline")
    st.page_link(p_decomp, label="2. Aufschlüsselung")
    st.page_link(p_mech, label="3. Mechanismus")
    st.page_link(p_stories, label="4. Personen")
    st.divider()
    st.page_link("https://vdss.cboss.dev/", label="Dokumentation")
    st.caption("Daten: OpenParlData.ch · Stand Mai 2026")

nav.run()
