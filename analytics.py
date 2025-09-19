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


def check_wildcard(user_id, data, fixtures, lookahead_gw=5, form_weeks=5,
                   form_threshold_count=3, fdr_threshold=3.6, injured_threshold=0.25):
    """
    Wildcard kontrolü (daha sağlam versiyon).
    - user_id: FPL entry id (int or str)
    - data: bootstrap-static JSON (dict)
    - fixtures: fixtures JSON (list of dicts)
    - lookahead_gw: kaç GW ileri bakılacak (default 5)
    - form_weeks: son kaç haftaya bakılacak (default 5)
    - form_threshold_count: son form_weeks içinde kaç kere altında kalırsa kötü form kabul edilecek (default 3)
    - fdr_threshold: ortalama FDR eşiği (örn. 3.6)
    - injured_threshold: sakat/cezalı oranı eşiği (örn. 0.25)
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
        # fallback: en küçük bitmemiş veya max id - daha güvenli mantık isteğe göre değişir
        raise RuntimeError("Couldn't determine current GW from bootstrap 'events' data.")

    # --- 1) Kullanıcının history'ini çek (güvenli)
    history_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/history/"
    r = requests.get(history_url)
    if r.status_code != 200:
        raise RuntimeError(f"History fetch failed (status {r.status_code}) for user {user_id}")
    hist = r.json()
    if "current" not in hist or len(hist["current"]) == 0:
        # bazen farklı yapı olabilir; handle gracefully
        return "⚠️ Kullanıcı geçmişi bulunamadı veya boş. ID'yi kontrol et."

    past = pd.DataFrame(hist["current"])
    if "points" not in past.columns:
        return "⚠️ History verisinde 'points' yok; farklı bir response yapısıyla karşılaşıldı."

    # son N haftayı al (eğer daha az varsa, var olanları kullan)
    lastN = past.tail(form_weeks).copy()
    user_mean = past["points"].mean()  # kullanıcının sezon ortalaması

    # Kaç kez kullanıcı sezon ortalamasının altında kalmış?
    under_avg = int((lastN["points"] < user_mean).sum())
    bad_form = under_avg >= form_threshold_count

    # --- 2) Squad/picks çek
    picks_url = f"https://fantasy.premierleague.com/api/entry/{user_id}/event/{current_gw}/picks/"
    r = requests.get(picks_url)
    if r.status_code != 200:
        return "⚠️ Kullanıcı picks verisi alınamadı. (private / non-existent / rate-limited?)"
    picks_json = r.json()
    # picks JSON yapısı değişebilir (bazı endpoint'lerde 'picks' olmadığında farklı response olur)
    if "picks" not in picks_json:
        return "⚠️ Picks bilgisi response içinde yok."

    squad_ids = [int(p["element"]) for p in picks_json["picks"]]

    squad_players = players[players["id"].isin(squad_ids)].copy()
    if squad_players.empty:
        return "⚠️ Squad verisi eşleşmedi (oyuncu id'leri bulunamadı)."

    # --- 3) Fixture zorlukları: önümüzdeki lookahead_gw haftalık ortalama FDR
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
        # map takım zorluklarını kullanıcının kadrosuna
        squad_players["team_difficulty"] = squad_players["team"].map(team_diff_map)
        avg_fdr = float(squad_players["team_difficulty"].dropna().mean()) if not squad_players["team_difficulty"].dropna().empty else float("nan")

    hard_fixtures = False
    if not pd.isna(avg_fdr):
        hard_fixtures = avg_fdr >= fdr_threshold

    # --- 4) Sakat/cezalı oranı
    if "status" in squad_players.columns:
        flagged = squad_players[squad_players["status"].isin(["i", "s", "d"])]
        injured_ratio = len(flagged) / len(squad_players) if len(squad_players) > 0 else 0.0
    else:
        injured_ratio = 0.0
    many_injuries = injured_ratio >= injured_threshold

    # --- 5) Sonuç / açıklama oluşturma
    reasons = []
    if bad_form:
        reasons.append(f"son {form_weeks} haftada {under_avg} kere kendi sezon ortalamanın ({user_mean:.1f}) altında puan aldın")
    if not pd.isna(avg_fdr):
        reasons.append(f"kadronun önümüzdeki {lookahead_gw} GW için ortalama FDR {avg_fdr:.2f}")
    else:
        reasons.append("önümüzdeki fikstür verisi yetersiz")
    if many_injuries:
        reasons.append(f"kadronun %{int(injured_ratio*100)}'i sakat/şüpheli/cezalı")

    # karar mantığı: bir veya daha fazla sebep varsa wildcard öner
    if bad_form or hard_fixtures or many_injuries:
        return "💡 Wildcard düşünebilirsin çünkü " + "; ".join(reasons) + "."
    else:
        return "✅ Wildcard için acil bir sebep görünmüyor. " + "; ".join(reasons) + "."
    
def chip_suggestion():
    st.title("🎮 Chip Suggestions for FPL")

    # 1) User ID input
    user_id = st.text_input("FPL User ID giriniz:", placeholder="ör. 123456")

    if user_id:
        st.divider()  # gri çizgi ile ayır

        # 2) Triple Captain
        st.subheader("🎯 Triple Captain Suggestion")
        tc_suggestion = suggest_triple_captain(user_id, data, fixtures_data)
        st.info(tc_suggestion)

        st.divider()

        # 3) Wild Card
        st.subheader("🃏 Wild Card Suggestion")
        wc_suggestion = check_wildcard(user_id, data, fixtures_data)
        st.info(wc_suggestion)    

