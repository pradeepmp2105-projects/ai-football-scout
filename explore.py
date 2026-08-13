import soccerdata as sd
import pandas as pd

print("Fetching Premier League player stats - last 5 seasons...")

fbref = sd.FBref(leagues="ENG-Premier League", seasons=[2021, 2022, 2023, 2024, 2025])
df = fbref.read_player_season_stats("standard")

df.columns = ['_'.join(col).strip('_') for col in df.columns]
df = df.reset_index()

df.to_csv("players.csv", index=False)
print(f"Saved {len(df)} players to players.csv")
print(f"Seasons available: {df['season'].unique()}")
print(f"Total clubs: {df['team'].nunique()}")
print(df[['player', 'season', 'team', 'pos', 'Performance_Gls', 'Performance_Ast']].head(10))