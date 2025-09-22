import streamlit as st
import requests
import pandas as pd
from visuals import (
    graphics_selected_vs_points,
    player_advice,
    graphics_value_vs_points,
    team_dependency_ratio,
    consistency_index,
    show_table,
    fixture_difficulty_analysis,
    show_player_stats
)
from analytics import chip_suggestion

# --- Page config ---
st.set_page_config(
    page_title="FPL Analysis Dashboard",
    page_icon="⚽",
    layout="wide"
)

# --- Sidebar ---
st.sidebar.title("⚽ Navigation")

page = st.sidebar.radio(
    "Go to:",
    [
        "🏠 Home",
        "📊 Player Analysis",
        "🛠 Scout Tools",
        "📅 Fixture Tools"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("🚀 Quick Start")
st.sidebar.markdown(
    """
    1. **Scout Tools** → Oyuncu önerilerini incele  
    2. **Player Analysis** → Fiyat/performans analizine bak  
    3. **Fixture Tools** → Fikstür zorluklarına göre plan yap  
    """
)

st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ using Streamlit")

# --- Data ---
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()

players = pd.DataFrame(data["elements"])
teams = pd.DataFrame(data["teams"])

# --- Global CSS ---
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }

        .box {
            padding: 20px;
            margin: 15px;
            border-radius: 16px;
            background-color: #ffffff;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        }

        .custom-divider {
            border-top: 2px solid #6c757d;
            margin: 20px 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Main content ---
if page == "🏠 Home":
    st.markdown(
        """
        <div style="text-align:center; margin-bottom:20px;">
            <img src="https://fantasy.premierleague.com/static/media/shared/branding/fpl-logo--darkbg.abc123.png" 
                 style="max-width: 80%; height: auto;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.title("Welcome to the FPL Analysis Dashboard ⚡")
    st.markdown(
        """
        Explore different analyses, scout tools, and fixture-based strategies  
        to improve your Fantasy Premier League decisions.
        """
    )

elif page == "📊 Player Analysis":
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        graphics_value_vs_points()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        graphics_selected_vs_points(players)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        consistency_index()
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "🛠 Scout Tools":
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        player_advice(players)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="box">', unsafe_allow_html=True)
        chip_suggestion()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        team_dependency_ratio()
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "📅 Fixture Tools":
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        fixture_difficulty_analysis()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="box">', unsafe_allow_html=True)
        show_table()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="box">', unsafe_allow_html=True)
    show_player_stats()
    st.markdown('</div>', unsafe_allow_html=True)
