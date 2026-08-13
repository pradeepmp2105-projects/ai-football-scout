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
        'Team': ['team', 'team'],
        'Position': ['pos', 'pos'],
        'Age': ['age', 'age'],
        'Matches Played': ['Playing Time_MP', 'Playing Time_MP'],
        'Minutes': ['Playing Time_Min', 'Playing Time_Min'],
        'Goals': ['Performance_Gls', 'Performance_Gls'],
        'Assists': ['Performance_Ast', 'Performance_Ast'],
        'Goals + Assists': ['Performance_G+A', 'Performance_G+A'],
        'Goals per 90': ['Per 90 Minutes_Gls', 'Per 90 Minutes_Gls'],
        'Assists per 90': ['Per 90 Minutes_Ast', 'Per 90 Minutes_Ast'],
        'G+A per 90': ['Per 90 Minutes_G+A', 'Per 90 Minutes_G+A'],
        'Yellow Cards': ['Performance_CrdY', 'Performance_CrdY'],
        'Red Cards': ['Performance_CrdR', 'Performance_CrdR'],
    }
    
    # Build comparison table
    rows = []
    for metric, cols in metrics.items():
        rows.append({
            'Metric': metric,
            player1: p1[cols[0]],
            player2: p2[cols[0]]
        })
    
    comparison = pd.DataFrame(rows)
    comparison = comparison.set_index('Metric')
    
    return comparison

# Test it
result = compare_players("Bukayo Saka", "Mohamed Salah")
if result is not None:
    print("\n=== PLAYER COMPARISON ===\n")
    print(result.to_string())
    # Test with specific season
print("\n=== SAKA vs SALAH (2025/26) ===\n")
result_2526 = compare_players("Bukayo Saka", "Mohamed Salah", season="2526")
if result_2526 is not None:
    print(result_2526.to_string())

# Search function - find player names
def search_player(name):
    results = df[df['player'].str.lower().str.contains(name.lower())]
    return results[['player', 'team', 'season', 'pos']].drop_duplicates('player')

# Test search
print("\n=== PLAYER SEARCH: 'sal' ===")
print(search_player("sal").to_string())
# Check all seasons for specific players
print("\n=== SAKA ALL SEASONS ===")
saka = df[df['player'].str.lower() == 'bukayo saka'][['player', 'season', 'team', 'Performance_Gls', 'Performance_Ast']]
print(saka.to_string())

print("\n=== SALAH ALL SEASONS ===")
salah = df[df['player'].str.lower() == 'mohamed salah'][['player', 'season', 'team', 'Performance_Gls', 'Performance_Ast']]
print(salah.to_string())