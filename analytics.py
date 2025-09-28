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
    print("Calculating Triple Captain recommendation...")

    # Current GW
    current_gw = events.loc[events["is_current"] == True, "id"].values[0]

    # Get user squad
    entry_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gw}/picks/"
    squad = requests.get(entry_url).json()["picks"]
    squad_ids = [p["element"] for p in squad]

    user_players = players[players["id"].isin(squad_ids)].copy()
    user_players["form"] = user_players["form"].astype(float)

    # GW Fixtures
    gw_fixtures = [f for f in fixtures if f["event"] == current_gw]

    # Fixture difficulty table (team id → avg difficulty)
    fixture_df = pd.DataFrame([
        {"team": f["team_h"], "difficulty": f["team_h_difficulty"]} for f in gw_fixtures
    ] + [
        {"team": f["team_a"], "difficulty": f["team_a_difficulty"]} for f in gw_fixtures
    ])
    team_difficulty = fixture_df.groupby("team")["difficulty"].mean().to_dict()

    # Find Double GW players
    doubles = []
    for pid in user_players["id"]:
        team_id = user_players.loc[user_players["id"] == pid, "team"].values[0]
        matches = [f for f in gw_fixtures if f["team_h"] == team_id or f["team_a"] == team_id]
        if len(matches) > 1:
            doubles.append(pid)

    # --- Priority  1: Double GW + form >= 5.5
    candidates = user_players[(user_players["form"] >= 5.5) & (user_players["id"].isin(doubles))]
    if not candidates.empty:
        best = candidates.sort_values("form", ascending=False).iloc[0]
        return f"🎯 Triple Captain candidate: {best['web_name']} ({teams.loc[best['team']-1,'name']}) - Form {best['form']}, Double GW!"
    
    # --- Priority  lik 2: Single game + form >= 6.5 + easy fixture
    user_players["team_difficulty"] = user_players["team"].map(team_difficulty)
    candidates = user_players[(user_players["form"] >= 6.5) & (user_players["team_difficulty"] <= 2.5)]
    if not candidates.empty:
        best = candidates.sort_values("form", ascending=False).iloc[0]
        return f"🎯 Alternative  Triple Captain candidate: {best['web_name']} ({teams.loc[best['team']-1,'name']}) - Form {best['form']}, easy fixture ({best['team_difficulty']})"
    
    # --- Nothing found, explain why 
    reasons = []
    if len(doubles) == 0:
        reasons.append("No Double GW")
    if user_players["form"].max() < 6.5:
        reasons.append("You don't have any in-form players")
    if user_players["team"].map(team_difficulty).min() > 2.5:
        reasons.append("fixtures are not easy enough")

    reason_text = ", ".join(reasons) if reasons else "general conditions are not suitable"

    return f"⚠️ This week, the Triple Captain candidate was not found because {reason_text}."


def check_wildcard(user_id, data, fixtures, lookahead_gw=5, form_weeks=5,
                   form_threshold_count=3, fdr_threshold=3.6, injured_threshold=0.25):
    """
Wildcard check (more robust version).
- user_id: FPL entry id (int or str)
- data: bootstrap-static JSON (dict)
- fixtures: fixtures JSON (list of dicts)
- lookahead_gw: number of GWs to look ahead (default 5)
- form_weeks: number of weeks in the past (default 5)
- form_threshold_count: number of times in the past form_weeks that it falls below will be considered bad form (default 3)
- fdr_threshold: average FDR threshold (e.g. 3.6)
- injured_threshold: injured/penalty ratio threshold (e.g. 0.25)
    """

    players = pd.DataFrame(data.get("elements", []))
    teams = pd.DataFrame(data.get("teams", []))
    events = pd.DataFrame(data.get("events", []))

    # current GW'yi güvenli alma
    current_gw = None
    if not events.empty and "is_current" in events.columns:
        cur = events.loc[events["is_current"] == True, "id"]
        if len(cur) > 0:
            current_gw = int(cur.values[0])
    if current_gw is None:
       # fallback: smallest unfinished or max id - safer logic varies optional
        raise RuntimeError("Couldn't determine current GW from bootstrap 'events' data.")

    # --- 1) Check the user's history (safe)
    history_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/history/"
    r = requests.get(history_url)
    if r.status_code != 200:
        raise RuntimeError(f"History fetch failed (status {r.status_code}) for user {user_id}")
    hist = r.json()
    if "current" not in hist or len(hist["current"]) == 0:
        # bazen farklı yapı olabilir; handle gracefully
        return "⚠️ User history not found or empty. Check ID."

    past = pd.DataFrame(hist["current"])
    if "points" not in past.columns:
        return "⚠️ No 'points' in history data; a different response structure was encountered."

    # take the last N weeks (if there are fewer, use existing ones)
    lastN = past.tail(form_weeks).copy()
    user_mean = past["points"].mean()  # user's season average

    # How many times has the user been below the seasonal average?
    under_avg = int((lastN["points"] < user_mean).sum())
    bad_form = under_avg >= form_threshold_count

    # --- 2) Squad/picks check
    picks_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gw}/picks/"
    r = requests.get(picks_url)
    if r.status_code != 200:
        return "⚠️ Could not retrieve user picks data. (private / non-existent / rate-limited?)"
    picks_json = r.json()
    # The picks JSON structure may vary (some endpoints will have different responses when there are no 'picks')
    if "picks" not in picks_json:
        return "⚠️ Picks information is not in the response."

    squad_ids = [int(p["element"]) for p in picks_json["picks"]]

    squad_players = players[players["id"].isin(squad_ids)].copy()
    if squad_players.empty:
        return "⚠️ Squad data did not match (player IDs not found)."

    # --- 3) Fixture challenges: upcoming lookahead_gw weekly average FDR
    gw_fixtures = [f for f in fixtures if f.get("event") and current_gw <= f["event"] < current_gw + lookahead_gw]
    if len(gw_fixtures) == 0:
        avg_fdr = float("nan")
    else:
        rows = []
        for f in gw_fixtures:
            rows.append({"team": int(f["team_h"]), "diff": float(f["team_h_difficulty"])})
            rows.append({"team": int(f["team_a"]), "diff": float(f["team_a_difficulty"])})
        fix_df = pd.DataFrame(rows)
        team_diff_map = fix_df.groupby("team")["diff"].mean().to_dict()
        # map team difficulties to the user's squad
        squad_players["team_difficulty"] = squad_players["team"].map(team_diff_map)
        avg_fdr = float(squad_players["team_difficulty"].dropna().mean()) if not squad_players["team_difficulty"].dropna().empty else float("nan")

    hard_fixtures = False
    if not pd.isna(avg_fdr):
        hard_fixtures = avg_fdr >= fdr_threshold

    # --- 4) Injured/suspended ratio
    if "status" in squad_players.columns:
        flagged = squad_players[squad_players["status"].isin(["i", "s", "d"])]
        injured_ratio = len(flagged) / len(squad_players) if len(squad_players) > 0 else 0.0
    else:
        injured_ratio = 0.0
    many_injuries = injured_ratio >= injured_threshold

    # --- 5) Create conclusion/explanation
    reasons = []
    if bad_form:
        reasons.append(f"You scored below your season average ({user_mean:.1f}) {under_avg} times in the last {form_weeks} weeks")
    if not pd.isna(avg_fdr):
        reasons.append(f"squad's average FDR for the upcoming {lookahead_gw} GW is {avg_fdr:.2f}")
    else:
        reasons.append("insufficient fixture data")
    if many_injuries:
        reasons.append(f"{int(injured_ratio*100)}% of the squad is injured/questionable/suspended")

    # Decision logic: propose a wildcard if one or more reasons exist
    if bad_form or hard_fixtures or many_injuries:
        return "💡 You can consider wildcard because " + "; ".join(reasons) + "."
    else:
        return "✅ There doesn't seem to be any pressing reason for a wildcard " + "; ".join(reasons) + "."
    
def chip_suggestion():
    st.title("🎮 Chip Suggestions for FPL")

    # 1) User ID input
    user_id = st.text_input("Enter your FPL User ID:", placeholder="ex. 123456")

    if user_id:
        st.divider()  # separate with gray line
        
        # 2) Triple Captain
        st.subheader("🎯 Triple Captain Suggestion")
        tc_suggestion = suggest_triple_captain(user_id, data, fixtures_data)
        st.info(tc_suggestion)

        st.divider()

        # 3) Wild Card
        st.subheader("🃏 Wild Card Suggestion")
        wc_suggestion = check_wildcard(user_id, data, fixtures_data)
        st.info(wc_suggestion)    

