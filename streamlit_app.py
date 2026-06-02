from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from analytics import chip_suggestion
from visuals import (
    consistency_index,
    fixture_difficulty_analysis,
    graphics_selected_vs_points,
    graphics_value_vs_points,
    player_advice,
    show_player_stats,
    show_table,
    team_dependency_ratio,
)

# -------------------------------------------------------------------
# Page configuration
# -------------------------------------------------------------------
st.set_page_config(
    page_title="FPL Analyst – Fantasy Premier League Data Dashboard",
    page_icon="⚽",
    layout="wide",
)

# -------------------------------------------------------------------
# SEO / verification helpers
# Note: Streamlit renders this inside the app body, not the true HTML <head>.
# Google Search Console verification can still work if Google can read it.
# -------------------------------------------------------------------
st.markdown(
    """
    <meta name="google-site-verification" content="dxyOY9w3Zsj56zGnmVCWoqCRcRYQs7NzwHemkTxoNZo" />
    <meta name="description" content="FPL Analyst is a Fantasy Premier League analytics dashboard for player value, selection rate, team dependency ratio, fixture difficulty and consistency analysis." />
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# Global styling
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }

        .card {
            padding: 20px;
            margin: 15px 0;
            border-radius: 16px;
            background-color: #381769;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.12);
        }

        .app-intro {
            margin-top: 0.5rem;
            margin-bottom: 2rem;
            font-size: 1.05rem;
            line-height: 1.6;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_fpl_data():
    """Load core Fantasy Premier League bootstrap data."""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    return (
        pd.DataFrame(data["elements"]),
        pd.DataFrame(data["teams"]),
        data["events"],
    )


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
header_path = Path("assets/header.png")

if header_path.exists():
    st.image(str(header_path), use_container_width=True)
else:
    st.warning("Header image not found: assets/header.png")

st.title("FPL Analyst")
st.caption("Fantasy Premier League Analytics Dashboard")
st.markdown(
    """
    <div class="app-intro">
        FPL Analyst helps Fantasy Premier League managers analyze player value,
        selection trends, team dependency, fixture difficulty and consistency metrics.
    </div>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Data loading
# -------------------------------------------------------------------
try:
    players, teams, events = load_fpl_data()
except requests.RequestException as exc:
    st.error("FPL API data could not be loaded. Please try again later.")
    st.exception(exc)
    st.stop()


# -------------------------------------------------------------------
# Dashboard layout
# -------------------------------------------------------------------
rows = [st.columns(3) for _ in range(3)]

# Row 1
with rows[0][0]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        graphics_value_vs_points()
        st.markdown("</div>", unsafe_allow_html=True)

with rows[0][1]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        graphics_selected_vs_points(players)
        st.markdown("</div>", unsafe_allow_html=True)

with rows[0][2]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        player_advice(players, teams)
        st.markdown("</div>", unsafe_allow_html=True)

# Row 2
with rows[1][0]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        team_dependency_ratio(players, teams)
        st.markdown("</div>", unsafe_allow_html=True)

with rows[1][1]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        consistency_index(players)
        st.markdown("</div>", unsafe_allow_html=True)

with rows[1][2]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        show_table()
        st.markdown("</div>", unsafe_allow_html=True)

# Row 3
with rows[2][0]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        fixture_difficulty_analysis(teams, events)
        st.markdown("</div>", unsafe_allow_html=True)

with rows[2][1]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        chip_suggestion()
        st.markdown("</div>", unsafe_allow_html=True)

with rows[2][2]:
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        show_player_stats(players, teams)
        st.markdown("</div>", unsafe_allow_html=True)
