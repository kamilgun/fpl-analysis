import requests
import pandas as pd
import time

# Get data from FPL API
url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()

# Export data to DataFrame
players = pd.DataFrame(data['elements'])
teams = pd.DataFrame(data['teams'])

def get_fpl_players_history():
    """
    Tüm oyuncuların 'element-summary' datasını çekip
    history (GW performansları) datasını tek bir DataFrame olarak döner.
    """
    # 1. Önce bootstrap'ten tüm oyuncuların id'lerini al
    player_ids = players["id"].tolist()

    all_history = []

    # 2. Her oyuncu için element-summary çek
    for pid in player_ids:
        try:
            url = f"https://fantasy.premierleague.com/api/element-summary/{pid}/"
            player_data = requests.get(url).json()

            history = pd.DataFrame(player_data["history"])
            if not history.empty:
                history["player_id"] = pid
                all_history.append(history)

            # FPL API'yi zorlamamak için küçük bekleme
            time.sleep(0.2)

        except Exception as e:
            print(f"⚠️ Player {pid} için hata: {e}")

    # 3. Tüm history'leri birleştir
    history_df = pd.concat(all_history, ignore_index=True)

    history_df.to_csv("./weekly_points.csv", index=False, encoding='utf-8-sig')
    history_df.to_csv("./fpl_stats/weekly_points.csv", index=False, encoding='utf-8-sig')
    return history_df, players

def fpl_value_calc():
    position_map = {
        1: "Goalkeeper",
        2: "Defender",
        3: "Midfielder",
        4: "Forward"
    }
    players["position"] = players["element_type"].map(position_map)


    # Get the required columns
    df = players[['first_name', 'second_name', 'team', 'position','now_cost', 'total_points', 'minutes']].copy()
    df['now_cost'] = df['now_cost'] / 10  # 50 -> 5.0M gibi

    #print(df.head())  # Print first few rows to check data

    # Match team name
    team_map = teams.set_index('id')['name'].to_dict()
    df['team_name'] = df['team'].map(team_map)

    # Combine first and last name
    df['name'] = df['first_name'] + ' ' + df['second_name']

    # Calculate value ratio
    df['value_ratio'] = df['total_points'] / df['now_cost']

    # Eliminate players with very few minutes (e.g. less than 500 minutes)
    df_filtered = df[df['minutes'] > 30]

    # Get the top 120 players
    top_value_players = df_filtered.sort_values(by='value_ratio', ascending=False).head(120)

    # Show only required columns
    result = top_value_players[['name', 'team_name', 'position', 'now_cost', 'total_points', 'value_ratio']]

    from tabulate import tabulate

    import os

    print("Şu anki çalışma dizini:", os.getcwd())
    # Klasör varsa geç, yoksa oluştur
    os.makedirs("verianalizi/fpl_stats", exist_ok=True)

    # Get only required columns
    table_data = top_value_players[['name', 'team_name', 'position', 'now_cost', 'total_points', 'value_ratio']].copy()

    # Rename column names
    table_data.columns = ['Player', 'Team', 'Position', 'Value', 'Points', 'Points/Value']

    # Print table
    print(tabulate(table_data, headers='keys', tablefmt='fancy_grid', showindex=False, floatfmt=".2f"))

    # Oranları yuvarla
    table_data['value_ratio'] = result['value_ratio'].round(2)
    table_data['now_cost'] = result['now_cost'].round(1)

    #print(result.to_string(index=False))
    print("Satır sayısı:", len(table_data))

    print(table_data.head())  # İlk birkaç satırı yazdır


    table_data.to_csv("./player_stats.csv", index=False, encoding='utf-8-sig')
    table_data.to_csv("./fpl_stats/player_stats.csv", index=False, encoding='utf-8-sig')

def pl_table():
    url = "https://api.football-data.org/v4/competitions/PL/standings"
    headers = {"X-Auth-Token": "8df16e10df3c45a08707dfdc1c76ef29"}

    response = requests.get(url, headers=headers)
    data = response.json()
    table = data['standings'][0]['table']   # bu list of dict
    df = pd.DataFrame(table)                # DataFrame'e çevir

    # İstediğin kolonları seçebilirsin, ör:
    # df = df[["position", "team", "playedGames", "won", "draw", "lost", "points", "goalDifference"]]

    df.to_csv("./league_table.csv", index=False, encoding='utf-8-sig')



#get_fpl_players_history()
#fpl_value_calc()
#pl_table()
