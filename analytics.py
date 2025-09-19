import streamlit as st
import requests
import pandas as pd



url = "https://fantasy.premierleague.com/api/bootstrap-static/"
response = requests.get(url)
data = response.json()


url = "https://fantasy.premierleague.com/api/fixtures/"
response = requests.get(url)
fixtures_data = response.json()

def suggest_triple_captain(user_id, data, fixtures):
    players = pd.DataFrame(data["elements"])
    teams = pd.DataFrame(data["teams"])
    events = pd.DataFrame(data["events"])

    print(f"User ID: {user_id}")
    print("Triple Captain önerisi hesaplanıyor...")

    # Güncel GW
    current_gw = events.loc[events["is_current"] == True, "id"].values[0]

    # User squad çek
    entry_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gw}/picks/"
    squad = requests.get(entry_url).json()["picks"]
    squad_ids = [p["element"] for p in squad]

    user_players = players[players["id"].isin(squad_ids)].copy()
    user_players["form"] = user_players["form"].astype(float)

    # O GW'deki fixture'lar
    gw_fixtures = [f for f in fixtures if f["event"] == current_gw]

    # Fixture kolaylık tablosu (takım id → avg difficulty)
    fixture_df = pd.DataFrame([
        {"team": f["team_h"], "difficulty": f["team_h_difficulty"]} for f in gw_fixtures
    ] + [
        {"team": f["team_a"], "difficulty": f["team_a_difficulty"]} for f in gw_fixtures
    ])
    team_difficulty = fixture_df.groupby("team")["difficulty"].mean().to_dict()

    # Double GW oyuncuları bul
    doubles = []
    for pid in user_players["id"]:
        team_id = user_players.loc[user_players["id"] == pid, "team"].values[0]
        matches = [f for f in gw_fixtures if f["team_h"] == team_id or f["team_a"] == team_id]
        if len(matches) > 1:
            doubles.append(pid)

    # --- Öncelik 1: Double GW + form >= 5.5
    candidates = user_players[(user_players["form"] >= 5.5) & (user_players["id"].isin(doubles))]
    if not candidates.empty:
        best = candidates.sort_values("form", ascending=False).iloc[0]
        return f"🎯 Triple Captain adayı: {best['web_name']} ({teams.loc[best['team']-1,'name']}) - Form {best['form']}, Double GW!"
    
    # --- Öncelik 2: Tek maç + form >= 6.5 + kolay fixture
    user_players["team_difficulty"] = user_players["team"].map(team_difficulty)
    candidates = user_players[(user_players["form"] >= 6.5) & (user_players["team_difficulty"] <= 2.5)]
    if not candidates.empty:
        best = candidates.sort_values("form", ascending=False).iloc[0]
        return f"🎯 Alternatif Triple Captain adayı: {best['web_name']} ({teams.loc[best['team']-1,'name']}) - Form {best['form']}, kolay fikstür ({best['team_difficulty']})"
    
    # --- Hiçbiri değil
    reasons = []
    if len(doubles) == 0:
        reasons.append("Double GW yok")
    if user_players["form"].max() < 6.5:
        reasons.append("formda oyuncun yok")
    if user_players["team"].map(team_difficulty).min() > 2.5:
        reasons.append("fikstürler yeterince kolay değil")

    reason_text = ", ".join(reasons) if reasons else "genel koşullar uygun değil"

    return f"⚠️ Bu hafta Triple Captain adayı bulunamadı çünkü {reason_text}."

def streamlit_triple_captain():
    # UI
    st.title("Chip Suggestions for FPL 2")

    user_id = st.text_input("FPL User ID giriniz:")

    st.subheader("🎯 Triple Captain Suggestion")

    if user_id:
        #data = load_data()
        #fixtures = load_fixtures()
        suggestion = suggest_triple_captain(user_id, data, fixtures_data)
        st.success(suggestion)

    st.subheader("🎯 Wild Card Suggestion")

    if user_id:
        #data = load_data()
        #fixtures = load_fixtures()
        suggestion = check_wildcard(user_id, data, fixtures_data)
        st.info(suggestion)

def check_wildcard(user_id, data, fixtures):
    events = pd.DataFrame(data["events"])
    players = pd.DataFrame(data["elements"])
    teams = pd.DataFrame(data["teams"])

    # Güncel GW
    current_gw = events.loc[events["is_current"], "id"].values[0]

    # Son 5 GW skorlarını çek
    history_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/history/"
    history = requests.get(history_url).json()
    past = pd.DataFrame(history["current"])
    last5 = past.tail(5)

    # 1) Form düşüklüğü: 5 haftada 3+ kez global avg altında
    under_avg = (last5["points"] < last5["points_average"]).sum()
    bad_form = under_avg >= 3

    # 2) Zor fikstür: kadronun ortalama FDR’si önümüzdeki 5 hafta
    picks_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gw}/picks/"
    squad = requests.get(picks_url).json()["picks"]
    squad_ids = [p["element"] for p in squad]

    squad_players = players[players["id"].isin(squad_ids)]
    gw_fixtures = [f for f in fixtures if f["event"] and current_gw <= f["event"] < current_gw+5]

    data_rows = []
    for f in gw_fixtures:
        data_rows.append({"team": f["team_h"], "diff": f["team_h_difficulty"]})
        data_rows.append({"team": f["team_a"], "diff": f["team_a_difficulty"]})
    fix_df = pd.DataFrame(data_rows)
    avg_fdr = squad_players["team"].map(fix_df.groupby("team")["diff"].mean().to_dict()).mean()

    hard_fixtures = avg_fdr >= 3.6

    # 3) Sakat/cezalı oranı
    status_flags = ["i", "d", "s"]  # injured, doubtful, suspended
    flagged = squad_players[squad_players["status"].isin(status_flags)]
    injured_ratio = len(flagged) / len(squad_players)
    many_injuries = injured_ratio >= 0.25

    # Sonuç ve açıklama
    reasons = []
    if bad_form:
        reasons.append(f"Son 5 haftada {under_avg} kez ortalamanın altında puan aldın")
    if hard_fixtures:
        reasons.append(f"Önümüzdeki 5 haftada kadronun ortalama FDR’si {avg_fdr:.2f} (zor fikstür)")
    if many_injuries:
        reasons.append(f"Oyuncularının %{int(injured_ratio*100)}’i sakat/cezalı")

    if reasons:
        return "💡 Wildcard düşünebilirsin çünkü " + ", ".join(reasons) + "."
    else:
        return "✅ Wildcard için acil bir sebep görünmüyor. Kadron gayet stabil."

#suggest_triple_captain(932776, data, fixtures_data)