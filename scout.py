import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from comparison import compare_players, search_player, get_player_history

# Load API keys
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_scouting_report(player1, player2, season=None):
    # Get comparison data
    comparison = compare_players(player1, player2, season)
    if comparison is None:
        return None
    
    # Get player history
    p1_history = get_player_history(player1)
    p2_history = get_player_history(player2)
    
    # Build prompt
    prompt = f"""
You are an elite football scout with 20 years of experience in the Premier League.

You have been asked to compare two players and generate a detailed scouting report.

PLAYER COMPARISON DATA:
{comparison.to_string()}

{player1} SEASON BY SEASON HISTORY:
{p1_history.to_string()}

{player2} SEASON BY SEASON HISTORY:
{p2_history.to_string()}

Generate a detailed scouting report that includes:
1. Overview of both players
2. Attacking contribution analysis
3. Consistency and availability analysis
4. Age and trajectory analysis
5. Final verdict — who would you recommend signing and why?

Write like a professional scout — be specific, reference the actual numbers, and be decisive in your recommendation.
"""

    # Call OpenAI
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an elite football scout. Always be specific, data-driven, and decisive."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content

# Test it
print("Generating scouting report...\n")
report = generate_scouting_report("Bukayo Saka", "Mohamed Salah")
if report:
    print("=" * 60)
    print("AI SCOUTING REPORT")
    print("=" * 60)
    print(report)
    print("=" * 60)