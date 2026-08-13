import pandas as pd

# Load the data
df = pd.read_csv("players.csv")

def compare_players(player1, player2, season=None):
    # Filter by season if provided
    data = df.copy()
    if season:
        data = data[data['season'].astype(str) == str(season)]
    
    # Find players (case insensitive)
    p1 = data[data['player'].str.lower() == player1.lower()]
    p2 = data[data['player'].str.lower() == player2.lower()]
    
    # Check if players found
    if p1.empty:
        print(f"Player '{player1}' not found!")
        return None
    if p2.empty:
        print(f"Player '{player2}' not found!")
        return None
    
    # Take most recent season if multiple rows
    p1 = p1.sort_values('season', ascending=False).iloc[0]
    p2 = p2.sort_values('season', ascending=False).iloc[0]
    
    # Key metrics to compare
    metrics = {
        'Team': 'team',
        'Position': 'pos',
        'Age': 'age',
        'Matches Played': 'Playing Time_MP',
        'Minutes': 'Playing Time_Min',
        'Goals': 'Performance_Gls',
        'Assists': 'Performance_Ast',
        'Goals + Assists': 'Performance_G+A',
        'Goals per 90': 'Per 90 Minutes_Gls',
        'Assists per 90': 'Per 90 Minutes_Ast',
        'G+A per 90': 'Per 90 Minutes_G+A',
        'Yellow Cards': 'Performance_CrdY',
        'Red Cards': 'Performance_CrdR',
    }
    
    # Build comparison table
    rows = []
    for metric, col in metrics.items():
        rows.append({
            'Metric': metric,
            player1: p1[col],
            player2: p2[col]
        })
    
    comparison = pd.DataFrame(rows)
    comparison = comparison.set_index('Metric')
    
    return comparison

def search_player(name):
    results = df[df['player'].str.lower().str.contains(name.lower())]
    return results[['player', 'team', 'season', 'pos']].drop_duplicates('player')

def get_player_history(name):
    results = df[df['player'].str.lower() == name.lower()]
    return results[['player', 'season', 'team', 'Performance_Gls', 'Performance_Ast', 'Per 90 Minutes_G+A']].sort_values('season')