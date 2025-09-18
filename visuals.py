import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt

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
        .reset_index(drop=True)
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
            x=alt.X("mean:Q", title="Ortalama Puan"),
            y=alt.Y("std:Q", title="Standart Sapma"),
            color="team:N",
            tooltip=["web_name", "total_points", "mean", "std", "consistency_index"]
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
    )    