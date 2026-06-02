import streamlit as st
import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import ast
from paths import DATA_DIR
import time
from functools import wraps

@st.cache_data
def _read_csv_cached(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_csv(path)

def load_csv(path) -> pd.DataFrame:
    # path: str veya Path olabilir
    path_str = str(path)
    return _read_csv_cached(path_str, os.path.getmtime(path_str))

# def timed(name: str):
#     def decorator(fn):
#         @wraps(fn)
#         def wrapper(*args, **kwargs):
#             start = time.perf_counter()
#             result = fn(*args, **kwargs)
#             duration = time.perf_counter() - start
#             st.caption(f"⏱️ {name}: {duration:.2f} s")
#             return result
#         return wrapper
#     return decorator

# @timed("graphics_selected_vs_points")
def graphics_selected_vs_points(players):

    ply = players.copy()
    # convert column to float
    ply['selected_by_percent'] = pd.to_numeric(players['selected_by_percent'], errors='coerce')

    st.title("👥 Selection Rate vs Total Points")
    st.markdown("Displaying players based on their selection rates. You can examine less-preferred players with good ratings or more-preferred players with ineffective scores.")
    st.markdown("Y-Axis: Total Points | X-Axis: Selection Rate (%)")

    # Get filter from user
    min_sel = st.slider("Min selection rate (%)", 0.0, 100.0, 3.0)
    max_sel = st.slider("Max selection rate (%)", 0.0, 100.0, 10.0)
   
  
    # Filter
    filtered = ply[
        (ply['selected_by_percent'] >= min_sel) &
        (ply['selected_by_percent'] <= max_sel) &
        (ply['total_points'] > 0)
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

# @timed("graphics_value_vs_points")
def graphics_value_vs_points():
    
    #df = pd.read_csv("./player_stats.csv")
    # df  = pd.read_csv(DATA_DIR / "player_stats.csv")
    df = load_csv(DATA_DIR / "player_stats.csv")

    st.title("📈 FPL Efficiency Analysis")
    st.markdown("Examining players with the highest ratings relative to their value. Of course, everyone knows about Salah or Haaland")
    st.markdown("Here are some budget-friendly players who bring in high scores despite their low cost")

    # Position selection
    # pozisyonlar = ["All Players"] + sorted(df["Position"].unique())
    # secilen_pozisyon = st.selectbox("Filter by Position", pozisyonlar)

    # Futbol mantığına uygun manuel sıralama
    position_order = [
        "All Players",
        "Goalkeeper",
        "Defender",
        "Midfielder",
        "Forward",
    ]

    selected_position = st.selectbox(
        "Filter by Position",
        options=position_order,
        index=0  # default: All Players
    )

    if selected_position != "All Players": 
        df = df[df["Position"] == selected_position]

    # Calculate efficiency (points / value)
    df["point_per_value"] = df["Points/Value"]

    # Sort by efficiency
    df = df.sort_values("point_per_value", ascending=False)    

    """ # 📋 Table
    st.dataframe(
        df[["Player", "Team", "Position", "Value", "Points", "Value Ratio"]].head(120)
        .sort_values("value_ratio", ascending=False)
        .reset_index(drop=True),
        height=600
    )  """ 

    # 📋 Table
    table_df = (
        df[["Player", "Team", "Position", "Value", "Points", "value_ratio"]]
        .head(120)
        .sort_values("value_ratio", ascending=False)
        .reset_index(drop=True)
    )

    # index'i 1'den başlat
    table_df.index = table_df.index + 1

    st.dataframe(table_df, height=900)

# @timed("player_advice")
def player_advice(players, teams):
    st.title("🧭 Scout Assistant - Advised Players")
    st.markdown("Here you can perform a detailed search for each position, including the player's playing time, value and selection rate in your search.")
    
    position = st.selectbox("Position", ["All", "Goalkeeper", "Defence", "Midfielder", "Forward"])
    cost_limit = st.slider("Maximum Player Value", 4.0, 12.5, 8.5)
    min_minutes = st.slider("Minimum minutes played", 0, 3000, 200)
    min_points = st.slider("Minimum points", 0, 250, 20)
    sel_range = st.slider("Selection Rate (%)", 0.0, 100.0, (5.0, 25.0))

    position_map = {
        1: "Goalkeeper",
        2: "Defence",
        3: "Midfielder",
        4: "Forward"
    }

    ply = players.copy()

    ply["cost_million"] = ply["now_cost"] / 10
    ply["position_name"] = ply["element_type"].map(position_map)
    ply["selected_by_percent"] = pd.to_numeric(ply["selected_by_percent"], errors="coerce")

    # Takım adını ekle
    team_lookup = teams[["id", "name"]].rename(columns={
        "id": "team",
        "name": "team_name"
    })

    ply = ply.merge(team_lookup, on="team", how="left")

    filtered_players = ply[
        (ply["cost_million"] <= cost_limit) &
        (ply["minutes"] >= min_minutes) &
        (ply["total_points"] >= min_points) &
        (ply["selected_by_percent"] >= sel_range[0]) &
        (ply["selected_by_percent"] <= sel_range[1])
    ].copy()

    if position != "All":
        filtered_players = filtered_players[
            filtered_players["position_name"] == position
        ]

    filtered_players["value_ratio"] = (
        filtered_players["total_points"] / filtered_players["cost_million"]
    ).round(2)

    filtered_players = filtered_players.sort_values("value_ratio", ascending=False)

    table_df = (
        filtered_players[[
            "web_name",
            "team_name",
            "position_name",
            "cost_million",
            "total_points",
            "selected_by_percent",
            "value_ratio"
        ]]
        .rename(columns={
            "web_name": "Player",
            "team_name": "Team",
            "position_name": "Position",
            "cost_million": "Value",
            "total_points": "Total Points",
            "selected_by_percent": "Selected By (%)",
            "value_ratio": "Points / Value"
        })
        .reset_index(drop=True)
    )

    table_df.index = table_df.index + 1

    st.dataframe(table_df, height=600)

@st.cache_data(ttl=3600)
def compute_team_dependency_ratio(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per team: the player with the highest Team Dependency Ratio (TDR).
    Cached because it involves groupby + merge.
    """
    # Work on a copy to avoid mutating the shared DataFrame across reruns
    p = players[[
        "id", "first_name", "second_name", "web_name",
        "team", "goals_scored", "assists"
    ]].copy()

    # Contribution = goals + assists
    p["contribution"] = p["goals_scored"].fillna(0) + p["assists"].fillna(0)

    # Team total goals (based on goals_scored; simple and consistent with your current logic)
    team_goals = (
        p.groupby("team", as_index=False)["goals_scored"]
         .sum()
         .rename(columns={"team": "team_id", "goals_scored": "team_total_goals"})
    )

    t = teams[["id", "name", "short_name"]].copy()

    merged = (
        p.merge(t, left_on="team", right_on="id", how="left", suffixes=("", "_team"))
         .merge(team_goals, left_on="team", right_on="team_id", how="left")
    )

    # Avoid division by zero
    merged["team_total_goals"] = merged["team_total_goals"].fillna(0)

    merged["TDR"] = (merged["contribution"] / merged["team_total_goals"].replace(0, pd.NA)).astype("Float64")

    # Keep only teams where we can compute a meaningful ratio
    merged = merged.dropna(subset=["TDR"])

    # Pick the top TDR player per team
    team_leaders = (
        merged.sort_values("TDR", ascending=False)
              .drop_duplicates(subset=["team"])
              .reset_index(drop=True)
    )

    # Keep only columns we need downstream
    out = team_leaders[[
        "first_name", "second_name", "web_name",
        "name", "short_name",
        "goals_scored", "assists", "contribution",
        "team_total_goals", "TDR"
    ]].copy()

    return out

# @timed("team_dependency_ratio")
def team_dependency_ratio(players: pd.DataFrame, teams: pd.DataFrame) -> None:
    st.title("🏟️ Team Dependency Ratio (TDR) Analysis")
    st.markdown("The player who contributed the most points to each team is listed in this panel.")
    st.markdown("Sometimes a player takes the scoring load off their team. If you think that team will win the week, you should definitely check it out!")

    team_leaders = compute_team_dependency_ratio(players, teams)

    # Chart
    chart = (
        alt.Chart(team_leaders)
        .mark_bar()
        .encode(
            x=alt.X("short_name:N", title="Team"),
            y=alt.Y("TDR:Q", axis=alt.Axis(format="%"), title="Team Dependency Ratio"),
            color=alt.Color("name:N", legend=None),
            tooltip=[
                    alt.Tooltip("web_name:N", title="Player"),
                    alt.Tooltip("name:N", title="Team"),
                    alt.Tooltip("goals_scored:Q", title="Goals"),
                    alt.Tooltip("assists:Q", title="Assists"),
                    alt.Tooltip("contribution:Q", title="Goal Contribution"),
                    alt.Tooltip("team_total_goals:Q", title="Team Goals"),
                    alt.Tooltip("TDR:Q", format=".0%", title="TDR"),
                ],
        )
        .properties(height=400)
    )

    st.altair_chart(chart, use_container_width=True)

    # Table (pretty)
    table_df = (
        team_leaders
        .sort_values("TDR", ascending=False)
        [[
            "web_name",
            "name",
            "short_name",
            "goals_scored",
            "assists",
            "contribution",
            "team_total_goals",
            "TDR"
        ]]
        .rename(columns={
            "web_name": "Player",
            "name": "Team",
            "short_name": "Team Code",
            "goals_scored": "Goals",
            "assists": "Assists",
            "contribution": "Goal Contribution",
            "team_total_goals": "Team Goals",
            "TDR": "TDR"
        })
        .reset_index(drop=True)
    )

    table_df.index = table_df.index + 1

    st.dataframe(
        table_df.style.format({
            "TDR": "{:.0%}",
            "Goal Contribution": "{:.0f}",
            "Team Goals": "{:.0f}"
        }),
    use_container_width=True,
    height=500
) 

# @timed("consistency_index")    
def consistency_index(players):
    #history_df = pd.read_csv("./weekly_exec/weekly_points.csv")
    # history_df = pd.read_csv(DATA_DIR / "weekly_points.csv")
    history_df = load_csv(DATA_DIR / "weekly_points.csv")

    consistency = (
        history_df.groupby("player_id")["total_points"]
        .agg(["mean", "std"])
        .reset_index()
    )

    # 4. Stability score
    consistency["consistency_index"] = consistency["mean"] / consistency["std"].replace(0, 1)

    st.title("🔄 Consistency Index Analysis")
    st.markdown("Examining a player's weekly points distribution to show how stable or surprising their profile is.")
    st.markdown("Does a player consistently score the same, or does he fly for a week and then go quiet for a long time? Here we go!")
    

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
    # 7. Table
    # st.dataframe(
    #     consistency[["first_name", "second_name", "total_points", "mean", "std", "consistency_index"]]
    #     .sort_values("consistency_index", ascending=False)
    #     .reset_index(drop=True)
    #     .style.format({
    #       "mean": "{:.2f}",
    #       "std": "{:.2f}",
    #       "consistency_index": "{:.2f}"
    #   })
    # )
    table_df = (
        consistency[[
            "first_name",
            "second_name",
            "total_points",
            "mean",
            "std",
            "consistency_index"
        ]]
        .sort_values("consistency_index", ascending=False)
        .reset_index(drop=True)
    )

    # index'i 1'den başlat
    table_df.index = table_df.index + 1

    # kolon isimlerini değiştir
    table_df = table_df.rename(columns={
        "consistency_index": "consistency index",
        "total_points": "total points",
        "first_name": "first name",
        "second_name": "second name",
    })

    # EN SON stil uygula
    table_df = table_df.style.format({
        "mean": "{:.2f}",
        "std": "{:.2f}",
        "consistency index": "{:.2f}",
    })

    st.dataframe(table_df, height=500)

# def read_pl_table():
#     # df  = pd.read_csv(DATA_DIR / "league_table.csv")
#     df = load_csv(DATA_DIR / "league_table.csv")

#     # Convert team column to dict
#     df["team"] = df["team"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
#     df["team_name"] = df["team"].apply(lambda t: t.get("name") if isinstance(t, dict) else t)
#     df["short_name"] = df["team"].apply(lambda t: t.get("shortName") if isinstance(t, dict) else t)

#     standings = df[[
#         "position", "team_name", "playedGames", "won", "draw", "lost", 
#         "goalsFor", "goalsAgainst", "goalDifference", "points"
#     ]].sort_values("position").reset_index(drop=True)
#     return standings


@st.cache_data
def compute_pl_standings(path: str, mtime: float) -> pd.DataFrame:
    df = pd.read_csv(path)

    # team kolonu string json/dict formatındaysa parse et
    df["team"] = df["team"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)

    # dict içinden alanları çıkar
    df["team_name"] = df["team"].apply(lambda t: t.get("name") if isinstance(t, dict) else t)
    df["short_name"] = df["team"].apply(lambda t: t.get("shortName") if isinstance(t, dict) else t)

    standings = (
        df[[
            "position", "team_name", "playedGames", "won", "draw", "lost",
            "goalsFor", "goalsAgainst", "goalDifference", "points"
        ]]
        .sort_values("position")
        .reset_index(drop=True)
    )
    return standings

def read_pl_table() -> pd.DataFrame:
    path = str(DATA_DIR / "league_table.csv")
    return compute_pl_standings(path, os.path.getmtime(path))

 
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

# @timed("show_table") 
def show_table():
    st.title("🏆 Premier League Table")
    standings = read_pl_table()
    html = render_standings_html(standings)  
    components.html(html, height=950, scrolling=True)

@st.cache_data
def load_fixtures():
    url = "https://fantasy.premierleague.com/api/fixtures/"
    #r = requests.get(url)
    r = requests.get(url, timeout=15); r.raise_for_status()
    return r.json()

# @st.cache_data
# def load_teams():
#     url = "https://fantasy.premierleague.com/api/bootstrap-static/"
#     r = requests.get(url).json()
#     teams = pd.DataFrame(r["teams"])
#     return teams[["id", "name", "short_name", "code"]], r["events"]


def build_fixture_difficulty(fixtures, teams, events, gameweeks=5):
    # Just take the next X weeks
    current_gw = next(e["id"] for e in events if e["is_current"]) + 1

    upcoming = [f for f in fixtures if f["event"] and current_gw <= f["event"] < current_gw+gameweeks]

    # Home and Away are processed separately
    data = []
    for f in upcoming:
        # Home
        data.append({
            "team": f["team_h"],
            "opponent": f["team_a"],
            "gw": f["event"],
            "difficulty": f["team_h_difficulty"],
            "venue": "H"
        })
        # Away
        data.append({
            "team": f["team_a"],
            "opponent": f["team_h"],
            "gw": f["event"],
            "difficulty": f["team_a_difficulty"],
            "venue": "A"
        })

    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df = df.merge(teams, left_on="team", right_on="id").drop("id", axis=1)
    df = df.merge(teams, left_on="opponent", right_on="id", suffixes=("", "_opp")).drop("id", axis=1)

    # Average difficulty per team
    avg_df = df.groupby("name").agg({"difficulty":"mean"}).reset_index().sort_values("difficulty")
    avg_df.rename(columns={"difficulty":"Avg Difficulty (next %d GWs)" % gameweeks}, inplace=True)

    return avg_df, df

# @timed("fixture_difficulty_analysis") 
def fixture_difficulty_analysis(teams, events):
    st.title("📊 Fixture Difficulty Analysis")

    fixtures = load_fixtures()
    #teams, events = load_teams()

    avg_df, fixture_df = build_fixture_difficulty(fixtures, teams, events, gameweeks=5)
    if avg_df.empty or fixture_df.empty:
        st.warning("Fixture difficulty datası şu anda üretilemedi. Muhtemelen önümüzdeki gameweek fixture datası henüz API'de yok.")
        return

    st.write("### Average FDR (Next 5 Games)")
    
    #st.dataframe(avg_df, use_container_width=True)
    styled_avg = avg_df.style.background_gradient(
        cmap="RdYlGn_r", subset=["Avg Difficulty (next 5 GWs)"]
    ).format({"Avg Difficulty (next 5 GWs)": "{:.2f}"})

    st.dataframe(styled_avg, use_container_width=True,  hide_index=True)

    # Detailed table (competitor name + difficulty)
    st.write("### Fixture Difficulty Detailed")
    fixture_df["opp_info"] = fixture_df["short_name_opp"] + " (" + fixture_df["difficulty"].astype(str) + ")"
    pivot = fixture_df.pivot_table(index="name", columns="gw", values="opp_info", aggfunc="first")
    st.dataframe(pivot, use_container_width=True)

# @timed("show_player_stats") 
def show_player_stats(players, teams):
    st.title("📊 Player Statistics – Dynamic Ranking")

    # Kullanıcıya görünen isim -> DataFrame kolon adı
    METRIC_ALIASES = {
        "Total Points": "total_points",
        "Price (£m)": "now_cost",        # not: FPL'de now_cost genelde 10x gelir (örn 75 = 7.5)
        "Minutes": "minutes",
        "Goals": "goals_scored",
        "Assists": "assists",
        "ICT Index": "ict_index",
    }

    # Futbol mantığına uygun sıra (alfabetik değil)
    metric_labels = list(METRIC_ALIASES.keys())

    metric_label = st.selectbox(
        "Select sorting criteria:",
        metric_labels,
        index=0  # default: Total Points -> tablo hemen gelsin
    )
    metric_choice = METRIC_ALIASES[metric_label]

    order_choice = st.radio("Sort direction:", ["Descending", "Ascending"], index=0)
    ascending = (order_choice == "Ascending")

    merged_players = players.merge(
        teams[["id", "name"]],
        left_on="team",
        right_on="id",
        how="left"
    )

    # İsteğe bağlı: price'ı düzgün göstermek (now_cost çoğu zaman 10x)
    if metric_choice == "now_cost":
        merged_players["now_cost"] = merged_players["now_cost"] / 10

    sorted_df = merged_players.sort_values(metric_choice, ascending=ascending)

    # Player adını birleştir
    sorted_df["Player"] = (sorted_df["first_name"].fillna("") + " " + sorted_df["second_name"].fillna("")).str.strip()

    # Ekranda kolon başlığı alias görünsün
    out = sorted_df[["Player", "name", metric_choice]].head(50).rename(columns={
        "name": "Team",
        metric_choice: metric_label
    })

    st.dataframe(out, use_container_width=True, hide_index=True)
