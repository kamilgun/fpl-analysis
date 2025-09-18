import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import ast

# Get data from FPL API
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()

# Export data to DataFrame
players = pd.DataFrame(data['elements'])
teams = pd.DataFrame(data['teams'])

def grafik_selected_vs_points(players):

    # convert column to float
    players['selected_by_percent'] = pd.to_numeric(players['selected_by_percent'], errors='coerce')

    st.title("Player Selection Rate vs Total Points")
    st.markdown("Displaying players based on their selection rates. You can examine less-preferred players with good ratings or more-preferred players with ineffective scores")

    # Get filter from user
    min_sel = st.slider("Min selection rate (%)", 0.0, 100.0, 3.0)
    max_sel = st.slider("Max selection rate (%)", 0.0, 100.0, 10.0)

    # Filter
    filtered = players[
        (players['selected_by_percent'] >= min_sel) &
        (players['selected_by_percent'] <= max_sel) &
        (players['total_points'] > 0)
    ]

    # Create Graphics
    fig, ax = plt.subplots()
    ax.scatter(filtered['selected_by_percent'], filtered['total_points'])

    # Name the spots
    for i, row in filtered.iterrows():
        ax.text(row['selected_by_percent'], row['total_points'], row['web_name'], fontsize=8)

    ax.set_xlabel('Selection Rate (%)')
    ax.set_ylabel('Total Points')
    ax.set_title('Selection Rate vs Total Points')

    # Publish to streamlit
    st.pyplot(fig)

def grafik_value_vs_points():
    
    df = pd.read_csv("./player_stats.csv")

    st.title("FPL Efficiency Analysis")
    st.markdown("Examining players with the highest ratings relative to their value")

    # Pozisyon seçimi
    pozisyonlar = ["All Players"] + sorted(df["Position"].unique())
    secilen_pozisyon = st.selectbox("Filter by Position", pozisyonlar)

    if secilen_pozisyon != "All Players":
        df = df[df["Position"] == secilen_pozisyon]

    # Verimlilik hesapla (puan / değer)
    df["point_per_value"] = df["Points/Value"]

    # En verimli oyuncuları sırala
    df = df.sort_values("point_per_value", ascending=False)

    # st.dataframe(df[["Player", "Team", "Position", "Value", "Points", "value_ratio"]].head(120).reset_index(drop=True).rename_axis("Sıra").reset_index())

    # 📋 Tablo
    st.dataframe(
        df[["Player", "Team", "Position", "Value", "Points", "value_ratio"]].head(120)
        .sort_values("value_ratio", ascending=False)
        .reset_index(drop=True),
        height=600
    )  

def player_advice(players):
    st.title("Scout Assisant - Adviced Players")
    
    cost_limit = st.slider("Maximum Player Value", 4.0, 12.5, 8.5)
    position = st.selectbox("Position", ["All", "Goalkeeper", "Defence", "Midfielder", "Forward"])
    min_minutes = st.slider("Minimum minutes played", 0, 3000, 200)
    min_points = st.slider("Minimum points", 0, 250, 20)
    sel_range = st.slider("Selection Rate (%)", 0.0, 100.0, (5.0, 25.0))

    # Pozisyon dönüşümü için eşleştirme sözlüğü
    position_map = {
        1: "Goalkeeper",
        2: "Defence",
        3: "Midfielder",
        4: "Forward"
    }

    # now_cost 10x formatından float'a çevriliyor
    players["cost_million"] = players["now_cost"] / 10

    # Pozisyon adı ekleniyor
    players["position_name"] = players["element_type"].map(position_map)

    # Seçilme oranı string olarak geliyorsa float'a çevir
    players["selected_by_percent"] = players["selected_by_percent"].astype(float)

    # Filtreleme işlemi
    filtered_players = players[
        (players["cost_million"] <= cost_limit) &
        (players["minutes"] >= min_minutes) &
        (players["total_points"] >= min_points) &
        (players["selected_by_percent"] >= sel_range[0]) &
        (players["selected_by_percent"] <= sel_range[1]) 
    ]
    
    # Pozisyon filtresi (eğer "Tümü" değilse)
    if position != "All":
        filtered_players = filtered_players[filtered_players["position_name"] == position]

    # Verimlilik oranı hesaplama ve sıralama
    filtered_players["value_ratio"] = filtered_players["total_points"] / filtered_players["cost_million"]
    filtered_players = filtered_players.sort_values("value_ratio", ascending=False)

    # Kolonları seçerek göster
    
    #st.dataframe(filtered_players[["web_name", "team", "position_name", "cost_million", "total_points", "selected_by_percent", "value_ratio"]].reset_index(drop=True).rename_axis("Sıra").reset_index())

    # 📋 Tablo
    st.dataframe(
        filtered_players[["web_name", "team", "position_name", "cost_million", "total_points", "selected_by_percent", "value_ratio"]]
        .sort_values("value_ratio", ascending=False)
        .reset_index(drop=True)
    )

def team_dependency_ratio():
    # 🏃‍♂️ Oyuncu katkısı
    players["contribution"] = players["goals_scored"] + players["assists"]

    # 🏟️ Takım toplam gollerini hesapla
    team_goals = players.groupby("team")["goals_scored"].sum().reset_index()
    team_goals.rename(columns={"goals_scored": "team_total_goals", "team": "team_id"}, inplace=True)

    # Merge et: players + teams + team_goals
    merged = players.merge(teams[["id", "name", "short_name"]], left_on="team", right_on="id", how="left")
    merged = merged.merge(team_goals, left_on="team", right_on="team_id", how="left")

    # 🔧 TDR hesaplama
    merged["TDR"] = merged["contribution"] / merged["team_total_goals"]

    st.title("Team Dependency Ratio (TDR) Analysis")
    st.markdown("The player who contributed the most points to each team is listed in this panel.")

    
    team_leaders = (
        merged.sort_values("TDR", ascending=False)
        .drop_duplicates(subset=["team"])   # her takım için en yüksek TDR’li oyuncu kalır
        .reset_index(drop=True)
    )

    # -----------------------------
    # 📊 Görselleştirme
    chart = (
        alt.Chart(team_leaders)
        .mark_bar()
        .encode(
            x=alt.X("short_name:N", title="Team"),
            y=alt.Y("TDR:Q", axis=alt.Axis(format="%"), title="Team Dependency Ratio"),
            color="name:N",
            tooltip=["first_name", "second_name", "name", "goals_scored", "assists", "contribution", "team_total_goals", alt.Tooltip("TDR", format=".0%")]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # -----------------------------
    # 📋 Tablo
    st.dataframe(
        team_leaders[["first_name", "second_name", "name", "goals_scored", "assists", "contribution", "team_total_goals", "TDR"]]
        .sort_values("TDR", ascending=False)
        .reset_index(drop=True)
    )          
   
def consistency_index():
    history_df = pd.read_csv("./weekly_exec/weekly_points.csv")

    consistency = (
        history_df.groupby("player_id")["total_points"]
        .agg(["mean", "std"])
        .reset_index()
    )

    # 4. İstikrar skoru
    consistency["consistency_index"] = consistency["mean"] / consistency["std"].replace(0, 1)

    st.title("Consistency Index Analysis")
    st.markdown("Examining a player's weekly points distribution to show how stable or surprising their profile is.")

    consistency = consistency.merge(
    players[["id", "first_name", "second_name", "team", "web_name", "total_points"]],
    left_on="player_id", right_on="id", how="left"
    )

    max_point = history_df["total_points"].max()

    consistency = consistency[consistency["total_points"] > max_point/3]

    consistency = consistency.dropna(subset=["consistency_index"])

    # -----------------------------
    # 6. Scatterplot
    chart = (
        alt.Chart(consistency)
        .mark_circle(size=60)
        .encode(
            x=alt.X("mean:Q", title="Average Points"),
            y=alt.Y("std:Q", title="Standard Deviation"),
            color="team:N",
            #tooltip=["web_name", "total_points", "mean", "std", "consistency_index"]
            tooltip=[
            alt.Tooltip("web_name:N", title="Player"),
            alt.Tooltip("total_points:Q", title="Points"),
            alt.Tooltip("mean:Q", format=".2f"),
            alt.Tooltip("std:Q", format=".2f"),
            alt.Tooltip("consistency_index:Q", format=".2f")
        ]
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # -----------------------------
    # 7. Tablo
    st.dataframe(
        consistency[["first_name", "second_name", "total_points", "mean", "std", "consistency_index"]]
        .sort_values("consistency_index", ascending=False)
        .reset_index(drop=True)
        .style.format({
          "mean": "{:.2f}",
          "std": "{:.2f}",
          "consistency_index": "{:.2f}"
      })
    )

def read_pl_table(csv_path="./league_table.csv"):
    df = pd.read_csv(csv_path)

    # team kolonunu dict'e çevir
    df["team"] = df["team"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
    df["team_name"] = df["team"].apply(lambda t: t.get("name") if isinstance(t, dict) else t)
    df["short_name"] = df["team"].apply(lambda t: t.get("shortName") if isinstance(t, dict) else t)

    standings = df[[
        "position", "team_name", "playedGames", "won", "draw", "lost", 
        "goalsFor", "goalsAgainst", "goalDifference", "points"
    ]].sort_values("position").reset_index(drop=True)
    return standings

import textwrap
def render_standings_html(df: pd.DataFrame) -> str:
    html = textwrap.dedent("""\
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');

    table.pl-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        font-family: 'Roboto', sans-serif;
    }
    table.pl-table th {
        background-color: #222;
        color: #fff;
        padding: 6px;
        text-align: center;
        font-weight: 500;
    }
    table.pl-table td {
        border-bottom: 1px solid #ddd;
        padding: 6px;
        text-align: center;
    }
    /* Points: yeşil */
    table.pl-table td.points { font-weight: 700; color: #1a7f37; }
    /* Goal Difference: pozitif yeşil, negatif kırmızı */
    table.pl-table td.gd-pos { color: #1a7f37; }
    table.pl-table td.gd-neg { color: #d73a49; }
    </style>
    <table class="pl-table">
      <thead>
        <tr>
          <th>Pos</th><th>Team</th><th>Pld</th><th>W</th><th>D</th><th>L</th>
          <th>GF</th><th>GA</th><th>GD</th><th>Pts</th>
        </tr>
      </thead>
      <tbody>
    """)
    for _, row in df.iterrows():
        gd_class = "gd-pos" if row["goalDifference"] >= 0 else "gd-neg"
        html += f"""
        <tr>
          <td>{row['position']}</td>
          <td style="text-align:left">{row['team_name']}</td>
          <td>{row['playedGames']}</td>
          <td>{row['won']}</td>
          <td>{row['draw']}</td>
          <td>{row['lost']}</td>
          <td>{row['goalsFor']}</td>
          <td>{row['goalsAgainst']}</td>
          <td class="{gd_class}">{row['goalDifference']}</td>
          <td class="points">{row['points']}</td>
        </tr>
        """
    html += "</tbody></table>"
    return html

import streamlit.components.v1 as components

def show_table():
    st.title("🏆 Premier League Table")
    standings = read_pl_table("./league_table.csv")
    html = render_standings_html(standings)   # burada dedent kullanmak iyi olur yine
    components.html(html, height=950, scrolling=True)

@st.cache_data
def load_fixtures():
    url = "https://fantasy.premierleague.com/api/fixtures/"
    r = requests.get(url)
    return r.json()

@st.cache_data
def load_teams():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    r = requests.get(url).json()
    teams = pd.DataFrame(r["teams"])
    return teams[["id", "name", "short_name", "code"]], r["events"]

def build_fixture_difficulty(fixtures, teams, events, gameweeks=5):
    # Sadece önümüzdeki X haftayı al
    current_gw = next(e["id"] for e in events if e["is_current"]) + 1

    upcoming = [f for f in fixtures if f["event"] and current_gw <= f["event"] < current_gw+gameweeks]

    # Home ve Away ayrı ayrı işleniyor
    data = []
    for f in upcoming:
        # Ev sahibi
        data.append({
            "team": f["team_h"],
            "opponent": f["team_a"],
            "gw": f["event"],
            "difficulty": f["team_h_difficulty"],
            "venue": "H"
        })
        # Deplasman
        data.append({
            "team": f["team_a"],
            "opponent": f["team_h"],
            "gw": f["event"],
            "difficulty": f["team_a_difficulty"],
            "venue": "A"
        })

    df = pd.DataFrame(data)
    df = df.merge(teams, left_on="team", right_on="id").drop("id", axis=1)
    df = df.merge(teams, left_on="opponent", right_on="id", suffixes=("", "_opp")).drop("id", axis=1)

    # Takım başına ortalama difficulty
    avg_df = df.groupby("name").agg({"difficulty":"mean"}).reset_index().sort_values("difficulty")
    avg_df.rename(columns={"difficulty":"Avg Difficulty (next %d GWs)" % gameweeks}, inplace=True)

    return avg_df, df

def fixture_difficulty_analysis():
    st.title("📊 Fixture Difficulty Analysis")

    fixtures = load_fixtures()
    teams, events = load_teams()

    avg_df, fixture_df = build_fixture_difficulty(fixtures, teams, events, gameweeks=5)

    st.write("### Average FDR (Next 5 Games)")
    
    #st.dataframe(avg_df, use_container_width=True)
    styled_avg = avg_df.style.background_gradient(
        cmap="RdYlGn_r", subset=["Avg Difficulty (next 5 GWs)"]
    ).format({"Avg Difficulty (next 5 GWs)": "{:.2f}"})

    st.dataframe(styled_avg, use_container_width=True)

        # Detaylı tablo (rakip adı + difficulty)
    st.write("### Fixture Difficulty Detailed")
    fixture_df["opp_info"] = fixture_df["short_name_opp"] + " (" + fixture_df["difficulty"].astype(str) + ")"
    pivot = fixture_df.pivot_table(index="name", columns="gw", values="opp_info", aggfunc="first")
    st.dataframe(pivot, use_container_width=True)

def show_player_stats():
    st.title("📊 Player Statistics – Dynamic Ranking")
    
    # Kullanıcıya seçim imkanı
    metrics = ["Select"] + ["total_points", "now_cost", "minutes", "goals_scored", "assists", "ict_index"]
    metric_choice = st.selectbox("Sıralama ölçütü seç:", metrics, index=0) 

    order_choice = st.radio("Sıralama yönü:", ["Azalan", "Artan"])
    ascending = True if order_choice == "Artan" else False

    merged_players = players.merge(teams[["id", "name"]], left_on="team", right_on="id", how="left")

    # Sıralı tablo
    if metric_choice:
        sorted_df = merged_players.sort_values(metric_choice, ascending=ascending)
        st.dataframe(sorted_df[["first_name", "second_name", "name", metric_choice]].head(50), height=600)    