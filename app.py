import os
import json
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from comparison import compare_players, get_player_history

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=openai_key)

df = pd.read_csv("players.csv")

st.set_page_config(
    page_title="AI Football Scout",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚽ AI Football Scout")
st.markdown("*Find transfer targets by position, age, nationality and budget — with AI-powered analysis*")
st.divider()

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    your_club = st.selectbox("Your Club (optional)", ["Any"] + sorted(df['team'].dropna().unique().tolist()))
    position = st.selectbox("Position Needed", ["Any", "FW", "MF", "DF", "GK"])
    budget = st.selectbox("Transfer Budget", [
        "Any",
        "Under £20m",
        "£20m - £50m",
        "£50m - £100m",
        "£100m - £150m",
        "Over £150m"
    ])

with col2:
    max_age = st.slider("Maximum Age", min_value=18, max_value=35, value=28)
    min_minutes = st.slider("Minimum Minutes", min_value=0, max_value=3420, value=500)
    if position in ["FW", "Any"]:
        min_goals = st.slider("Minimum Goals", min_value=0, max_value=30, value=5)
    else:
        min_goals = 0

with col3:
    if position in ["FW", "MF", "Any"]:
        min_ga_per90 = st.slider("Minimum G+A per 90", min_value=0.0, max_value=2.0, value=0.3, step=0.1)
    else:
        min_ga_per90 = 0.0
    if position in ["FW", "MF", "Any"]:
        min_assists = st.slider("Minimum Assists", min_value=0, max_value=20, value=0)
    else:
        min_assists = 0
    nationalities = sorted(df['nation'].dropna().unique().tolist())
    nationality = st.selectbox("Nationality", ["Any"] + nationalities)

season = st.selectbox(
    "Season",
    options=["Most Recent", "2526", "2425", "2324", "2223", "2021"],
    index=0
)
playing_style = st.text_input("Playing Style (optional)", placeholder="e.g. high press, possession, counter attack")
st.divider()

# Position focus
if position == "DF":
    analysis_focus = "Focus on availability, defensive positioning, aerial ability, versatility. Do NOT focus on goals or assists."
elif position == "GK":
    analysis_focus = "Focus on availability and consistency. Do NOT focus on goals or assists."
elif position == "MF":
    analysis_focus = "Focus on assists, creativity, G+A per 90. Goals secondary."
else:
    analysis_focus = "Focus on goals, assists and G+A per 90 as primary metrics."

# Session state init
for key in ['results_ready', 'perf_data', 'perf_report', 'human_data', 'human_report',
            'verdict_data', 'verdict', 'display', 'top_3_players', 'club_squad_detail',
            'show_comparison', 'your_club_saved']:
    if key not in st.session_state:
        st.session_state[key] = None

if st.session_state.results_ready is None:
    st.session_state.results_ready = False
if st.session_state.show_comparison is None:
    st.session_state.show_comparison = False
if st.session_state.club_squad_detail is None:
    st.session_state.club_squad_detail = ""
if st.session_state.your_club_saved is None:
    st.session_state.your_club_saved = "Any"

def scout_notes_box(text):
    st.markdown(
        f"""<div style='height:180px; overflow-y:auto;
        background-color:#1e1e2e; color:#e0e0e0;
        padding:12px; border-radius:8px; font-size:13px;
        line-height:1.6; border: 1px solid #444;'>
        {text}
        </div>""",
        unsafe_allow_html=True
    )

if st.button("🔍 Find Transfer Targets", type="primary", use_container_width=True):
    st.session_state.results_ready = False
    st.session_state.show_comparison = False
    st.session_state.your_club_saved = your_club

    most_recent_season = df['season'].max()
    current_squads = df[df['season'] == most_recent_season][['player', 'team']].rename(columns={'team': 'current_team'})
    all_latest = df.sort_values('season', ascending=False).drop_duplicates('player')[['player', 'team']].rename(columns={'team': 'current_team'})
    latest = all_latest.merge(current_squads, on='player', how='left', suffixes=('_old', '_new'))
    latest['current_team'] = latest['current_team_new'].fillna(latest['current_team_old'])
    latest = latest[['player', 'current_team']]

    if season == "Most Recent":
        filtered = df.sort_values('season', ascending=False).drop_duplicates('player')
    else:
        filtered = df[df['season'].astype(str) == season]

    filtered = filtered.drop(columns=['team']).merge(latest, on='player', how='left')
    filtered = filtered.rename(columns={'current_team': 'team'})

    if your_club != "Any":
        filtered = filtered[filtered['team'] != your_club]

    filtered = filtered[filtered['age'] <= max_age]
    filtered = filtered[filtered['Playing Time_Min'] >= min_minutes]

    if min_goals > 0:
        filtered = filtered[filtered['Performance_Gls'] >= min_goals]
    if min_assists > 0:
        filtered = filtered[filtered['Performance_Ast'] >= min_assists]
    if min_ga_per90 > 0:
        filtered = filtered[filtered['Per 90 Minutes_G+A'] >= min_ga_per90]
    if position != "Any":
        filtered = filtered[filtered['pos'].str.contains(position, na=False)]
    if nationality != "Any":
        filtered = filtered[filtered['nation'] == nationality]

    if position in ["DF", "GK"]:
        filtered = filtered.sort_values('Playing Time_Min', ascending=False).head(15)
    else:
        filtered = filtered.sort_values('Per 90 Minutes_G+A', ascending=False).head(15)

    if filtered.empty:
        st.warning("No players found. Try relaxing your filters.")
    else:
        if position in ["DF", "GK"]:
            display = filtered[[
                'player', 'team', 'nation', 'pos', 'age', 'season',
                'Playing Time_MP', 'Playing Time_Min',
                'Performance_CrdY', 'Performance_CrdR'
            ]]
            display.columns = ['Player', 'Club', 'Nation', 'Position', 'Age', 'Season', 'Matches', 'Minutes', 'Yellow Cards', 'Red Cards']
        else:
            display = filtered[[
                'player', 'team', 'nation', 'pos', 'age', 'season',
                'Playing Time_MP', 'Playing Time_Min',
                'Performance_Gls', 'Performance_Ast',
                'Performance_G+A', 'Per 90 Minutes_G+A'
            ]]
            display.columns = ['Player', 'Club', 'Nation', 'Position', 'Age', 'Season', 'Matches', 'Minutes', 'Goals', 'Assists', 'G+A', 'G+A per 90']

        top_3_players = display.head(3)
        st.session_state.display = display
        st.session_state.top_3_players = top_3_players

        if your_club != "Any":
            club_data = df[df['team'] == your_club].sort_values('season', ascending=False).drop_duplicates('player')
            club_avg_goals = round(club_data['Performance_Gls'].mean(), 2)
            club_avg_ga = round(club_data['Per 90 Minutes_G+A'].mean(), 2)
            club_players_nations = club_data[['player', 'nation']].dropna().drop_duplicates().values.tolist()
            club_squad_detail = ', '.join([f"{p} ({n})" for p, n in club_players_nations])
            club_context = f"""
BUYING CLUB: {your_club}
CLUB AVERAGE GOALS PER PLAYER: {club_avg_goals}
CLUB AVERAGE G+A PER 90: {club_avg_ga}
CURRENT SQUAD WITH NATIONALITIES: {club_squad_detail}
"""
        else:
            club_context = "No specific buying club selected."
            club_squad_detail = ""

        st.session_state.club_squad_detail = club_squad_detail

        # ── Performance Analysis ──
        with st.spinner("Analysing player performance..."):
            perf_prompt = f"""
You are an elite football scout and transfer analyst.

SEARCH REQUIREMENTS:
{club_context}
TRANSFER BUDGET: {budget}
POSITION NEEDED: {position}
ANALYSIS FOCUS: {analysis_focus}

YOU MUST ANALYSE ALL 3 OF THESE EXACT PLAYERS — ALL THREE, NOT JUST ONE:
{top_3_players.to_string()}

PLAYER 1: {top_3_players.iloc[0]['Player']} at {top_3_players.iloc[0]['Club']}
PLAYER 2: {top_3_players.iloc[1]['Player']} at {top_3_players.iloc[1]['Club']}
PLAYER 3: {top_3_players.iloc[2]['Player']} at {top_3_players.iloc[2]['Club']}

Your JSON response MUST contain exactly 3 player objects in the "players" array.
Do not skip any player. Do not combine players. Each player gets their own object.

Return ONLY a JSON object, no other text, no markdown, no backticks.
Exactly this structure:

{{
  "players": [
    {{
      "name": "Player Name",
      "club": "Club Name",
      "nation": "NAT",
      "age": 25,
      "performance_score": 8,
      "transfer_likelihood": "High",
      "transfer_likelihood_score": 80,
      "estimated_fee": "£30m - £40m",
      "strengths": ["strength 1", "strength 2", "strength 3"],
      "concerns": ["concern 1", "concern 2"],
      "one_line_summary": "One sentence scouting summary",
      "detailed_analysis": "Three to four sentence detailed scout analysis"
    }},
    {{
      "name": "Player Name",
      "club": "Club Name",
      "nation": "NAT",
      "age": 25,
      "performance_score": 8,
      "transfer_likelihood": "High",
      "transfer_likelihood_score": 80,
      "estimated_fee": "£30m - £40m",
      "strengths": ["strength 1", "strength 2", "strength 3"],
      "concerns": ["concern 1", "concern 2"],
      "one_line_summary": "One sentence scouting summary",
      "detailed_analysis": "Three to four sentence detailed scout analysis"
    }},
    {{
      "name": "Player Name",
      "club": "Club Name",
      "nation": "NAT",
      "age": 25,
      "performance_score": 8,
      "transfer_likelihood": "High",
      "transfer_likelihood_score": 80,
      "estimated_fee": "£30m - £40m",
      "strengths": ["strength 1", "strength 2", "strength 3"],
      "concerns": ["concern 1", "concern 2"],
      "one_line_summary": "One sentence scouting summary",
      "detailed_analysis": "Three to four sentence detailed scout analysis"
    }}
  ],
  "hidden_gem": "Player Name",
  "hidden_gem_reason": "One sentence why",
  "final_recommendation": "Player Name",
  "final_recommendation_reason": "Two sentence reason why"
}}
"""
            perf_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an elite football scout. Return only valid JSON. No markdown, no backticks, no extra text."},
                    {"role": "user", "content": perf_prompt}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            try:
                st.session_state.perf_data = json.loads(perf_response.choices[0].message.content)
                st.session_state.perf_report = perf_response.choices[0].message.content
            except json.JSONDecodeError:
                perf_response2 = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an elite football scout. Return only valid JSON. No markdown, no backticks, no extra text."},
                        {"role": "user", "content": perf_prompt}
                    ],
                    max_tokens=3000,
                    temperature=0.5
                )
                try:
                    st.session_state.perf_data = json.loads(perf_response2.choices[0].message.content)
                    st.session_state.perf_report = perf_response2.choices[0].message.content
                except json.JSONDecodeError:
                    st.session_state.perf_report = perf_response2.choices[0].message.content
                    st.session_state.perf_data = None

        # ── Human Factors Analysis ──
        with st.spinner("Analysing human factors..."):
            human_prompt = f"""
You are a football transfer expert specialising in human and cultural factors.

BUYING CLUB: {your_club if your_club != "Any" else "Unknown"}
TRANSFER BUDGET: {budget}

CURRENT SQUAD WITH PLAYER NAMES AND NATIONALITIES:
{club_squad_detail if club_squad_detail else "Unknown"}

YOU MUST ONLY ANALYSE THESE EXACT 3 PLAYERS — ALL THREE, NOT JUST ONE:
{top_3_players[['Player', 'Club', 'Nation', 'Age']].to_string()}

PLAYER 1: {top_3_players.iloc[0]['Player']}
PLAYER 2: {top_3_players.iloc[1]['Player']}
PLAYER 3: {top_3_players.iloc[2]['Player']}

Your JSON response MUST contain exactly 3 player objects in the "players" array.
Do not skip any player.

Return ONLY a JSON object, no other text, no markdown, no backticks.
Exactly this structure:

{{
  "players": [
    {{
      "name": "Player Name",
      "international_chemistry": {{
        "has_compatriots": true,
        "compatriot_names": ["Player A"],
        "chemistry_score": 8,
        "summary": "One sentence summary"
      }},
      "club_rivalry": {{
        "rivalry_exists": true,
        "rivalry_level": "High",
        "fan_acceptance": "Controversial",
        "summary": "One sentence summary"
      }},
      "city_lifestyle": {{
        "adaptation_score": 7,
        "summary": "One sentence summary"
      }},
      "contract_career": {{
        "career_stage": "Peak",
        "move_makes_sense": true,
        "summary": "One sentence summary"
      }},
      "overall_human_fit_score": 8,
      "one_line_verdict": "One sentence overall verdict",
      "detailed_human_analysis": "Three to four sentence detailed human factors analysis"
    }},
    {{
      "name": "Player Name",
      "international_chemistry": {{
        "has_compatriots": false,
        "compatriot_names": [],
        "chemistry_score": 5,
        "summary": "One sentence summary"
      }},
      "club_rivalry": {{
        "rivalry_exists": false,
        "rivalry_level": "Low",
        "fan_acceptance": "Welcomed",
        "summary": "One sentence summary"
      }},
      "city_lifestyle": {{
        "adaptation_score": 7,
        "summary": "One sentence summary"
      }},
      "contract_career": {{
        "career_stage": "Peak",
        "move_makes_sense": true,
        "summary": "One sentence summary"
      }},
      "overall_human_fit_score": 7,
      "one_line_verdict": "One sentence overall verdict",
      "detailed_human_analysis": "Three to four sentence detailed human factors analysis"
    }},
    {{
      "name": "Player Name",
      "international_chemistry": {{
        "has_compatriots": false,
        "compatriot_names": [],
        "chemistry_score": 5,
        "summary": "One sentence summary"
      }},
      "club_rivalry": {{
        "rivalry_exists": false,
        "rivalry_level": "Low",
        "fan_acceptance": "Welcomed",
        "summary": "One sentence summary"
      }},
      "city_lifestyle": {{
        "adaptation_score": 7,
        "summary": "One sentence summary"
      }},
      "contract_career": {{
        "career_stage": "Peak",
        "move_makes_sense": true,
        "summary": "One sentence summary"
      }},
      "overall_human_fit_score": 7,
      "one_line_verdict": "One sentence overall verdict",
      "detailed_human_analysis": "Three to four sentence detailed human factors analysis"
    }}
  ]
}}
"""
            human_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a football transfer expert. Return only valid JSON. No markdown, no backticks. Only analyse exact players provided."},
                    {"role": "user", "content": human_prompt}
                ],
                max_tokens=3000,
                temperature=0.8
            )
            try:
                st.session_state.human_data = json.loads(human_response.choices[0].message.content)
                st.session_state.human_report = human_response.choices[0].message.content
            except json.JSONDecodeError:
                human_response2 = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a football transfer expert. Return only valid JSON. No markdown, no backticks. Only analyse exact players provided."},
                        {"role": "user", "content": human_prompt}
                    ],
                    max_tokens=3000,
                    temperature=0.5
                )
                try:
                    st.session_state.human_data = json.loads(human_response2.choices[0].message.content)
                    st.session_state.human_report = human_response2.choices[0].message.content
                except json.JSONDecodeError:
                    st.session_state.human_report = human_response2.choices[0].message.content
                    st.session_state.human_data = None

        # ── Verdict ──
        with st.spinner("Generating final verdict..."):
            verdict_prompt = f"""
You are the head of recruitment at {your_club if your_club != "Any" else "a Premier League club"}.

You have two reports on these exact players:
{top_3_players[['Player', 'Club', 'Nation']].to_string()}

PERFORMANCE ANALYSIS: {st.session_state.perf_report}
HUMAN FACTORS ANALYSIS: {st.session_state.human_report}

ONLY score and recommend the players listed above. Do not introduce any new players.

Return ONLY a JSON object, no other text, no markdown, no backticks.
Exactly this structure:

{{
  "top_pick": "Player Name",
  "players": [
    {{
      "name": "Player Name",
      "performance_score": 8,
      "human_score": 7,
      "combined_score": 7.5
    }},
    {{
      "name": "Player Name",
      "performance_score": 7,
      "human_score": 8,
      "combined_score": 7.5
    }},
    {{
      "name": "Player Name",
      "performance_score": 6,
      "human_score": 7,
      "combined_score": 6.5
    }}
  ],
  "risk_rating": "Medium",
  "deal_difficulty": 6,
  "board_recommendation": "Two to three sentence recommendation"
}}
"""
            verdict_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are head of recruitment. Return only valid JSON. No markdown, no backticks."},
                    {"role": "user", "content": verdict_prompt}
                ],
                max_tokens=700,
                temperature=0.7
            )
            try:
                st.session_state.verdict_data = json.loads(verdict_response.choices[0].message.content)
                st.session_state.verdict = verdict_response.choices[0].message.content
            except json.JSONDecodeError:
                st.session_state.verdict = verdict_response.choices[0].message.content
                st.session_state.verdict_data = None

        st.session_state.results_ready = True

# ── DISPLAY RESULTS ──
if st.session_state.results_ready and st.session_state.display is not None:

    display = st.session_state.display
    top_3_players = st.session_state.top_3_players
    perf_data = st.session_state.perf_data
    perf_report = st.session_state.perf_report
    human_data = st.session_state.human_data
    human_report = st.session_state.human_report
    verdict_data = st.session_state.verdict_data
    verdict = st.session_state.verdict
    club_squad_detail = st.session_state.club_squad_detail
    your_club = st.session_state.your_club_saved

    st.subheader(f"🏆 {len(display)} Transfer Targets Found")
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.divider()

    # Performance Display
    st.subheader("🤖 AI Performance Analysis")

    if perf_data:
        for player in perf_data['players']:
            likelihood_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(player['transfer_likelihood'], "⚪")
            score = player['performance_score']
            score_bar = "🟦" * score + "⬜" * (10 - score)

            with st.container():
                st.markdown(f"### {player['name']} — {player['club']} {likelihood_color}")
                left, right = st.columns([2, 1])

                with left:
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Performance Score", f"{score}/10")
                        st.markdown(f"`{score_bar}`")
                    with col_b:
                        st.metric("Transfer Likelihood", player['transfer_likelihood'])
                        st.progress(player['transfer_likelihood_score'] / 100)
                    with col_c:
                        st.metric("Estimated Fee", player['estimated_fee'])

                    col_s, col_c2 = st.columns(2)
                    with col_s:
                        st.markdown("**✅ Strengths**")
                        for s in player['strengths']:
                            st.markdown(f"- {s}")
                    with col_c2:
                        st.markdown("**⚠️ Concerns**")
                        for c in player['concerns']:
                            st.markdown(f"- {c}")

                    st.info(f"💬 *{player['one_line_summary']}*")

                with right:
                    st.markdown("**📋 Scout Notes**")
                    scout_notes_box(player.get('detailed_analysis', 'Analysis not available.'))

                st.divider()

        col_gem, col_rec = st.columns(2)
        with col_gem:
            st.success(f"💎 **Hidden Gem:** {perf_data['hidden_gem']}\n\n{perf_data['hidden_gem_reason']}")
        with col_rec:
            st.warning(f"🎯 **Top Recommendation:** {perf_data['final_recommendation']}\n\n{perf_data['final_recommendation_reason']}")
    else:
        st.markdown(perf_report)

    st.divider()

    # Human Factors Display
    st.subheader("🧠 Human Factors Analysis")
    st.markdown("*Beyond the stats — culture, chemistry, rivalry, and lifestyle fit*")

    if human_data:
        for player in human_data['players']:
            rivalry_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "None": "🟢"}.get(player['club_rivalry']['rivalry_level'], "⚪")
            fit_score = player['overall_human_fit_score']
            fit_bar = "🟩" * fit_score + "⬜" * (10 - fit_score)

            with st.container():
                st.markdown(f"### {player['name']}")
                left, right = st.columns([2, 1])

                with left:
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        chem_score = player['international_chemistry']['chemistry_score']
                        st.metric("🤝 Chemistry", f"{chem_score}/10")
                        compatriots = player['international_chemistry']['compatriot_names']
                        if compatriots:
                            st.caption(f"Knows: {', '.join(compatriots[:2])}")
                        else:
                            st.caption("No compatriots in squad")
                    with col_b:
                        st.metric("⚔️ Rivalry", player['club_rivalry']['rivalry_level'])
                        st.caption(f"{rivalry_emoji} {player['club_rivalry']['fan_acceptance']}")
                    with col_c:
                        adapt_score = player['city_lifestyle']['adaptation_score']
                        st.metric("🌍 City Fit", f"{adapt_score}/10")
                        st.caption(player['city_lifestyle']['summary'][:50] + "...")
                    with col_d:
                        st.metric("📅 Career Stage", player['contract_career']['career_stage'])
                        move_emoji = "✅" if player['contract_career']['move_makes_sense'] else "❌"
                        st.caption(f"{move_emoji} Move makes sense")

                    st.markdown(f"**Overall Human Fit:** `{fit_bar}` {fit_score}/10")
                    st.info(f"💬 *{player['one_line_verdict']}*")

                with right:
                    st.markdown("**📋 Human Factors Notes**")
                    scout_notes_box(player.get('detailed_human_analysis', 'Analysis not available.'))

                st.divider()
    else:
        st.markdown(human_report)

    st.divider()

    # Verdict Display
    st.subheader("🏆 Overall Transfer Verdict")

    if verdict_data:
        risk_color = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(verdict_data['risk_rating'], "⚪")
        st.success(f"## 🏆 Top Pick: {verdict_data['top_pick']}")

        cols = st.columns(len(verdict_data['players']))
        for i, player in enumerate(verdict_data['players']):
            with cols[i]:
                st.markdown(f"**{player['name']}**")
                st.metric("⚽ Performance", f"{player['performance_score']}/10")
                st.metric("🧠 Human Fit", f"{player['human_score']}/10")
                st.metric("🎯 Combined", f"{player['combined_score']}/10")

        st.divider()
        col_risk, col_diff = st.columns(2)
        with col_risk:
            st.metric("Risk Rating", f"{risk_color} {verdict_data['risk_rating']}")
        with col_diff:
            difficulty = verdict_data['deal_difficulty']
            diff_bar = "🔷" * difficulty + "⬜" * (10 - difficulty)
            st.metric("Deal Difficulty", f"{difficulty}/10")
            st.markdown(f"`{diff_bar}`")

        st.warning(f"📋 **Board Recommendation:** {verdict_data['board_recommendation']}")
    else:
        st.markdown(verdict)

    st.divider()

    # Inline Comparison
    st.subheader("🔍 Compare Top 2 Players in Detail")
    st.markdown("*Side by side deep dive on the top two recommendations*")

    if st.button("⚽ Compare Top 2 Players", use_container_width=True):
        st.session_state.show_comparison = True

    if st.session_state.show_comparison and len(top_3_players) >= 2:
        p1_name = top_3_players.iloc[0]['Player']
        p2_name = top_3_players.iloc[1]['Player']

        comparison = compare_players(p1_name, p2_name)

        if comparison is not None:
            st.subheader(f"📊 {p1_name} vs {p2_name}")
            st.dataframe(comparison, use_container_width=True)
            st.divider()

            h1 = get_player_history(p1_name)
            h2 = get_player_history(p2_name)

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown(f"**{p1_name} — Goals per season**")
                st.bar_chart(h1.set_index('season')['Performance_Gls'])
            with chart_col2:
                st.markdown(f"**{p2_name} — Goals per season**")
                st.bar_chart(h2.set_index('season')['Performance_Gls'])

            st.divider()
            st.subheader("🤖 Head to Head AI Report")
            with st.spinner("Generating head to head report..."):
                h2h_prompt = f"""
You are an elite football scout comparing two transfer targets.

COMPARISON DATA:
{comparison.to_string()}

{p1_name} SEASON HISTORY:
{h1.to_string()}

{p2_name} SEASON HISTORY:
{h2.to_string()}

Generate a concise head to head report:
1. Key differences between the two players
2. Who suits {your_club if your_club != "Any" else "a top Premier League club"} better
3. Final verdict — who to sign and why

Be specific, reference actual numbers, max 200 words.
"""
                h2h_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an elite football scout. Be concise and decisive."},
                        {"role": "user", "content": h2h_prompt}
                    ],
                    max_tokens=400,
                    temperature=0.7
                )
                st.markdown(h2h_response.choices[0].message.content)

    st.divider()

    # Download
    full_report = f"""
AI FOOTBALL SCOUT — TRANSFER REPORT
=====================================
CLUB: {your_club}
POSITION: {position}
BUDGET: {budget}
SEASON: {season}

PERFORMANCE ANALYSIS
====================
{perf_report}

HUMAN FACTORS ANALYSIS
=======================
{human_report}

OVERALL VERDICT
===============
{verdict}
"""
    st.download_button(
        label="📥 Download Full Transfer Report",
        data=full_report,
        file_name=f"transfer_report_{your_club}_{position}.txt",
        mime="text/plain"
    )